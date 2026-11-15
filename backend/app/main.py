"""Main entry point for the Multi-Asset Market Alert Platform."""

import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, select
from backend.app.api.routes import router as api_router
from backend.app.api.websocket import ws_manager
from backend.app.config.settings import FullSystemConfig, get_config
from backend.app.core.event_bus import EventBus, get_event_bus
from backend.app.core.logging import get_logger, setup_logging
from backend.app.database.models import SignalModel
from backend.app.database.session import get_db_session, init_db
from backend.app.indicators.indicator_engine import IndicatorEngine
from backend.app.market_data.instrument_manager import InstrumentManager
from backend.app.market_data.stream_manager import StreamManager
from backend.app.models.candle import MarketCandle
from backend.app.models.signal import SignalEvent, SignalType
from backend.app.notifications.notification_manager import NotificationManager
from backend.app.providers.angelone.provider import AngelOneProvider
from backend.app.providers.delta.provider import DeltaExchangeProvider
from backend.app.signals.signal_engine import SignalEngine

logger = get_logger("main")


@dataclass
class ApplicationState:
    config: Optional[FullSystemConfig] = None
    event_bus: Optional[EventBus] = None
    angel_provider: Optional[AngelOneProvider] = None
    delta_provider: Optional[DeltaExchangeProvider] = None
    instrument_manager: Optional[InstrumentManager] = None
    stream_manager: Optional[StreamManager] = None
    indicator_engine: Optional[IndicatorEngine] = None
    signal_engine: Optional[SignalEngine] = None
    notification_manager: Optional[NotificationManager] = None
    is_engine_active: bool = True
    last_engine_action: str = "started"
    latest_historical_crossovers: Dict[Any, SignalEvent] = field(default_factory=dict)
    startup_notified_keys: Set[str] = field(default_factory=set)


app_state = ApplicationState()


async def on_candle_closed(candle: MarketCandle) -> None:
    """Invoked whenever a candle is fully finalized and closed."""
    if not app_state.is_engine_active:
        return

    if not app_state.indicator_engine or not app_state.signal_engine:
        return

    # Check per-instrument timeframes:
    cfg = get_config()
    symbol_upper = candle.symbol.upper()
    if symbol_upper in cfg.strategy.instrument_timeframes:
        if candle.timeframe not in cfg.strategy.instrument_timeframes[symbol_upper]:
            return
    elif candle.timeframe not in cfg.strategy.timeframes:
        return

    # 1. Update EMA indicators
    indicator_event = app_state.indicator_engine.process_closed_candle(candle)
    if not indicator_event:
        return

    state = indicator_event.state

    # Track latest historical crossover during warm-up replay
    if (
        state.previous_ema_fast is not None
        and state.previous_ema_slow is not None
        and state.current_ema_fast is not None
        and state.current_ema_slow is not None
    ):
        sig_type = app_state.signal_engine.detector.detect(
            prev_fast=state.previous_ema_fast,
            prev_slow=state.previous_ema_slow,
            curr_fast=state.current_ema_fast,
            curr_slow=state.current_ema_slow,
        )
        if sig_type != SignalType.NONE:
            sig = SignalEvent.create(
                provider=candle.provider,
                asset_class=candle.asset_class,
                exchange=candle.exchange,
                instrument_id=candle.instrument_id,
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                signal_type=sig_type,
                candle_timestamp=candle.timestamp,
                price=candle.close,
                ema100=state.current_ema_fast,
                ema200=state.current_ema_slow,
                previous_ema100=state.previous_ema_fast,
                previous_ema200=state.previous_ema_slow,
                strategy_version=app_state.signal_engine.strategy_version,
                is_catchup=True,
            )
            key = (candle.provider, candle.instrument_id, candle.timeframe)
            app_state.latest_historical_crossovers[key] = sig
            app_state.latest_historical_crossovers[(candle.symbol.upper(), candle.timeframe)] = sig
            clean_s = candle.symbol.upper().replace("-EQ", "")
            app_state.latest_historical_crossovers[(clean_s, candle.timeframe)] = sig

    # Skip alerting on historical candles during initial indicator warm-up
    if app_state.stream_manager and getattr(app_state.stream_manager, "is_warming_up", False):
        return

    # 2. Check for Crossover & Deduplicate
    signal = await app_state.signal_engine.process_indicator_update(indicator_event)
    if not signal:
        return

    # Latency guard: suppress urgent push notifications for historical/stale candles (e.g. from gap recovery)
    from datetime import datetime
    from backend.app.market_data.closed_candle_tracker import get_timeframe_delta

    now_utc = datetime.utcnow()
    tf_delta = get_timeframe_delta(signal.timeframe)
    candle_age_sec = (now_utc - signal.candle_timestamp).total_seconds()
    max_push_latency_sec = max(tf_delta.total_seconds() * 2.5, 900.0)  # at most 15 min or 2.5 bars
    is_realtime_candle = candle_age_sec <= max_push_latency_sec

    # 3. Dispatch to notification channels (Telegram, Email, WhatsApp) for live real-time candles
    if app_state.notification_manager:
        if is_realtime_candle:
            await app_state.notification_manager.dispatch(signal)
        else:
            logger.info(
                f"Suppressed stale notification dispatch for {signal.symbol} [{signal.timeframe}] "
                f"candle from {signal.candle_timestamp.isoformat()} (age: {candle_age_sec / 60.0:.1f} mins ago)."
            )

    # 4. Push to connected dashboard browsers with explicit UTC ISO string
    cts = signal.candle_timestamp.isoformat()
    if not cts.endswith("Z") and "+" not in cts:
        cts += "Z"
    crts = signal.created_at.isoformat()
    if not crts.endswith("Z") and "+" not in crts:
        crts += "Z"

    await ws_manager.broadcast({
        "type": "NEW_ALERT",
        "data": {
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
            "exchange": signal.exchange,
            "asset_class": signal.asset_class,
            "timeframe": signal.timeframe,
            "signal_type": signal.signal_type.value,
            "price": signal.price,
            "ema100": signal.ema100,
            "ema200": signal.ema200,
            "previous_ema100": signal.previous_ema100,
            "previous_ema200": signal.previous_ema200,
            "candle_timestamp": cts,
            "created_at": crts,
            "is_catchup": getattr(signal, "is_catchup", False),
        },
    })


async def process_startup_catchup_crossovers(
    target_symbols: Optional[List[str]] = None,
    force_notify: bool = True,
) -> List[Dict[str, Any]]:
    """
    Quant Startup / Online Synchronization Protocol:
    Audits every monitored instrument and its user-configured execution timeframes.
    Identifies the EXACT LAST CROSSOVER that occurred prior to or up to startup time.
    Calculates quant execution metrics:
      - Trigger price vs current market price
      - Drift in points and % slippage/gain
      - Confirms if prevailing indicator regime is still ACTIVE
    Dispatches professional [STARTUP CATCH-UP] alerts to:
      1. Telegram (and active channels) with complete trade context
      2. Web terminal via WebSocket
      3. SQLite database with is_catchup=True flag
    Returns structured list of audited startup crossovers.
    """
    if not app_state.instrument_manager or not app_state.signal_engine:
        return []

    cfg = get_config()
    monitored = app_state.instrument_manager.get_monitored_instruments()
    if target_symbols:
        t_set = {s.strip().upper() for s in target_symbols}
        t_clean = {s.replace("-EQ", "").replace("-A", "").replace("-B", "") for s in t_set}
        monitored = [
            i for i in monitored
            if i.symbol.upper() in t_set or i.symbol.upper().replace("-EQ", "") in t_clean
        ]

    logger.info(
        f"🔍 [QUANT STARTUP AUDIT] Evaluating last prevailing crossovers across "
        f"{len(monitored)} monitored instruments..."
    )

    results: List[Dict[str, Any]] = []

    for inst in monitored:
        sym_upper = inst.symbol.upper()
        clean_sym = sym_upper.replace("-EQ", "").replace("-A", "").replace("-B", "")

        # User's exact configured timeframes for this specific stock
        stock_tfs = (
            cfg.strategy.instrument_timeframes.get(sym_upper)
            or cfg.strategy.instrument_timeframes.get(clean_sym)
            or cfg.strategy.timeframes
        )

        for tf in stock_tfs:
            # 1. Lookup in-memory latest historical crossover
            signal: Optional[SignalEvent] = (
                app_state.latest_historical_crossovers.get((sym_upper, tf))
                or app_state.latest_historical_crossovers.get((clean_sym, tf))
                or app_state.latest_historical_crossovers.get((inst.provider, inst.instrument_id, tf))
            )

            # 2. If not found in memory, check SQLite DB for the most recent recorded signal
            if not signal:
                try:
                    async with get_db_session() as session:
                        stmt = (
                            select(SignalModel)
                            .where(
                                (SignalModel.symbol == inst.symbol)
                                | (SignalModel.symbol == clean_sym)
                                | (SignalModel.symbol == sym_upper),
                                SignalModel.timeframe == tf,
                            )
                            .order_by(desc(SignalModel.candle_timestamp))
                            .limit(1)
                        )
                        res = await session.execute(stmt)
                        row = res.scalar_one_or_none()
                        if row:
                            signal = SignalEvent.create(
                                provider=row.provider,
                                asset_class=row.asset_class,
                                exchange=row.exchange,
                                instrument_id=row.instrument_id,
                                symbol=row.symbol,
                                timeframe=row.timeframe,
                                signal_type=SignalType(row.signal_type),
                                candle_timestamp=row.candle_timestamp,
                                price=row.price,
                                ema100=row.ema100,
                                ema200=row.ema200,
                                previous_ema100=row.previous_ema100,
                                previous_ema200=row.previous_ema200,
                                strategy_version=row.strategy_version,
                                is_catchup=True,
                            )
                except Exception as e:
                    logger.warning(f"DB fallback query error for {inst.symbol} [{tf}]: {e}")

            if not signal:
                logger.debug(f"No crossover detected yet for {inst.symbol} [{tf}] within lookback window.")
                continue

            # Ensure is_catchup flag is True
            signal.is_catchup = True

            # 3. Quant metrics: Current price, indicator state, drift calculation
            state = None
            if app_state.indicator_engine:
                state = app_state.indicator_engine.get_state(inst.provider, inst.instrument_id, tf)

            current_price = getattr(state, "last_close", None) or signal.price
            drift_pts = round(current_price - signal.price, 4)
            drift_pct = round((drift_pts / signal.price) * 100, 2) if signal.price else 0.0

            # Elapsed time calculation
            now_utc = datetime.utcnow()
            age_sec = (now_utc - signal.candle_timestamp).total_seconds()
            hrs = int(age_sec // 3600)
            mins = int((age_sec % 3600) // 60)
            elapsed_str = f"{hrs}h {mins}m ago" if hrs > 0 else f"{mins}m ago"

            # Check if current regime matches the crossover
            is_active_regime = True
            if state and state.is_ready:
                is_bull = (state.current_ema_fast or 0) > (state.current_ema_slow or 0)
                is_active_regime = (
                    (signal.signal_type == SignalType.BULLISH and is_bull)
                    or (signal.signal_type == SignalType.BEARISH and not is_bull)
                )

            # 4. Save to Database / Update deduplicator
            is_new = await app_state.signal_engine.deduplicator.register_signal(signal)
            if not is_new:
                # Mark as catchup in existing DB record
                await app_state.signal_engine.deduplicator.mark_catchup(signal.signal_id)

            # 5. Session notification deduplication check
            notify_key = f"{signal.symbol}:{signal.timeframe}:{signal.candle_timestamp.isoformat()}"
            should_notify = force_notify or (notify_key not in app_state.startup_notified_keys)

            if should_notify:
                app_state.startup_notified_keys.add(notify_key)

                logger.info(
                    f"🚀 [STARTUP CATCH-UP SIGNAL] Dispatched last {signal.signal_type.value} on "
                    f"{signal.symbol} [{signal.timeframe}] from {signal.candle_timestamp.isoformat()} | "
                    f"Trigger: {signal.price} -> Current: {current_price} ({drift_pct:+.2f}%) "
                    f"[Prevailing Active Regime]"
                )

                # Dispatch to Notification Channels (Telegram, etc.)
                if app_state.notification_manager:
                    try:
                        await app_state.notification_manager.dispatch(
                            signal=signal,
                            current_price=current_price,
                            drift_points=drift_pts,
                            drift_percent=drift_pct,
                            elapsed_time_str=elapsed_str,
                        )
                    except Exception as e:
                        logger.warning(f"Error dispatching startup catch-up alert to channels: {e}")

                # Push to WebSocket Clients
                cts = signal.candle_timestamp.isoformat()
                if not cts.endswith("Z") and "+" not in cts:
                    cts += "Z"
                crts = signal.created_at.isoformat()
                if not crts.endswith("Z") and "+" not in crts:
                    crts += "Z"

                await ws_manager.broadcast({
                    "type": "NEW_ALERT",
                    "data": {
                        "signal_id": signal.signal_id,
                        "symbol": signal.symbol,
                        "exchange": signal.exchange,
                        "asset_class": signal.asset_class,
                        "timeframe": signal.timeframe,
                        "signal_type": signal.signal_type.value,
                        "price": signal.price,
                        "current_price": current_price,
                        "drift_points": drift_pts,
                        "drift_percent": drift_pct,
                        "ema100": signal.ema100,
                        "ema200": signal.ema200,
                        "previous_ema100": signal.previous_ema100,
                        "previous_ema200": signal.previous_ema200,
                        "candle_timestamp": cts,
                        "created_at": crts,
                        "is_catchup": True,
                    },
                })

            results.append({
                "symbol": signal.symbol,
                "exchange": signal.exchange,
                "asset_class": signal.asset_class,
                "timeframe": signal.timeframe,
                "signal_type": signal.signal_type.value,
                "crossover_time": signal.candle_timestamp.isoformat(),
                "trigger_price": signal.price,
                "current_price": current_price,
                "drift_points": drift_pts,
                "drift_percent": drift_pct,
                "elapsed_time": elapsed_str,
                "ema100": signal.ema100,
                "ema200": signal.ema200,
                "is_active_regime": is_active_regime,
            })

    logger.info(f"✅ Startup catch-up audit complete: {len(results)} prevailing setups processed.")
    return results


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orchestrates comprehensive startup and graceful shutdown sequences."""
    # 1. Load configuration and setup logging
    cfg = get_config()
    setup_logging(log_level=cfg.settings.log_level)
    logger.info("Starting Multi-Asset Market Alert Platform (Strictly Alert-Only)...")
    app_state.config = cfg

    # 2. Initialize Database & Event Bus
    await init_db()
    bus = get_event_bus()
    await bus.start()
    app_state.event_bus = bus

    # 3. Initialize Providers
    logger.info("Initializing market data providers...")
    angel = AngelOneProvider(
        api_key=cfg.settings.angel_api_key,
        client_code=cfg.settings.angel_client_code,
        password=cfg.settings.angel_password,
        totp_secret=cfg.settings.angel_totp_secret,
    )
    await angel.initialize()
    app_state.angel_provider = angel

    delta = DeltaExchangeProvider(
        rest_url=cfg.settings.delta_rest_url,
        ws_url=cfg.settings.delta_ws_url,
        api_key=cfg.settings.delta_api_key,
        api_secret=cfg.settings.delta_api_secret,
    )
    await delta.initialize()
    app_state.delta_provider = delta

    # 4. Instrument Discovery & Dynamic Universe Resolution
    inst_mgr = InstrumentManager(cfg)
    inst_mgr.register_instruments("angelone", await angel.get_instruments())
    inst_mgr.register_instruments("delta", await delta.get_instruments())
    monitored_universe = inst_mgr.resolve_monitored_universe()
    app_state.instrument_manager = inst_mgr

    # 5. Initialize Indicator Engine & Signal Engine
    app_state.indicator_engine = IndicatorEngine(cfg.strategy)
    app_state.signal_engine = SignalEngine(strategy_version=cfg.strategy.version)
    await app_state.signal_engine.initialize()

    # 6. Initialize Notification Manager
    app_state.notification_manager = NotificationManager(cfg)

    # 7. Initialize Stream Manager & Closed Candle Pipeline
    stream_mgr = StreamManager(
        config=cfg,
        providers={"angelone": angel, "delta": delta},
        on_candle_closed=on_candle_closed,
        on_warmup_completed=process_startup_catchup_crossovers,
    )
    app_state.stream_manager = stream_mgr

    # 8. Subscribe to Real-Time Feeds
    angel_targets = inst_mgr.get_monitored_by_provider("angelone")
    if angel_targets:
        await angel.subscribe(angel_targets, cfg.strategy.timeframes)

    delta_targets = inst_mgr.get_monitored_by_provider("delta")
    if delta_targets:
        await delta.subscribe(delta_targets, cfg.strategy.timeframes)

    await stream_mgr.start()

    # 9. Warm Up Historical Candles in background
    asyncio.create_task(stream_mgr.warm_up_instruments(monitored_universe, cfg.strategy.timeframes))
    logger.info("Platform initialization complete. System status: HEALTHY 🟢")

    yield

    # Graceful Shutdown
    logger.info("Shutting down Multi-Asset Market Alert Platform...")
    if app_state.stream_manager:
        await app_state.stream_manager.stop()
    if app_state.angel_provider:
        await app_state.angel_provider.close()
    if app_state.delta_provider:
        await app_state.delta_provider.close()
    if app_state.event_bus:
        await app_state.event_bus.stop()
    logger.info("Graceful shutdown completed successfully.")


def create_app(lifespan_handler: Optional[Any] = lifespan) -> FastAPI:
    """Create configured FastAPI application."""
    app = FastAPI(
        title="Multi-Asset Market Alert Platform",
        description="Production-grade real-time market alert engine for Indian stocks, F&O, commodities, and crypto.",
        version="1.0.0",
        lifespan=lifespan_handler,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    # Mount compiled frontend terminal if present
    frontend_dist = Path("frontend/dist")
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    cfg = get_config()
    uvicorn.run("backend.app.main:app", host=cfg.settings.host, port=cfg.settings.port, reload=False)
