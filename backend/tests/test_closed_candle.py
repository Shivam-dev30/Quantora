"""Unit tests verifying strict closed-candle logic and zero intrabar false signals."""

import asyncio
from datetime import datetime
import pytest
from backend.app.market_data.closed_candle_tracker import ClosedCandleTracker
from backend.app.models.candle import MarketCandle


@pytest.mark.asyncio
async def test_intrabar_ticks_do_not_emit_closed_candles():
    """Forming candles within the same 15m window must NEVER emit closed candle signals."""
    emitted_candles = []

    async def on_closed(c: MarketCandle):
        emitted_candles.append(c)

    tracker = ClosedCandleTracker(on_candle_closed=on_closed)

    # Tick 1 at 10:01:00
    c1 = MarketCandle(
        provider="angelone",
        asset_class="equity",
        exchange="NSE",
        symbol="RELIANCE",
        instrument_id="2885",
        timeframe="15m",
        timestamp=datetime(2026, 10, 8, 10, 1, 0),
        open=1500.0,
        high=1505.0,
        low=1498.0,
        close=1502.0,
        volume=100.0,
        is_closed=False,
    )
    await tracker.process_candle(c1)
    assert len(emitted_candles) == 0  # Not closed!

    # Tick 2 at 10:14:59 (still inside 10:00-10:15 window)
    c2 = MarketCandle(
        provider="angelone",
        asset_class="equity",
        exchange="NSE",
        symbol="RELIANCE",
        instrument_id="2885",
        timeframe="15m",
        timestamp=datetime(2026, 10, 8, 10, 14, 59),
        open=1500.0,
        high=1520.0,
        low=1498.0,
        close=1518.0,
        volume=250.0,
        is_closed=False,
    )
    await tracker.process_candle(c2)
    assert len(emitted_candles) == 0  # Still forming, zero intrabar emissions!

    # Tick 3 at 10:15:01 (New bucket begins! Previous 10:00-10:15 candle MUST close now)
    c3 = MarketCandle(
        provider="angelone",
        asset_class="equity",
        exchange="NSE",
        symbol="RELIANCE",
        instrument_id="2885",
        timeframe="15m",
        timestamp=datetime(2026, 10, 8, 10, 15, 1),
        open=1518.0,
        high=1519.0,
        low=1517.0,
        close=1518.5,
        volume=50.0,
        is_closed=False,
    )
    await tracker.process_candle(c3)

    assert len(emitted_candles) == 1
    finalized = emitted_candles[0]
    assert finalized.is_closed is True
    assert finalized.timestamp == datetime(2026, 10, 8, 10, 0, 0)
    assert finalized.open == 1500.0
    assert finalized.high == 1520.0  # Captured maximum across ticks
    assert finalized.low == 1498.0   # Captured minimum
    assert finalized.close == 1518.0 # Final tick close before boundary


@pytest.mark.asyncio
async def test_duplicate_closed_candle_ignored():
    """Duplicate closed candles with identical timestamp must not be emitted twice."""
    emitted_candles = []

    async def on_closed(c: MarketCandle):
        emitted_candles.append(c)

    tracker = ClosedCandleTracker(on_candle_closed=on_closed)

    closed_bar = MarketCandle(
        provider="angelone",
        asset_class="equity",
        exchange="NSE",
        symbol="RELIANCE",
        instrument_id="2885",
        timeframe="15m",
        timestamp=datetime(2026, 10, 8, 10, 0, 0),
        open=1500.0,
        high=1510.0,
        low=1495.0,
        close=1505.0,
        volume=1000.0,
        is_closed=True,
    )

    # First emission
    res1 = await tracker.process_candle(closed_bar)
    assert res1 is not None
    assert len(emitted_candles) == 1

    # Replay of same candle
    res2 = await tracker.process_candle(closed_bar)
    assert res2 is None
    assert len(emitted_candles) == 1  # Duplicate suppressed!
