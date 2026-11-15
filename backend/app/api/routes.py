"""REST API and WebSocket routes for system health, signals, instruments, and notifications."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.websocket import ws_manager
from backend.app.config.settings import get_config
from backend.app.database.models import (
    InstrumentModel,
    NotificationDeliveryModel,
    SignalModel,
    SystemEventModel,
)
from backend.app.database.session import get_db_session
from backend.app.models.signal import SignalEvent, SignalType

router = APIRouter()


class TestAlertRequest(BaseModel):
    symbol: str = "RELIANCE"
    exchange: str = "NSE"
    asset_class: str = "equity"
    timeframe: str = "15m"
    signal_type: str = "BULLISH"
    price: float = 1542.30
    ema100: float = 1538.25
    ema200: float = 1536.90


@router.get("/health")
async def get_health() -> Dict[str, Any]:
    """Basic health check endpoint returning connectivity status across all components."""
    from backend.app.main import app_state

    status = "healthy"
    angel_conn = "connected" if app_state.angel_provider and app_state.angel_provider.is_connected else "disconnected"
    delta_conn = "connected" if app_state.delta_provider and app_state.delta_provider.is_connected else "disconnected"

    cfg = get_config()
    tg_status = "healthy" if cfg.notifications.telegram.enabled else "disabled"
    em_status = "healthy" if cfg.notifications.email.enabled else "disabled"
    wa_status = "configured" if cfg.notifications.whatsapp.enabled else "disabled"

    return {
        "status": status,
        "angelone": angel_conn,
        "delta": delta_conn,
        "telegram": tg_status,
        "email": em_status,
        "whatsapp": wa_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


def format_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """Ensure datetime string is explicitly suffixed with Z for UTC client parsing."""
    if not dt:
        return None
    s = dt.isoformat()
    return s if s.endswith("Z") or "+" in s else f"{s}Z"


@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """Detailed monitoring status matching specification Section 37."""
    from backend.app.main import app_state

    cfg = get_config()
    inst_mgr = app_state.instrument_manager

    # Count monitored instruments by asset class
    counts = {"stocks": 0, "futures": 0, "options": 0, "commodities": 0, "crypto": 0}
    if inst_mgr:
        monitored = inst_mgr.get_monitored_instruments()
        for inst in monitored:
            if inst.asset_class == "equity":
                counts["stocks"] += 1
            elif inst.asset_class == "equity_futures":
                counts["futures"] += 1
            elif inst.asset_class == "equity_options":
                counts["options"] += 1
            elif inst.asset_class == "commodity":
                counts["commodities"] += 1
            elif inst.asset_class == "crypto":
                counts["crypto"] += 1

    # Fetch recent signals count
    recent_signals = []
    try:
        async with get_db_session() as session:
            stmt = select(SignalModel).order_by(desc(SignalModel.created_at)).limit(10)
            res = await session.execute(stmt)
            rows = res.scalars().all()
            for r in rows:
                recent_signals.append({
                    "id": r.id,
                    "signal_id": r.signal_id,
                    "symbol": r.symbol,
                    "exchange": r.exchange,
                    "asset_class": r.asset_class,
                    "timeframe": r.timeframe,
                    "signal_type": r.signal_type,
                    "price": r.price,
                    "ema100": r.ema100,
                    "ema200": r.ema200,
                    "created_at": format_iso_utc(r.created_at),
                })
    except Exception:
        pass

    return {
        "system_status": "HEALTHY" if getattr(app_state, "is_engine_active", True) else "PAUSED",
        "is_engine_active": getattr(app_state, "is_engine_active", True),
        "last_engine_action": getattr(app_state, "last_engine_action", "started"),
        "providers": {
            "angelone": "Connected" if app_state.angel_provider and app_state.angel_provider.is_connected else "Standby",
            "delta": "Connected" if app_state.delta_provider and app_state.delta_provider.is_connected else "Standby",
        },
        "monitored_counts": counts,
        "timeframes": cfg.strategy.timeframes,
        "instrument_timeframes": cfg.strategy.instrument_timeframes,
        "notifications": {
            "telegram": "Enabled" if cfg.notifications.telegram.enabled else "Disabled",
            "email": "Enabled" if cfg.notifications.email.enabled else "Disabled",
            "whatsapp": "Enabled" if cfg.notifications.whatsapp.enabled else "Disabled",
        },
        "recent_alerts": recent_signals,
    }


@router.get("/api/signals")
async def get_signals(
    asset_class: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    signal_type: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Search and filter historical alert signals."""
    async with get_db_session() as session:
        query = select(SignalModel)

        if asset_class:
            query = query.where(SignalModel.asset_class == asset_class.lower())
        if exchange:
            query = query.where(SignalModel.exchange == exchange.upper())
        if symbol:
            query = query.where(SignalModel.symbol.ilike(f"%{symbol}%"))
        if timeframe:
            query = query.where(SignalModel.timeframe == timeframe.lower())
        if signal_type:
            query = query.where(SignalModel.signal_type == signal_type.upper())
        if provider:
            query = query.where(SignalModel.provider == provider.lower())

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        count_res = await session.execute(count_stmt)
        total = count_res.scalar_one()

        # Paginate
        query = query.order_by(desc(SignalModel.created_at)).offset(offset).limit(limit)
        result = await session.execute(query)
        signals = result.scalars().all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "signals": [
                {
                    "id": s.id,
                    "signal_id": s.signal_id,
                    "provider": s.provider,
                    "asset_class": s.asset_class,
                    "exchange": s.exchange,
                    "symbol": s.symbol,
                    "instrument_id": s.instrument_id,
                    "timeframe": s.timeframe,
                    "signal_type": s.signal_type,
                    "candle_timestamp": format_iso_utc(s.candle_timestamp),
                    "price": s.price,
                    "ema100": s.ema100,
                    "ema200": s.ema200,
                    "previous_ema100": s.previous_ema100,
                    "previous_ema200": s.previous_ema200,
                    "is_catchup": bool(getattr(s, "is_catchup", False)),
                    "created_at": format_iso_utc(s.created_at),
                }
                for s in signals
            ],
        }


@router.get("/api/instruments")
async def get_instruments() -> Dict[str, Any]:
    """Retrieve list of currently monitored instruments across all asset classes."""
    from backend.app.main import app_state

    if not app_state.instrument_manager:
        return {"instruments": []}

    monitored = app_state.instrument_manager.get_monitored_instruments()
    return {
        "count": len(monitored),
        "instruments": [i.model_dump() for i in monitored],
    }


class ConfigureAlertRequest(BaseModel):
    strategy: str = "ema_crossover"
    ema_fast: int = 100
    ema_slow: int = 200
    timeframes: List[str] = ["5m", "15m", "30m", "1h"]
    symbols: Dict[str, List[str]] = {}
    instrument_timeframes: Optional[Dict[str, List[str]]] = None
    action: str = "add"  # "add" | "set"


class UpdateInstrumentTimeframesRequest(BaseModel):
    symbol: str
    timeframes: List[str]


class RemoveInstrumentRequest(BaseModel):
    symbol: str
    asset_class: Optional[str] = ""


@router.get("/api/available-instruments")
async def get_available_instruments(
    query: Optional[str] = None,
    category: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
) -> Dict[str, Any]:
    """Retrieve full dynamic instrument universe for adding into alerts.

    Supports fast typeahead search across 150k+ NSE/BSE/NFO/MCX instruments.
    Returns expiry dates, monitoring status, and lot/tick sizes.
    """
    from datetime import date, datetime
    from backend.app.main import app_state
    from backend.app.market_data.instrument_manager import parse_expiry_date

    if not app_state.instrument_manager:
        return {"crypto": [], "equity": [], "equity_futures": [], "commodity": [], "counts": {}}

    # Use fast catalog search if category or query is specified
    if query or category:
        results = app_state.instrument_manager.search_catalog(
            query=query or "",
            category=category,
            exchange=exchange,
            limit=limit,
        )
        return {"results": results, "count": len(results)}

    # Default: return full categorized view for modal population
    all_insts = app_state.instrument_manager.get_all_instruments()
    monitored_ids = {
        f"{i.provider}:{i.instrument_id}"
        for i in app_state.instrument_manager.get_monitored_instruments()
    }

    today = datetime.now().date()

    categorized: Dict[str, List[Dict[str, Any]]] = {
        "crypto": [],
        "equity_nse": [],
        "equity_bse": [],
        "equity": [],
        "equity_futures": [],
        "equity_options": [],
        "commodity": [],
    }

    for inst in all_insts:
        key = f"{inst.provider}:{inst.instrument_id}"
        sym_upper = inst.symbol.upper()
        is_mon = key in monitored_ids

        exp_d = parse_expiry_date(inst.expiry)
        is_expired = (exp_d is not None and exp_d < today)
        # Skip expired contracts unless actively monitored
        if is_expired and not is_mon:
            continue

        item = {
            "symbol": inst.symbol,
            "name": inst.name or inst.symbol,
            "provider": inst.provider,
            "exchange": inst.exchange,
            "instrument_id": inst.instrument_id,
            "tick_size": inst.tick_size,
            "lot_size": inst.lot_size,
            "asset_class": inst.asset_class,
            "instrument_type": inst.instrument_type,
            "expiry": inst.expiry,
            "expiry_date": exp_d.isoformat() if exp_d else None,
            "strike": inst.strike,
            "option_type": inst.option_type,
            "underlying": inst.underlying,
            "is_expired": is_expired,
            "is_monitored": is_mon,
        }

        cat = inst.asset_class
        if cat == "equity":
            exch = inst.exchange.upper()
            if exch == "NSE":
                categorized["equity_nse"].append(item)
            elif exch == "BSE":
                categorized["equity_bse"].append(item)
            categorized["equity"].append(item)
        elif cat == "equity_futures":
            categorized["equity_futures"].append(item)
        elif cat == "equity_options":
            categorized["equity_options"].append(item)
        elif cat == "commodity":
            categorized["commodity"].append(item)
        elif cat == "crypto":
            categorized["crypto"].append(item)

    # Sort: monitored first, then alphabetical, futures sorted by nearest expiry
    def sort_key(x: Dict) -> tuple:
        from datetime import date
        exp_d = None
        if x.get("expiry_date"):
            try:
                exp_d = date.fromisoformat(x["expiry_date"])
            except Exception:
                pass
        return (not x["is_monitored"], x.get("is_expired", False), exp_d or date.max, x["symbol"])

    MAX_PER_CATEGORY = 120
    for cat in categorized:
        categorized[cat].sort(key=sort_key)
        # Always retain all monitored, then take up to MAX_PER_CATEGORY items
        monitored_items = [i for i in categorized[cat] if i["is_monitored"]]
        unmonitored_items = [i for i in categorized[cat] if not i["is_monitored"]]
        categorized[cat] = monitored_items + unmonitored_items[:max(0, MAX_PER_CATEGORY - len(monitored_items))]

    return {
        "counts": {cat: len(items) for cat, items in categorized.items()},
        "instruments": categorized,
    }


@router.get("/api/catalog-search")
async def catalog_search(
    q: str = Query(""),
    category: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """Lightning-fast typeahead search across 150k+ instruments from the cached Angel One catalog with live API fallback."""
    from backend.app.main import app_state
    from backend.app.models.instrument import InstrumentDefinition

    if not app_state.instrument_manager:
        return {"results": [], "count": 0}

    results = app_state.instrument_manager.search_catalog(
        query=q,
        category=category,
        exchange=exchange,
        limit=limit,
    )

    # If results are very few or 0 and query is provided, query Angel One SmartAPI live for NSE and BSE
    clean_q = q.strip().upper()
    if len(results) < 2 and clean_q and app_state.angel_provider and hasattr(app_state.angel_provider, "client"):
        exchanges_to_query = [exchange.upper()] if exchange and exchange.upper() in ("NSE", "BSE") else ["NSE", "BSE"]
        for target_exch in exchanges_to_query:
            try:
                api_results = await app_state.angel_provider.client.search_scrip(target_exch, clean_q)
                for item in api_results:
                    tsym = item.get("tradingsymbol", "").strip()
                    tok = str(item.get("symboltoken", "")).strip()
                    sym_upper = tsym.upper()

                    # Filter out clutter non-retail exchange deal series on NSE
                    if target_exch == "NSE":
                        clutter_suffixes = ("-BL", "-IQ", "-RL", "-IL", "-BZ", "-E1", "-W1", "-MF", "-GB", "-SG")
                        if any(sym_upper.endswith(sfx) for sfx in clutter_suffixes):
                            continue
                        if sym_upper.endswith("-BE") and not clean_q.endswith("-BE"):
                            continue

                    base_sym = sym_upper.replace("-EQ", "").replace("-A", "").replace("-B", "").strip()
                    display_sym = f"{base_sym}-{target_exch}"

                    if tok and not any(r["instrument_id"] == tok for r in results):
                        new_inst = InstrumentDefinition(
                            provider="angelone",
                            exchange=target_exch,
                            symbol=tsym,
                            instrument_id=tok,
                            name=clean_q,
                            asset_class="equity" if target_exch in ("NSE", "BSE") else "equity_futures",
                            instrument_type="EQUITY",
                            expiry=item.get("expiry"),
                            lot_size=1,
                            tick_size=0.05,
                            is_active=True,
                            underlying=clean_q,
                        )
                        app_state.instrument_manager.register_single_instrument("angelone", new_inst)
                        results.append({
                            "symbol": new_inst.symbol,
                            "display_symbol": display_sym,
                            "base_symbol": base_sym,
                            "name": new_inst.name or new_inst.symbol,
                            "provider": new_inst.provider,
                            "exchange": new_inst.exchange,
                            "instrument_id": new_inst.instrument_id,
                            "asset_class": new_inst.asset_class,
                            "instrument_type": new_inst.instrument_type,
                            "expiry": new_inst.expiry,
                            "expiry_date": None,
                            "strike": None,
                            "option_type": None,
                            "lot_size": 1,
                            "tick_size": 0.05,
                            "is_expired": False,
                            "is_monitored": False,
                        })
            except Exception as e:
                logger.warning(f"Live SmartAPI search fallback error for {clean_q} on {target_exch}: {e}")

    return {"results": results, "count": len(results)}


@router.get("/api/active-alerts")
async def get_active_alerts() -> Dict[str, Any]:
    """Retrieve currently active alert rules and monitored symbols."""
    from backend.app.main import app_state

    cfg = get_config()
    inst_mgr = app_state.instrument_manager

    monitored = inst_mgr.get_monitored_instruments() if inst_mgr else []
    return {
        "strategy": {
            "name": cfg.strategy.name,
            "version": cfg.strategy.version,
            "ema_fast": cfg.strategy.ema_fast,
            "ema_slow": cfg.strategy.ema_slow,
            "timeframes": cfg.strategy.timeframes,
            "instrument_timeframes": cfg.strategy.instrument_timeframes,
        },
        "total_monitored": len(monitored),
        "monitored_instruments": [
            {
                "symbol": i.symbol,
                "name": i.name or i.symbol,
                "provider": i.provider,
                "exchange": i.exchange,
                "asset_class": i.asset_class,
                "instrument_id": i.instrument_id,
            }
            for i in monitored
        ],
    }


@router.post("/api/alerts/configure")
async def configure_alert(req: ConfigureAlertRequest) -> Dict[str, Any]:
    """
    Dynamically add or set coins/stocks for EMA 100/200 crossover alerts,
    warm up indicators on live data, and subscribe WebSocket feeds in real-time.
    """
    import asyncio
    from pathlib import Path
    from backend.app.core.atomic_yaml import atomic_write_yaml, read_yaml
    from backend.app.main import app_state

    if not app_state.instrument_manager or not app_state.stream_manager:
        raise HTTPException(status_code=500, detail="Platform engines are still initializing.")

    cfg = get_config()
    prev_timeframes = list(cfg.strategy.timeframes)
    cfg.strategy.timeframes = req.timeframes or cfg.strategy.timeframes
    newly_added_timeframes = [tf for tf in cfg.strategy.timeframes if tf not in prev_timeframes]

    # Track previously monitored symbols to find new ones
    prev_monitored_ids = {
        f"{i.provider}:{i.instrument_id}"
        for i in app_state.instrument_manager.get_monitored_instruments()
    }

    # Update markets config and ensure uncataloged symbols are fetched & registered
    for market_key, symbol_list in req.symbols.items():
        if market_key in cfg.markets and symbol_list is not None:
            m_cfg = cfg.markets[market_key]
            m_cfg.enabled = True
            clean_syms = [s.strip().upper() for s in symbol_list if s.strip()]

            # Dynamically ensure custom or uncataloged equity stocks from Angel One SmartAPI
            if market_key in ("equity", "bse_equity"):
                target_exch = "NSE" if market_key == "equity" else "BSE"
                for sym in clean_syms:
                    await app_state.instrument_manager.ensure_instrument(
                        symbol=sym,
                        exchange=target_exch,
                        angel_provider=app_state.angel_provider,
                    )

            if req.action == "set":
                m_cfg.symbols = clean_syms
            else:
                # Add unique symbols
                existing_set = set(m_cfg.symbols)
                for s in clean_syms:
                    if s not in existing_set:
                        m_cfg.symbols.append(s)
                        existing_set.add(s)

    # Persist updated symbols to default_config.yaml so they survive restarts
    try:
        cfg_path = Path("backend/app/config/default_config.yaml")
        raw_yaml = read_yaml(cfg_path)

        if "markets" not in raw_yaml:
            raw_yaml["markets"] = {}

        for m_k, m_val in cfg.markets.items():
            if m_k not in raw_yaml["markets"]:
                raw_yaml["markets"][m_k] = {}
            raw_yaml["markets"][m_k]["enabled"] = m_val.enabled
            raw_yaml["markets"][m_k]["symbols"] = m_val.symbols

        if "strategy" not in raw_yaml:
            raw_yaml["strategy"] = {}
        raw_yaml["strategy"]["timeframes"] = cfg.strategy.timeframes

        if req.instrument_timeframes is not None:
            if "instrument_timeframes" not in raw_yaml["strategy"]:
                raw_yaml["strategy"]["instrument_timeframes"] = {}
            raw_yaml["strategy"]["instrument_timeframes"] = {
                k.upper(): [tf.lower() for tf in v]
                for k, v in req.instrument_timeframes.items()
            }
            cfg.strategy.instrument_timeframes = {
                k.upper(): [tf.lower() for tf in v]
                for k, v in req.instrument_timeframes.items()
            }

        await atomic_write_yaml(cfg_path, raw_yaml)
    except Exception as e:
        logger.warning(f"Could not persist config YAML: {e}")

    # Re-resolve monitored universe
    new_universe = app_state.instrument_manager.resolve_monitored_universe()

    # Identify newly added instruments that need historical warm-up
    newly_added = [
        inst for inst in new_universe
        if f"{inst.provider}:{inst.instrument_id}" not in prev_monitored_ids
    ]

    # Warm up indicators for new instruments or new timeframes in the background
    if newly_added:
        async def _warmup_and_catchup_new(insts, tfs):
            try:
                await app_state.stream_manager.warm_up_instruments(insts, tfs)
                from backend.app.main import process_startup_catchup_crossovers
                await process_startup_catchup_crossovers(target_symbols=[i.symbol for i in insts], force_notify=True)
            except Exception as e:
                logger.warning(f"Error in warmup/catchup for newly added instruments: {e}")

        asyncio.create_task(_warmup_and_catchup_new(newly_added, cfg.strategy.timeframes))
    elif newly_added_timeframes:
        logger.info(f"User enabled new timeframe(s) {newly_added_timeframes}. Warming up {len(new_universe)} instruments...")
        async def _warmup_and_catchup_tfs(insts, tfs):
            try:
                await app_state.stream_manager.warm_up_instruments(insts, tfs)
                from backend.app.main import process_startup_catchup_crossovers
                await process_startup_catchup_crossovers(force_notify=True)
            except Exception as e:
                logger.warning(f"Error in warmup/catchup for newly added timeframes: {e}")

        asyncio.create_task(_warmup_and_catchup_tfs(new_universe, newly_added_timeframes))

    # Subscribe providers to the updated active universe
    delta_targets = app_state.instrument_manager.get_monitored_by_provider("delta")
    if delta_targets and app_state.delta_provider:
        await app_state.delta_provider.subscribe(delta_targets, cfg.strategy.timeframes)

    angel_targets = app_state.instrument_manager.get_monitored_by_provider("angelone")
    if angel_targets and app_state.angel_provider:
        await app_state.angel_provider.subscribe(angel_targets, cfg.strategy.timeframes)

    # Broadcast update event to all connected dashboard clients
    await ws_manager.broadcast({
        "type": "MONITORED_UPDATED",
        "data": {
            "total_monitored": len(new_universe),
            "newly_added_count": len(newly_added),
        },
    })

    return {
        "status": "success",
        "message": f"Successfully updated alert monitoring. {len(new_universe)} instruments active.",
        "total_monitored": len(new_universe),
        "newly_added_count": len(newly_added),
        "timeframes": cfg.strategy.timeframes,
    }


@router.delete("/api/alerts/instrument")
async def remove_monitored_instrument(req: RemoveInstrumentRequest) -> Dict[str, Any]:
    """Remove a coin or stock from active monitoring."""
    import re
    import yaml
    from pathlib import Path
    from backend.app.main import app_state

    if not app_state.instrument_manager:
        raise HTTPException(status_code=500, detail="Platform not ready")

    cfg = get_config()
    target_sym = req.symbol.strip().upper()
    cat = (req.asset_class or "").lower()

    # Build set of all possible representations of this symbol to remove
    # 1. Exact symbol, e.g. "INDUSINDBK-EQ", "NIFTY23NOV26FUT", "BNBUSD"
    # 2. Clean base symbol without exchange suffixes, e.g. "INDUSINDBK", "BSE", "CUPID"
    # 3. Contract root underlying if futures/options, e.g. "NIFTY", "BANKNIFTY", "CRUDEOIL"
    clean_base = re.sub(r'-(EQ|BE|A|B|NSE|BSE)$', '', target_sym)
    root_sym = re.sub(r'\d{2}[A-Z]{3}.*$', '', target_sym).strip()
    if not root_sym or root_sym == target_sym:
        root_sym = re.sub(r'\d{2}[A-Z]{3}(FUT|CE|PE)?$', '', target_sym).strip()

    symbols_to_purge = {target_sym, clean_base}
    if root_sym and root_sym != target_sym:
        symbols_to_purge.add(root_sym)

    # Check registered instruments to get underlying / exact names
    for inst in app_state.instrument_manager._all_instruments.values():
        if inst.symbol.upper() == target_sym or inst.instrument_id == req.symbol:
            if inst.underlying:
                symbols_to_purge.add(inst.underlying.upper())
            if inst.name:
                clean_name = inst.name.upper().replace("-EQ", "").strip()
                symbols_to_purge.add(clean_name)
            break

    logger.info(f"Purging monitored instrument {target_sym} (keys: {symbols_to_purge}) in category {cat}")

    # Determine which categories to purge from
    target_categories = set()
    if cat:
        target_categories.add(cat)
        if cat in ("equity", "equity_nse", "nse"):
            target_categories.add("equity")
            target_categories.add("bse_equity")
        elif cat in ("bse_equity", "equity_bse", "bse"):
            target_categories.add("bse_equity")
            target_categories.add("equity")
    else:
        target_categories = set(cfg.markets.keys())

    for m_k, m_cfg in cfg.markets.items():
        if m_k in target_categories or not cat:
            m_cfg.symbols = [
                s for s in m_cfg.symbols
                if s.upper() not in symbols_to_purge
                and re.sub(r'-(EQ|BE|A|B|NSE|BSE)$', '', s.upper()) not in symbols_to_purge
                and (not root_sym or s.upper() != root_sym)
            ]

    # Also remove from cfg.strategy.instrument_timeframes
    for k in list(cfg.strategy.instrument_timeframes.keys()):
        k_upper = k.upper()
        k_clean = re.sub(r'-(EQ|BE|A|B|NSE|BSE)$', '', k_upper)
        if k_upper in symbols_to_purge or k_clean in symbols_to_purge:
            cfg.strategy.instrument_timeframes.pop(k, None)

    # Persist updated markets and instrument_timeframes to default_config.yaml atomically
    try:
        from backend.app.core.atomic_yaml import atomic_write_yaml, read_yaml
        cfg_path = Path("backend/app/config/default_config.yaml")
        raw_yaml = read_yaml(cfg_path)

        if "markets" in raw_yaml:
            for m_k, m_cfg in cfg.markets.items():
                if m_k in raw_yaml["markets"]:
                    raw_yaml["markets"][m_k]["symbols"] = m_cfg.symbols

        if "strategy" in raw_yaml and "instrument_timeframes" in raw_yaml["strategy"]:
            for k in list(raw_yaml["strategy"]["instrument_timeframes"].keys()):
                k_upper = k.upper()
                k_clean = re.sub(r'-(EQ|BE|A|B|NSE|BSE)$', '', k_upper)
                if k_upper in symbols_to_purge or k_clean in symbols_to_purge:
                    raw_yaml["strategy"]["instrument_timeframes"].pop(k, None)

        await atomic_write_yaml(cfg_path, raw_yaml)
    except Exception as e:
        logger.warning(f"Error persisting default_config.yaml on instrument removal: {e}")

    new_universe = app_state.instrument_manager.resolve_monitored_universe()

    # Re-subscribe
    delta_targets = app_state.instrument_manager.get_monitored_by_provider("delta")
    if app_state.delta_provider:
        await app_state.delta_provider.subscribe(delta_targets, cfg.strategy.timeframes)

    angel_targets = app_state.instrument_manager.get_monitored_by_provider("angelone")
    if app_state.angel_provider:
        await app_state.angel_provider.subscribe(angel_targets, cfg.strategy.timeframes)

    await ws_manager.broadcast({
        "type": "MONITORED_UPDATED",
        "data": {
            "total_monitored": len(new_universe),
            "removed_symbol": target_sym,
        },
    })

    return {
        "status": "removed",
        "symbol": target_sym,
        "total_monitored": len(new_universe),
    }


@router.post("/api/alerts/instrument-timeframes")
async def update_instrument_timeframes(req: UpdateInstrumentTimeframesRequest) -> Dict[str, Any]:
    """Update timeframes for a single specific stock/coin without altering others."""
    import asyncio
    import yaml
    from pathlib import Path
    from backend.app.main import app_state

    symbol = req.symbol.strip().upper()
    clean_tfs = [tf.strip().lower() for tf in req.timeframes if tf.strip()]
    if not clean_tfs:
        raise HTTPException(status_code=400, detail="At least one timeframe must remain active.")

    cfg = get_config()
    prev_tfs = cfg.strategy.instrument_timeframes.get(symbol) or list(cfg.strategy.timeframes)
    cfg.strategy.instrument_timeframes[symbol] = clean_tfs
    newly_added = [tf for tf in clean_tfs if tf not in prev_tfs]

    # Persist to default_config.yaml atomically
    try:
        from backend.app.core.atomic_yaml import atomic_write_yaml, read_yaml
        cfg_path = Path("backend/app/config/default_config.yaml")
        raw_yaml = read_yaml(cfg_path)

        if "strategy" not in raw_yaml:
            raw_yaml["strategy"] = {}
        if "instrument_timeframes" not in raw_yaml["strategy"]:
            raw_yaml["strategy"]["instrument_timeframes"] = {}

        raw_yaml["strategy"]["instrument_timeframes"][symbol] = clean_tfs

        await atomic_write_yaml(cfg_path, raw_yaml)
    except Exception as e:
        logger.warning(f"Could not persist instrument timeframes to config YAML: {e}")

    # If newly added timeframes, warm them up and check for missed crossovers
    if newly_added and app_state.instrument_manager and app_state.stream_manager:
        monitored = app_state.instrument_manager.get_monitored_instruments()
        clean_target = symbol.replace("-EQ", "").replace("-A", "").replace("-B", "")
        matching_inst = next(
            (i for i in monitored if i.symbol.upper() == symbol or i.symbol.upper().replace("-EQ", "") == clean_target),
            None,
        )
        if matching_inst:
            logger.info(f"Warming up newly enabled timeframes {newly_added} for {symbol}...")

            async def _warmup_and_catchup(inst, tfs):
                try:
                    await app_state.stream_manager.warm_up_instruments([inst], tfs)
                    from backend.app.main import process_startup_catchup_crossovers
                    await process_startup_catchup_crossovers(target_symbols=[inst.symbol], force_notify=True)
                except Exception as ex:
                    logger.warning(f"Error during on-demand warmup/catchup for {inst.symbol}: {ex}")

            asyncio.create_task(_warmup_and_catchup(matching_inst, newly_added))

    # Broadcast update event to all connected dashboard clients
    await ws_manager.broadcast({
        "type": "INSTRUMENT_TIMEFRAMES_UPDATED",
        "data": {
            "symbol": symbol,
            "timeframes": clean_tfs,
        },
    })

    return {
        "status": "success",
        "message": f"Updated timeframes for {symbol}: [{', '.join(clean_tfs)}]",
        "symbol": symbol,
        "timeframes": clean_tfs,
    }


@router.get("/api/notifications/status")
async def get_notifications_status() -> Dict[str, Any]:
    """Retrieve channel health and recent dispatch logs."""
    from backend.app.main import app_state

    health = {}
    if app_state.notification_manager:
        health = await app_state.notification_manager.get_health_status()

    recent_deliveries = []
    try:
        async with get_db_session() as session:
            stmt = select(NotificationDeliveryModel).order_by(desc(NotificationDeliveryModel.created_at)).limit(20)
            res = await session.execute(stmt)
            deliveries = res.scalars().all()
            recent_deliveries = [
                {
                    "id": d.id,
                    "signal_id": d.signal_id,
                    "channel": d.channel,
                    "status": d.status,
                    "attempt_count": d.attempt_count,
                    "error_message": d.error_message,
                    "sent_at": d.sent_at.isoformat() if d.sent_at else None,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in deliveries
            ]
    except Exception:
        pass

    return {
        "channels": health,
        "recent_deliveries": recent_deliveries,
    }


@router.post("/api/test-alert")
async def trigger_test_alert(req: TestAlertRequest) -> Dict[str, Any]:
    """Trigger a manual test alert across all active notification channels."""
    from backend.app.main import app_state

    if not app_state.notification_manager:
        raise HTTPException(status_code=500, detail="Notification manager not ready.")

    now = datetime.utcnow()
    sig_type = SignalType.BULLISH if req.signal_type.upper() == "BULLISH" else SignalType.BEARISH

    test_signal = SignalEvent.create(
        provider="test",
        asset_class=req.asset_class,
        exchange=req.exchange,
        instrument_id="test_token",
        symbol=req.symbol,
        timeframe=req.timeframe,
        signal_type=sig_type,
        candle_timestamp=now,
        price=req.price,
        ema100=req.ema100,
        ema200=req.ema200,
        previous_ema100=req.ema200,
        previous_ema200=req.ema100,
        strategy_version="test_v1",
    )

    results = await app_state.notification_manager.dispatch(test_signal)

    # Broadcast to dashboard websocket
    await ws_manager.broadcast({
        "type": "NEW_ALERT",
        "data": {
            "signal_id": test_signal.signal_id,
            "symbol": test_signal.symbol,
            "exchange": test_signal.exchange,
            "asset_class": test_signal.asset_class,
            "timeframe": test_signal.timeframe,
            "signal_type": test_signal.signal_type.value,
            "price": test_signal.price,
            "ema100": test_signal.ema100,
            "ema200": test_signal.ema200,
            "candle_timestamp": test_signal.candle_timestamp.isoformat(),
            "created_at": now.isoformat(),
        },
    })

    return {
        "status": "dispatched",
        "signal_id": test_signal.signal_id,
        "channel_results": results,
    }


@router.get("/api/engine/status")
async def get_engine_status() -> Dict[str, Any]:
    """Get active trading engine runtime state."""
    from backend.app.main import app_state
    is_active = getattr(app_state, "is_engine_active", True)
    action = getattr(app_state, "last_engine_action", "started")
    return {
        "is_running": is_active,
        "status": "RUNNING" if is_active else "PAUSED",
        "last_action": action,
        "angelone": "connected" if app_state.angel_provider and app_state.angel_provider.is_connected else "disconnected",
        "delta": "connected" if app_state.delta_provider and app_state.delta_provider.is_connected else "disconnected",
    }


@router.post("/api/engine/start")
async def start_engine() -> Dict[str, Any]:
    """Start or resume the real-time closed-candle indicator & alert engine."""
    import asyncio
    from backend.app.main import app_state, process_startup_catchup_crossovers

    app_state.is_engine_active = True
    app_state.last_engine_action = datetime.utcnow().isoformat()

    # Trigger Quant Startup Catch-Up scan across all monitored instruments & timeframes
    asyncio.create_task(process_startup_catchup_crossovers(force_notify=True))

    await ws_manager.broadcast({
        "type": "ENGINE_STATE_CHANGED",
        "data": {
            "is_running": True,
            "status": "RUNNING",
            "timestamp": app_state.last_engine_action,
        },
    })
    return {
        "status": "success",
        "is_running": True,
        "message": "Alert engine started. Scanning for latest prevailing crossovers across all configured timeframes...",
    }


@router.get("/api/signals/startup-catchup")
async def get_startup_catchup_crossovers() -> Dict[str, Any]:
    """Retrieve the latest active crossover for every monitored instrument across its configured timeframes."""
    from backend.app.main import process_startup_catchup_crossovers
    crossovers = await process_startup_catchup_crossovers(force_notify=False)
    return {
        "status": "success",
        "total": len(crossovers),
        "crossovers": crossovers,
    }


@router.post("/api/engine/stop")
async def stop_engine() -> Dict[str, Any]:
    """Pause closed-candle alert generation and signal dispatching."""
    from backend.app.main import app_state
    app_state.is_engine_active = False
    app_state.last_engine_action = datetime.utcnow().isoformat()
    await ws_manager.broadcast({
        "type": "ENGINE_STATE_CHANGED",
        "data": {
            "is_running": False,
            "status": "PAUSED",
            "timestamp": app_state.last_engine_action,
        },
    })
    return {"status": "success", "is_running": False, "message": "Alert engine paused safely."}


@router.websocket("/ws/dashboard")
async def dashboard_websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket connection for live dashboard streaming."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)
