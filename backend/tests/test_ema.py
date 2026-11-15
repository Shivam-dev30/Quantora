"""Unit tests verifying mathematical correctness of EMA 100 & EMA 200 calculations."""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest
from backend.app.indicators.ema import EMACalculator, EMAState
from backend.app.models.candle import MarketCandle


def create_candle(price: float, minute_offset: int = 0) -> MarketCandle:
    return MarketCandle(
        provider="test",
        asset_class="equity",
        exchange="NSE",
        symbol="TEST",
        instrument_id="123",
        timeframe="15m",
        timestamp=datetime(2026, 10, 8, 9, 15) + timedelta(minutes=15 * minute_offset),
        open=price,
        high=price + 1.0,
        low=price - 1.0,
        close=price,
        volume=100.0,
        is_closed=True,
    )


def test_ema_alpha_multipliers():
    """Verify standard EMA smoothing factors: 2 / (N + 1)."""
    calc = EMACalculator(period_fast=100, period_slow=200)
    assert pytest.approx(calc.alpha_fast, rel=1e-5) == 2.0 / 101.0
    assert pytest.approx(calc.alpha_slow, rel=1e-5) == 2.0 / 201.0


def test_incremental_ema_matches_pandas():
    """Verify that incremental EMA values exactly match standard Pandas ewm."""
    np.random.seed(42)
    # Generate 300 random prices starting at 1000
    prices = 1000.0 + np.cumsum(np.random.randn(300) * 5.0)

    # Calculate Pandas EMA
    df = pd.DataFrame({"close": prices})
    pandas_ema100 = df["close"].ewm(span=100, adjust=False).mean().values
    pandas_ema200 = df["close"].ewm(span=200, adjust=False).mean().values

    # Calculate incremental EMA via our engine
    calc = EMACalculator(period_fast=100, period_slow=200)
    state = EMAState(
        provider="test",
        exchange="NSE",
        instrument_id="123",
        symbol="TEST",
        timeframe="15m",
    )

    for i, p in enumerate(prices):
        candle = create_candle(float(p), minute_offset=i)
        calc.update(state, candle)

        # Check precision
        assert pytest.approx(state.current_ema_fast, abs=1e-4) == pandas_ema100[i]
        assert pytest.approx(state.current_ema_slow, abs=1e-4) == pandas_ema200[i]

    assert state.is_ready is True
    assert state.bars_processed == 300


def test_ema_state_readiness_barrier():
    """State is only ready when >= 200 bars have been processed."""
    calc = EMACalculator(period_fast=100, period_slow=200)
    state = EMAState(
        provider="test",
        exchange="NSE",
        instrument_id="123",
        symbol="TEST",
        timeframe="15m",
    )

    for i in range(199):
        calc.update(state, create_candle(100.0 + i, minute_offset=i))
        assert state.is_ready is False

    # 200th bar
    calc.update(state, create_candle(300.0, minute_offset=200))
    assert state.is_ready is True
