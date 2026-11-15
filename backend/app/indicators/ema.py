"""High-performance incremental Exponential Moving Average (EMA) calculator."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from backend.app.models.candle import MarketCandle


@dataclass
class EMAState:
    """Stores indicator state for a specific instrument and timeframe."""

    provider: str
    exchange: str
    instrument_id: str
    symbol: str
    timeframe: str
    period_fast: int = 100
    period_slow: int = 200

    current_ema_fast: Optional[float] = None
    current_ema_slow: Optional[float] = None
    previous_ema_fast: Optional[float] = None
    previous_ema_slow: Optional[float] = None

    last_candle_time: Optional[datetime] = None
    last_close: Optional[float] = None
    bars_processed: int = 0

    @property
    def is_ready(self) -> bool:
        """Indicator is mathematically ready when sufficient bars have converged."""
        return (
            self.current_ema_fast is not None
            and self.current_ema_slow is not None
            and self.previous_ema_fast is not None
            and self.previous_ema_slow is not None
            and self.bars_processed >= self.period_slow
        )


class EMACalculator:
    """Calculates EMA 100 and EMA 200 incrementally with O(1) time complexity per bar."""

    def __init__(self, period_fast: int = 100, period_slow: int = 200) -> None:
        self.period_fast = period_fast
        self.period_slow = period_slow
        self.alpha_fast = 2.0 / (period_fast + 1.0)
        self.alpha_slow = 2.0 / (period_slow + 1.0)

    def update(self, state: EMAState, candle: MarketCandle) -> EMAState:
        """
        Incrementally update EMA values with a newly closed candle.
        Ensures previous EMA is preserved for accurate crossover detection.
        """
        close_price = candle.close

        # Save previous closed values
        if state.current_ema_fast is not None:
            state.previous_ema_fast = state.current_ema_fast
        if state.current_ema_slow is not None:
            state.previous_ema_slow = state.current_ema_slow

        # First bar initialization
        if state.bars_processed == 0:
            state.current_ema_fast = close_price
            state.current_ema_slow = close_price
            state.previous_ema_fast = close_price
            state.previous_ema_slow = close_price
        else:
            # Incremental EMA formula: EMA_t = (Close * alpha) + (EMA_{t-1} * (1 - alpha))
            state.current_ema_fast = (
                close_price * self.alpha_fast + (state.previous_ema_fast or close_price) * (1.0 - self.alpha_fast)
            )
            state.current_ema_slow = (
                close_price * self.alpha_slow + (state.previous_ema_slow or close_price) * (1.0 - self.alpha_slow)
            )

        state.bars_processed += 1
        state.last_candle_time = candle.timestamp
        state.last_close = close_price
        return state

    def warm_up(self, state: EMAState, candles: List[MarketCandle]) -> EMAState:
        """Batch warm-up from a chronological historical series of closed candles."""
        for candle in candles:
            self.update(state, candle)
        return state
