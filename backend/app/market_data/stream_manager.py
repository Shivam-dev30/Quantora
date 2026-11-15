"""Stream Manager coordinating provider streams, historical warm-up, and gap recovery."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from backend.app.config.settings import FullSystemConfig
from backend.app.core.logging import get_logger
from backend.app.database.session import get_db_session
from backend.app.database.models import CandleMetadataModel
from backend.app.models.candle import MarketCandle
from backend.app.models.instrument import InstrumentDefinition
from backend.app.providers.base import MarketDataProvider
from backend.app.market_data.closed_candle_tracker import ClosedCandleTracker, get_timeframe_delta
from sqlalchemy import select

logger = get_logger("stream_manager")


class StreamManager:
    """Orchestrates market data providers, candle normalization, gap-filling, and closed candle feeds."""

    def __init__(
        self,
        config: FullSystemConfig,
        providers: Dict[str, MarketDataProvider],
        on_candle_closed: Any,
        on_warmup_completed: Optional[Any] = None,
    ) -> None:
        self.config = config
        self.providers = providers
        self.closed_candle_tracker = ClosedCandleTracker(on_candle_closed=on_candle_closed)
        self.on_warmup_completed = on_warmup_completed
        self._running: bool = False
        self.is_warming_up: bool = False
        self._rollover_task: Optional[asyncio.Task] = None

        # Link provider raw callbacks to closed candle tracker
        for provider in self.providers.values():
            provider.set_candle_callback(self._on_incoming_candle)

    async def _on_incoming_candle(self, candle: MarketCandle) -> None:
        """Route raw tick or closed candle through ClosedCandleTracker."""
        try:
            await self.closed_candle_tracker.process_candle(candle)
        except Exception as e:
            logger.exception(f"Error processing candle in StreamManager: {e}")

    @staticmethod
    def _warmup_lookback_days(timeframe: str, warmup_bars: int, is_crypto: bool = False) -> int:
        """
        Convert a desired number of market candles into calendar days to look back.

        EMA warm-up MUST use NATIVE-TIMEFRAME candles only — never mix timeframes.
        Mixing daily candles into a 15m/30m/1h EMA produces wrong values because
        EMA is computed on the closing price of one specific bar granularity.

        - Crypto (Delta Exchange): Trades 24/7 (1440 mins/day, 7 days/week).
        - Indian markets (NSE/MCX): Trades 9:15–15:30 IST = 375 mins/day, 5 days/week.

        Formula:
            Crypto:       calendar_days = ceil((warmup_bars × tf_minutes) / 1440 * 1.3)
            Traditional:  trading_days  = (warmup_bars × tf_minutes) / 375
                          calendar_days = ceil(trading_days × (7/5) × 1.8)
        """
        import math
        tf = timeframe.lower()
        if tf.endswith("m"):
            tf_minutes = int(tf[:-1])
        elif tf.endswith("h"):
            tf_minutes = int(tf[:-1]) * 60
        elif tf.endswith("d"):
            return max(int(warmup_bars * 1.5), 60)
        else:
            tf_minutes = 15  # safe default

        if is_crypto:
            total_minutes = warmup_bars * tf_minutes
            calendar_days = math.ceil((total_minutes / 1440.0) * 1.3)
            return max(calendar_days, 5)

        MARKET_MINS_PER_DAY = 375       # 9:15–15:30 IST
        CALENDAR_RATIO      = 7 / 5     # 5 trading days per 7 calendar days
        SAFETY              = 1.8       # buffer for holidays / API gaps

        trading_days  = (warmup_bars * tf_minutes) / MARKET_MINS_PER_DAY
        calendar_days = math.ceil(trading_days * CALENDAR_RATIO * SAFETY)
        return max(calendar_days, 30)   # always request at least 30 calendar days

    async def warm_up_instruments(
        self,
        instruments: List[InstrumentDefinition],
        timeframes: List[str],
    ) -> None:
        """
        Warm up EMA-100/200 indicator states using ONLY native-timeframe candles.

        Key design principles
        ─────────────────────
        • EMA is strictly timeframe-specific:
            - 15m EMA-200 = average of 200 × 15 min closes
            - 30m EMA-200 = average of 200 × 30 min closes   (different values!)
            - 1h  EMA-200 = average of 200 × 1 h  closes     (different values!)
          Injecting daily candles labelled as 15m/30m/1h corrupts these values and
          causes incorrect crossover signals. All timeframes must use their own bars.

        • Angel One's API caps intraday candles by CALENDAR DATE, not bar count.
          `tf_delta × 260` clock-time under-fetches because most of that window
          falls outside market hours.  `_warmup_lookback_days()` computes the
          correct calendar-day lookback covering 260+ market bars per timeframe.

        Lookback reference (260 bars target):
            15m  → ~30  calendar days  (10.4 trading days × 1.4 × 1.8)
            30m  → ~56  calendar days
            1h   → ~112 calendar days
            1d   → ~390 calendar days (not needed in practice, API has years)
        """
        self.is_warming_up = True
        try:
            warmup_bars = max(260, self.config.strategy.min_warmup_candles)
            logger.info(
                f"Warming up indicators for {len(instruments)} instruments across "
                f"{timeframes} — using native-TF candles only (target ≥ {warmup_bars} bars)..."
            )
            now = datetime.utcnow()

            for inst in instruments:
                provider = self.providers.get(inst.provider)
                if not provider:
                    continue

                is_crypto = (inst.provider == "delta" or inst.asset_class == "crypto")
                # Use per-instrument configured timeframes if set, otherwise fallback to provided timeframes
                inst_tfs = self.config.strategy.instrument_timeframes.get(inst.symbol.upper()) or timeframes

                for tf in inst_tfs:
                    # Compute market-hour-aware calendar lookback for this TF
                    lookback_days = self._warmup_lookback_days(tf, warmup_bars, is_crypto=is_crypto)
                    start_time    = now - timedelta(days=lookback_days)

                    try:
                        historical_candles = await provider.get_historical_candles(
                            instrument=inst,
                            timeframe=tf,
                            start=start_time,
                            end=now,
                        )
                        # Sort ascending (oldest → newest) so EMA builds correctly
                        historical_candles.sort(key=lambda c: c.timestamp)
                        logger.info(
                            f"Warm-up: {len(historical_candles)} × {tf} candles loaded for "
                            f"{inst.exchange}:{inst.symbol} "
                            f"(lookback {lookback_days}d, need ≥ {warmup_bars})"
                        )
                        if len(historical_candles) < 200:
                            logger.warning(
                                f"⚠ Only {len(historical_candles)} bars for "
                                f"{inst.symbol} [{tf}] — EMA-200 may not be fully converged."
                            )
                        for c in historical_candles:
                            c.is_closed = True
                            await self.closed_candle_tracker.process_candle(c)

                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch warm-up candles for {inst.symbol} [{tf}]: {e}"
                        )
        finally:
            self.is_warming_up = False
            logger.info("Warm-up bar replay completed across all instruments.")
            if self.on_warmup_completed:
                try:
                    await self.on_warmup_completed()
                except Exception as e:
                    logger.exception(f"Error executing on_warmup_completed catch-up handler: {e}")

    async def recover_missing_candles(
        self,
        provider_name: str,
        instruments: List[InstrumentDefinition],
        timeframes: List[str],
    ) -> None:
        """
        GAP RECOVERY:
        Called when a provider reconnects. Identifies last processed candle
        and fetches missed intervals to calculate missed crossovers.
        """
        logger.info(f"Checking for missed candle gaps on {provider_name}...")
        provider = self.providers.get(provider_name)
        if not provider:
            return

        now = datetime.utcnow()

        for inst in instruments:
            for tf in timeframes:
                key = (inst.provider, inst.instrument_id, tf)
                last_ts = self.closed_candle_tracker._last_closed_timestamps.get(key)
                if not last_ts:
                    continue

                tf_delta = get_timeframe_delta(tf)
                # If gap is larger than 1.5 candle intervals, fetch missed bars
                if (now - last_ts) > (tf_delta * 1.5):
                    logger.info(
                        f"Detected data gap for {inst.symbol} [{tf}]: "
                        f"Last: {last_ts.isoformat()}, Now: {now.isoformat()}. Recovering..."
                    )
                    try:
                        missed_candles = await provider.get_historical_candles(
                            instrument=inst,
                            timeframe=tf,
                            start=last_ts,
                            end=now,
                        )
                        for c in missed_candles:
                            if c.timestamp > last_ts:
                                c.is_closed = True
                                await self.closed_candle_tracker.process_candle(c)
                        logger.info(f"Recovered {len(missed_candles)} missed candles for {inst.symbol} [{tf}].")
                    except Exception as e:
                        logger.error(f"Error recovering gap for {inst.symbol} [{tf}]: {e}")

    async def _expiry_rollover_loop(self) -> None:
        """Periodic background task checking and rolling expired F&O/Commodity contracts."""
        from backend.app.api.websocket import ws_manager
        from backend.app.main import app_state

        while self._running:
            try:
                # Check every 5 minutes
                await asyncio.sleep(300)
                if not app_state.instrument_manager:
                    continue

                rolled = app_state.instrument_manager.check_and_roll_expired_contracts()
                if rolled:
                    logger.info(f"Automatically rolled {len(rolled)} expired contract(s)!")
                    for old_inst, new_inst in rolled:
                        provider = self.providers.get(new_inst.provider)
                        if provider:
                            await provider.unsubscribe([old_inst])
                            await provider.subscribe([new_inst], self.config.strategy.timeframes)
                            asyncio.create_task(
                                self.warm_up_instruments([new_inst], self.config.strategy.timeframes)
                            )

                    await ws_manager.broadcast({
                        "type": "CONTRACT_ROLLED",
                        "data": {
                            "rolled_count": len(rolled),
                            "contracts": [
                                {
                                    "old_symbol": old.symbol,
                                    "new_symbol": new.symbol,
                                    "new_expiry": new.expiry,
                                    "asset_class": new.asset_class,
                                    "exchange": new.exchange,
                                }
                                for old, new in rolled
                            ],
                        },
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in contract expiry rollover loop: {e}")

    async def start(self) -> None:
        self._running = True
        self._rollover_task = asyncio.create_task(self._expiry_rollover_loop())
        logger.info("StreamManager started with automated contract expiry rollover monitor.")

    async def stop(self) -> None:
        self._running = False
        if self._rollover_task:
            self._rollover_task.cancel()
            try:
                await self._rollover_task
            except asyncio.CancelledError:
                pass
            self._rollover_task = None

        for p in self.providers.values():
            await p.close()
        logger.info("StreamManager stopped.")
