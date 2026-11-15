"""Signal Engine coordinating crossover detection, deduplication, and alert generation."""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Optional
from backend.app.core.logging import get_logger
from backend.app.indicators.indicator_engine import IndicatorUpdatedEvent
from backend.app.models.signal import SignalEvent, SignalType
from backend.app.signals.crossover_detector import CrossoverDetector
from backend.app.signals.deduplicator import SignalDeduplicator

logger = get_logger("signal_engine")


@dataclass
class SignalDetectedEvent:
    """Event emitted when a unique, non-duplicate crossover signal is registered."""

    signal: SignalEvent


class SignalEngine:
    """Detects EMA 100/200 crossovers on closed candles and deduplicates alerts."""

    def __init__(
        self,
        strategy_version: str = "ema100_200_v1",
        on_signal_detected: Optional[Callable[[SignalEvent], Coroutine[Any, Any, None]]] = None,
    ) -> None:
        self.strategy_version = strategy_version
        self.detector = CrossoverDetector()
        self.deduplicator = SignalDeduplicator()
        self.on_signal_detected = on_signal_detected

    async def initialize(self) -> None:
        """Restore signal state from database to prevent post-restart duplicate alerts."""
        await self.deduplicator.restore_from_db()

    async def process_indicator_update(self, event: IndicatorUpdatedEvent) -> Optional[SignalEvent]:
        """
        Check for bullish or bearish crossover.
        Only executed for closed candles with valid EMA history.
        """
        state = event.state
        candle = event.candle

        if (
            state.previous_ema_fast is None
            or state.previous_ema_slow is None
            or state.current_ema_fast is None
            or state.current_ema_slow is None
        ):
            return None

        # Check for crossover
        signal_type = self.detector.detect(
            prev_fast=state.previous_ema_fast,
            prev_slow=state.previous_ema_slow,
            curr_fast=state.current_ema_fast,
            curr_slow=state.current_ema_slow,
        )

        if signal_type == SignalType.NONE:
            return None

        # Create candidate SignalEvent
        signal = SignalEvent.create(
            provider=candle.provider,
            asset_class=candle.asset_class,
            exchange=candle.exchange,
            instrument_id=candle.instrument_id,
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            signal_type=signal_type,
            candle_timestamp=candle.timestamp,
            price=candle.close,
            ema100=state.current_ema_fast,
            ema200=state.current_ema_slow,
            previous_ema100=state.previous_ema_fast,
            previous_ema200=state.previous_ema_slow,
            strategy_version=self.strategy_version,
        )

        # Deduplicate & Persist
        is_new = await self.deduplicator.register_signal(signal)
        if not is_new:
            return None

        logger.info(
            f"⚡ CROSSOVER DETECTED: {signal.signal_type.value} on {signal.exchange}:{signal.symbol} "
            f"[{signal.timeframe}] Price={signal.price} EMA100={signal.ema100:.2f} EMA200={signal.ema200:.2f}"
        )

        if self.on_signal_detected:
            await self.on_signal_detected(signal)

        return signal
