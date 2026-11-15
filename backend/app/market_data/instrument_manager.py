"""Instrument Manager for dynamic multi-asset universe discovery, filtering, and expiry resolution."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.config.settings import FullSystemConfig, MarketConfig
from backend.app.core.logging import get_logger
from backend.app.models.instrument import InstrumentDefinition, InstrumentFilter

logger = get_logger("instrument_manager")


def parse_expiry_date(expiry_str: Optional[str]) -> Optional[date]:
    """Parse Indian exchange expiry string (e.g. '23NOV2026', '19-OCT-2026') into date object."""
    if not expiry_str:
        return None
    cleaned = expiry_str.strip().upper()
    for fmt in ("%d%b%Y", "%d-%b-%Y", "%Y-%m-%d", "%d%b%y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


class InstrumentManager:
    """Manages multi-asset instrument registry, symbol filtering, and F&O expiry selections."""

    def __init__(self, config: FullSystemConfig) -> None:
        self.config = config
        self._all_instruments: Dict[str, InstrumentDefinition] = {}  # key: f"{provider}:{instrument_id}"
        self._monitored_instruments: Dict[str, InstrumentDefinition] = {}

    def register_instruments(self, provider_name: str, instruments: List[InstrumentDefinition]) -> None:
        """Add or update instrument definitions from a provider."""
        count = 0
        for inst in instruments:
            key = f"{provider_name}:{inst.instrument_id}"
            self._all_instruments[key] = inst
            count += 1
        logger.info(f"Registered {count} instruments from {provider_name}. Total pool: {len(self._all_instruments)}")

    def resolve_monitored_universe(self) -> List[InstrumentDefinition]:
        """Filter the entire instrument universe based on system configuration."""
        monitored: Dict[str, InstrumentDefinition] = {}
        today = datetime.now().date()

        for market_key, market_cfg in self.config.markets.items():
            if not market_cfg.enabled:
                continue

            provider = market_cfg.provider.lower()
            exchange = market_cfg.exchange.upper()
            mode = market_cfg.mode.lower()
            target_symbols = {s.upper() for s in market_cfg.symbols}
            expiry_mode = (market_cfg.expiry_mode or "current").lower()

            # Find matching candidates
            candidates = [
                inst for inst in self._all_instruments.values()
                if inst.provider == provider
                and (exchange in ("ALL", "ANY") or inst.exchange.upper() == exchange)
                and inst.is_active
            ]

            if market_key in ("equity", "bse_equity"):
                # Equity cash shares (NSE & BSE)
                for inst in candidates:
                    if inst.asset_class == "equity":
                        base_sym = inst.symbol.replace("-EQ", "").replace("-A", "").replace("-B", "").upper()
                        sym_raw = inst.symbol.upper()
                        name_raw = (inst.name or "").upper()
                        matched = (
                            mode == "all"
                            or base_sym in target_symbols
                            or sym_raw in target_symbols
                            or name_raw in target_symbols
                        )
                        if matched:
                            monitored[f"{provider}:{inst.instrument_id}"] = inst

            elif market_key == "equity_futures":
                # Filter futures by underlying and unexpired dates
                grouped_futures: Dict[str, List[InstrumentDefinition]] = {}
                for inst in candidates:
                    if inst.asset_class == "equity_futures":
                        underlying = (inst.underlying or inst.name or inst.symbol).upper()
                        # Match target root symbol
                        root_match = None
                        if mode == "all":
                            root_match = underlying
                        else:
                            for target in target_symbols:
                                if underlying == target or underlying.startswith(target) or target in inst.symbol.upper():
                                    root_match = target
                                    break

                        if root_match:
                            grouped_futures.setdefault(root_match, []).append(inst)

                for root, fut_list in grouped_futures.items():
                    # Filter out expired contracts
                    valid_candidates = []
                    for f in fut_list:
                        exp_d = parse_expiry_date(f.expiry)
                        if exp_d is None or exp_d >= today:
                            valid_candidates.append(f)

                    if not valid_candidates:
                        valid_candidates = fut_list  # Fallback if all past

                    sorted_futs = sorted(
                        valid_candidates,
                        key=lambda f: (parse_expiry_date(f.expiry) or date.max, f.symbol)
                    )

                    if expiry_mode == "current" and sorted_futs:
                        selected = sorted_futs[0]
                        monitored[f"{provider}:{selected.instrument_id}"] = selected
                    elif expiry_mode == "next" and len(sorted_futs) > 1:
                        selected = sorted_futs[1]
                        monitored[f"{provider}:{selected.instrument_id}"] = selected
                    else:
                        for f in sorted_futs:
                            monitored[f"{provider}:{f.instrument_id}"] = f

            elif market_key == "commodity":
                grouped_comms: Dict[str, List[InstrumentDefinition]] = {}
                for inst in candidates:
                    if inst.asset_class == "commodity":
                        underlying = (inst.underlying or inst.name or inst.symbol).upper()
                        inst_name = (inst.name or "").upper()
                        root_match = None
                        if mode == "all":
                            root_match = underlying
                        else:
                            # 1. Exact match first so CRUDEOILM doesn't collide with CRUDEOIL
                            for target in sorted(target_symbols, key=len, reverse=True):
                                if target == underlying or target == inst_name:
                                    root_match = target
                                    break
                            # 2. Suffix / prefix match if no exact match
                            if not root_match:
                                for target in sorted(target_symbols, key=len, reverse=True):
                                    if target in underlying or target in inst.symbol.upper():
                                        root_match = target
                                        break

                        if root_match:
                            grouped_comms.setdefault(root_match, []).append(inst)

                for root, comm_list in grouped_comms.items():
                    # Filter out expired contracts
                    valid_candidates = []
                    for c in comm_list:
                        exp_d = parse_expiry_date(c.expiry)
                        if exp_d is None or exp_d >= today:
                            valid_candidates.append(c)

                    if not valid_candidates:
                        valid_candidates = comm_list

                    # Prioritize Futures (FUTCOM / *FUT) over Options (CE/PE), then sort by expiry date
                    sorted_comms = sorted(
                        valid_candidates,
                        key=lambda c: (
                            0 if (getattr(c, "instrument_type", None) or "").upper() == "FUTCOM" or c.symbol.upper().endswith("FUT") else 1,
                            parse_expiry_date(c.expiry) or date.max,
                            c.symbol
                        )
                    )

                    if expiry_mode == "current" and sorted_comms:
                        selected = sorted_comms[0]
                        monitored[f"{provider}:{selected.instrument_id}"] = selected
                    elif expiry_mode == "next" and len(sorted_comms) > 1:
                        selected = sorted_comms[1]
                        monitored[f"{provider}:{selected.instrument_id}"] = selected
                    else:
                        for c in sorted_comms:
                            monitored[f"{provider}:{c.instrument_id}"] = c

            elif market_key == "crypto":
                for inst in candidates:
                    if inst.asset_class == "crypto":
                        sym_upper = inst.symbol.upper()
                        base_sym = sym_upper.replace("USDT", "").replace("USD", "")
                        matched = (
                            mode == "all"
                            or sym_upper in target_symbols
                            or base_sym in target_symbols
                            or f"{sym_upper}T" in target_symbols
                            or sym_upper.rstrip("T") in target_symbols
                        )
                        if matched:
                            monitored[f"{provider}:{inst.instrument_id}"] = inst

        self._monitored_instruments = monitored
        logger.info(f"Resolved active monitoring universe: {len(monitored)} instruments.")
        return list(monitored.values())

    def check_and_roll_expired_contracts(self) -> List[Tuple[InstrumentDefinition, InstrumentDefinition]]:
        """
        Check all currently monitored contracts. If any F&O or Commodity contract has
        expired, automatically roll over to the active near-month replacement.
        """
        today = datetime.now().date()
        rolled: List[Tuple[InstrumentDefinition, InstrumentDefinition]] = []

        current_monitored = list(self._monitored_instruments.values())
        for inst in current_monitored:
            if inst.asset_class not in ("equity_futures", "commodity", "equity_options"):
                continue

            exp_d = parse_expiry_date(inst.expiry)
            if exp_d and exp_d < today:
                logger.warning(
                    f"Contract EXPIRED: {inst.symbol} (expired on {inst.expiry}). Rolling over to active contract..."
                )
                underlying = (inst.underlying or inst.name or inst.symbol).upper()

                # Find valid unexpired replacement candidates with same underlying and exchange
                candidates = [
                    i for i in self._all_instruments.values()
                    if i.provider == inst.provider
                    and i.exchange == inst.exchange
                    and i.asset_class == inst.asset_class
                    and (i.underlying or i.name or i.symbol).upper() == underlying
                    and (parse_expiry_date(i.expiry) or date.max) >= today
                    and i.is_active
                ]

                if candidates:
                    target_type = (getattr(inst, "instrument_type", None) or "").upper()
                    sorted_cand = sorted(
                        candidates,
                        key=lambda c: (
                            0 if (getattr(c, "instrument_type", None) or "").upper() == target_type else 1,
                            parse_expiry_date(c.expiry) or date.max,
                            c.symbol
                        )
                    )
                    replacement = sorted_cand[0]

                    old_key = f"{inst.provider}:{inst.instrument_id}"
                    new_key = f"{replacement.provider}:{replacement.instrument_id}"

                    if old_key in self._monitored_instruments:
                        del self._monitored_instruments[old_key]
                    self._monitored_instruments[new_key] = replacement

                    rolled.append((inst, replacement))
                    logger.info(
                        f"Rollover completed: {inst.symbol} ({inst.expiry}) -> {replacement.symbol} ({replacement.expiry})"
                    )

        return rolled

    def register_single_instrument(self, provider: str, inst: InstrumentDefinition) -> None:
        """Register or dynamically inject an instrument into the live catalog."""
        key = f"{provider}:{inst.instrument_id}"
        self._all_instruments[key] = inst

    async def ensure_instrument(
        self,
        symbol: str,
        exchange: str = "NSE",
        angel_provider: Any = None,
    ) -> Optional[InstrumentDefinition]:
        """
        Check if symbol exists in catalog; if missing from local scrip master,
        query live SmartAPI searchScrip endpoint, register it, and return the definition.
        """
        clean_sym = symbol.strip().upper()
        exch_upper = exchange.strip().upper()

        # 1. Search existing catalog
        for inst in self._all_instruments.values():
            if inst.exchange.upper() == exch_upper:
                base = inst.symbol.replace("-EQ", "").replace("-A", "").replace("-B", "").upper()
                if (
                    base == clean_sym
                    or inst.symbol.upper() == clean_sym
                    or (inst.name and inst.name.upper() == clean_sym)
                ):
                    return inst

        # 2. Dynamic live query via Angel One SmartAPI client if uncataloged
        if angel_provider and hasattr(angel_provider, "client"):
            try:
                results = await angel_provider.client.search_scrip(exch_upper, clean_sym)
                for item in results:
                    tradingsymbol = item.get("tradingsymbol", "")
                    token = str(item.get("symboltoken", "")).strip()
                    if token and (
                        clean_sym in tradingsymbol.upper()
                        or tradingsymbol.upper().startswith(clean_sym)
                    ):
                        new_inst = InstrumentDefinition(
                            provider="angelone",
                            exchange=exch_upper,
                            symbol=tradingsymbol,
                            instrument_id=token,
                            name=clean_sym,
                            asset_class="equity" if exch_upper in ("NSE", "BSE") else "equity_futures",
                            instrument_type="EQUITY",
                            expiry=item.get("expiry"),
                            lot_size=1,
                            tick_size=0.05,
                            is_active=True,
                            underlying=clean_sym,
                        )
                        self.register_single_instrument("angelone", new_inst)
                        logger.info(
                            f"Dynamically discovered & registered uncataloged scrip from API: {tradingsymbol} (#{token}) [{exch_upper}]"
                        )
                        return new_inst
            except Exception as e:
                logger.warning(f"Error dynamically ensuring instrument {clean_sym} on {exch_upper}: {e}")

        return None

    def search_catalog(
        self,
        query: str = "",
        category: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Lightning-fast typeahead search across all 150,000+ instruments in the catalog.
        Returns normalized items with active status, expiry, and monitoring state.
        """
        q = query.strip().upper()
        cat = (category or "").lower()
        exch = (exchange or "").upper()
        today = datetime.now().date()

        monitored_ids = set(self._monitored_instruments.keys())
        results: List[Dict[str, Any]] = []
        seen_equity_bases: Set[Tuple[str, str]] = set()

        for key, inst in self._all_instruments.items():
            # Filter by exchange
            if exch and inst.exchange.upper() != exch:
                continue

            # Filter by category
            if cat == "crypto" and inst.asset_class != "crypto":
                continue
            elif cat == "equity" and inst.asset_class != "equity":
                continue
            elif cat == "equity_nse" and (inst.asset_class != "equity" or inst.exchange.upper() != "NSE"):
                continue
            elif cat == "equity_bse" and (inst.asset_class != "equity" or inst.exchange.upper() != "BSE"):
                continue
            elif cat == "equity_futures" and inst.asset_class != "equity_futures":
                continue
            elif cat == "equity_options" and inst.asset_class != "equity_options":
                continue
            elif cat == "commodity" and inst.asset_class != "commodity":
                continue

            sym_upper = inst.symbol.upper()
            name_upper = (inst.name or "").upper()
            underlying_upper = (inst.underlying or "").upper()

            # Clean base symbol and display symbol for equities
            base_sym = sym_upper
            display_sym = inst.symbol
            if inst.asset_class == "equity":
                # Filter out clutter non-retail exchange deal series on NSE
                if inst.exchange.upper() == "NSE":
                    clutter_suffixes = ("-BL", "-IQ", "-RL", "-IL", "-BZ", "-E1", "-W1", "-MF", "-GB", "-SG")
                    if any(sym_upper.endswith(sfx) for sfx in clutter_suffixes):
                        continue
                    if sym_upper.endswith("-BE") and not q.endswith("-BE"):
                        continue

                base_sym = sym_upper.replace("-EQ", "").replace("-A", "").replace("-B", "").strip()
                display_sym = f"{base_sym}-{inst.exchange.upper()}"

                # Deduplicate by (exchange, base_sym) to avoid duplicate series clutter
                dedup_key = (inst.exchange.upper(), base_sym)
                if dedup_key in seen_equity_bases:
                    continue
                seen_equity_bases.add(dedup_key)

            # Filter by query string
            if q:
                if (
                    q not in sym_upper
                    and q not in name_upper
                    and q not in underlying_upper
                    and q not in base_sym
                    and q not in display_sym.upper()
                ):
                    continue

            # Check expiration
            exp_d = parse_expiry_date(inst.expiry)
            is_expired = (exp_d is not None and exp_d < today)
            is_mon = key in monitored_ids

            results.append({
                "symbol": inst.symbol,
                "display_symbol": display_sym,
                "base_symbol": base_sym,
                "name": inst.name or inst.symbol,
                "provider": inst.provider,
                "exchange": inst.exchange,
                "instrument_id": inst.instrument_id,
                "asset_class": inst.asset_class,
                "instrument_type": inst.instrument_type,
                "expiry": inst.expiry,
                "expiry_date": exp_d.isoformat() if exp_d else None,
                "strike": inst.strike,
                "option_type": inst.option_type,
                "lot_size": inst.lot_size,
                "tick_size": inst.tick_size,
                "is_expired": is_expired,
                "is_monitored": is_mon,
            })

            # Early limit check
            if len(results) >= limit * 6:
                break

        # Priority sort:
        # 1. Monitored items first
        # 2. Non-expired items before expired
        # 3. Exact query match on base_symbol / name / symbol
        # 4. Exchange preference (NSE before BSE, or alphabetical)
        def sort_key(item: Dict[str, Any]) -> Tuple[int, int, int, int, str]:
            mon_priority = 0 if item["is_monitored"] else 1
            exp_priority = 1 if item["is_expired"] else 0
            b_sym = item.get("base_symbol", "").upper()
            d_sym = item.get("display_symbol", "").upper()
            sym = item["symbol"].upper()
            name = item["name"].upper()
            exact_priority = 0 if (q and (q == b_sym or q == d_sym or q == sym or q == name)) else 1
            exch_priority = 0 if item["exchange"].upper() == "NSE" else 1
            return (mon_priority, exp_priority, exact_priority, exch_priority, item.get("display_symbol", item["symbol"]))

        results.sort(key=sort_key)
        return results[:limit]

    def get_instrument_by_id(self, provider: str, instrument_id: str) -> Optional[InstrumentDefinition]:
        return self._all_instruments.get(f"{provider}:{instrument_id}")

    def get_monitored_instruments(self) -> List[InstrumentDefinition]:
        return list(self._monitored_instruments.values())

    def get_monitored_by_provider(self, provider: str) -> List[InstrumentDefinition]:
        return [i for i in self._monitored_instruments.values() if i.provider == provider]

    def get_all_instruments(self) -> List[InstrumentDefinition]:
        return list(self._all_instruments.values())
