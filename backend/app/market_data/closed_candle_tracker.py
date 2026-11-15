"""Closed Candle Tracker ensuring zero intrabar false signals."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, Optional, Tuple
from backend.app.core.logging import get_logger
from backend.app.models.candle import MarketCandle

logger = get_logger("closed_candle_tracker")


def get_timeframe_delta(timeframe: str) -> timedelta:
    """Convert timeframe string to timedelta."""
    tf = timeframe.lower()
    if tf.endswith("m"):
        return timedelta(minutes=int(tf[:-1]))
    if tf.endswith("h"):
        return timedelta(hours=int(tf[:-1]))
    if tf.endswith("d"):
        return timedelta(days=int(tf[:-1]))
    return timedelta(minutes=15)


def get_candle_bucket_start(dt: datetime, timeframe: str) -> datetime:
    """Align datetime to start of timeframe window (e.g. 10:14:32 -> 10:00:00 for 15m)."""
    tf = timeframe.lower()
    if tf.endswith("m"):
        minutes = int(tf[:-1])
        floored_minute = (dt.minute // minutes) * minutes
        return dt.replace(minute=floored_minute, second=0, microsecond=0)
    elif tf.endswith("h"):
        hours = int(tf[:-1])
        floored_hour = (dt.hour // hours) * hours
        return dt.replace(hour=floored_hour, minute=0, second=0, microsecond=0)
    elif tf.endswith("d"):
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    floored_minute = (dt.minute // 15) * 15
    return dt.replace(minute=floored_minute, second=0, microsecond=0)


class ClosedCandleTracker:
    """
    Maintains forming real-time candles and guarantees that ONLY completed,
    closed candles are emitted downstream to the indicator and signal engines.
    """

    def __init__(
        self,
        on_candle_closed: Callable[[MarketCandle], Coroutine[Any, Any, None]],
    ) -> None:
        self.on_candle_closed = on_candle_closed
        # Key: (provider, instrument_id, timeframe) -> MarketCandle (forming)
        self._forming_candles: Dict[Tuple[str, str, str], MarketCandle] = {}
        # Key: (provider, instrument_id, timeframe) -> last closed candle timestamp
        self._last_closed_timestamps: Dict[Tuple[str, str, str], datetime] = {}
        self._lock = asyncio.Lock()

    async def process_candle(self, candle: MarketCandle) -> Optional[MarketCandle]:
        """
        Process incoming candle update.
        Returns the finalized closed candle if a bar boundary was crossed, else None.
        """
        key = (candle.provider, candle.instrument_id, candle.timeframe)

        # 1. If candle is already marked closed (e.g. historical load, explicit REST bar):
        if candle.is_closed:
            async with self._lock:
                last_ts = self._last_closed_timestamps.get(key)
                if last_ts and candle.timestamp <= last_ts:
                    # Ignore duplicate historical or repeated closed bar
                    return None
                self._last_closed_timestamps[key] = candle.timestamp

            await self.on_candle_closed(candle)
            return candle

        # 2. Intrabar tick / forming candle processing
        bucket_start = get_candle_bucket_start(candle.timestamp, candle.timeframe)
        closed_candle_to_emit: Optional[MarketCandle] = None

        async with self._lock:
            existing = self._forming_candles.get(key)

            if existing is None:
                # First tick in current window
                self._forming_candles[key] = MarketCandle(
                    provider=candle.provider,
                    asset_class=candle.asset_class,
                    exchange=candle.exchange,
                    symbol=candle.symbol,
                    instrument_id=candle.instrument_id,
                    timeframe=candle.timeframe,
                    timestamp=bucket_start,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                    is_closed=False,
                )
            elif existing.timestamp < bucket_start:
                # Boundary crossed! The previous forming candle is now CLOSED
                last_ts = self._last_closed_timestamps.get(key)
                if not last_ts or existing.timestamp > last_ts:
                    closed_candle_to_emit = existing.model_copy()
                    closed_candle_to_emit.is_closed = True
                    self._last_closed_timestamps[key] = existing.timestamp

                # Initialize new forming candle for the new window
                self._forming_candles[key] = MarketCandle(
                    provider=candle.provider,
                    asset_class=candle.asset_class,
                    exchange=candle.exchange,
                    symbol=candle.symbol,
                    instrument_id=candle.instrument_id,
                    timeframe=candle.timeframe,
                    timestamp=bucket_start,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                    is_closed=False,
                )
            else:
                # Same timeframe bucket: update forming candle price & volume
                existing.high = max(existing.high, candle.high)
                existing.low = min(existing.low, candle.low)
                existing.close = candle.close
                existing.volume += candle.volume

        if closed_candle_to_emit:
            logger.info(
                f"Candle CLOSED: {closed_candle_to_emit.exchange}:{closed_candle_to_emit.symbol} "
                f"[{closed_candle_to_emit.timeframe}] Close={closed_candle_to_emit.close} "
                f"Time={closed_candle_to_emit.timestamp.isoformat()}"
            )
            await self.on_candle_closed(closed_candle_to_emit)
            return closed_candle_to_emit

        return None
