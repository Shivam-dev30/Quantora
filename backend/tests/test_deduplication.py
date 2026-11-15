"""Unit tests for signal identity generation and database deduplication."""

from datetime import datetime
import pytest
from backend.app.database.session import init_db
from backend.app.models.signal import SignalEvent, SignalType, generate_signal_id
from backend.app.signals.deduplicator import SignalDeduplicator


@pytest.mark.asyncio
async def test_deterministic_signal_id():
    """Ensure generate_signal_id produces strictly identical output for identical inputs."""
    ts = datetime(2026, 10, 9, 10, 15, 0)
    sig_id_1 = generate_signal_id(
        provider="angelone",
        exchange="NSE",
        instrument_id="2885",
        timeframe="15m",
        candle_timestamp=ts,
        signal_type=SignalType.BULLISH,
        strategy_version="ema100_200_v1",
    )
    sig_id_2 = generate_signal_id(
        provider="angelone",
        exchange="NSE",
        instrument_id="2885",
        timeframe="15m",
        candle_timestamp=ts,
        signal_type="BULLISH",
        strategy_version="ema100_200_v1",
    )
    assert sig_id_1 == sig_id_2
    assert sig_id_1 == "angelone:NSE:2885:15m:2026-10-09T10:15:00Z:BULLISH:ema100_200_v1"


@pytest.mark.asyncio
async def test_deduplicator_prevents_duplicate_signals():
    """Verify deduplicator allows the first occurrence and drops all duplicates."""
    await init_db()
    dedup = SignalDeduplicator()

    ts = datetime(2026, 10, 9, 11, 0, 0)
    signal = SignalEvent.create(
        provider="angelone",
        asset_class="equity",
        exchange="NSE",
        instrument_id="2885",
        symbol="RELIANCE",
        timeframe="15m",
        signal_type=SignalType.BULLISH,
        candle_timestamp=ts,
        price=1550.0,
        ema100=1545.0,
        ema200=1540.0,
        previous_ema100=1539.0,
        previous_ema200=1541.0,
    )

    # 1. First registration must SUCCEED
    is_new = await dedup.register_signal(signal)
    assert is_new is True

    # 2. Immediate duplicate must be REJECTED
    is_duplicate = await dedup.register_signal(signal)
    assert is_duplicate is False

    # 3. Simulate process restart: fresh deduplicator restored from DB must STILL reject!
    fresh_dedup = SignalDeduplicator()
    await fresh_dedup.restore_from_db()

    is_duplicate_after_restart = await fresh_dedup.register_signal(signal)
    assert is_duplicate_after_restart is False


@pytest.mark.asyncio
async def test_different_timeframes_produce_distinct_signals():
    """Different timeframes for the same symbol must be treated as independent signals."""
    await init_db()
    dedup = SignalDeduplicator()
    ts = datetime(2026, 10, 9, 12, 0, 0)

    sig_5m = SignalEvent.create(
        provider="delta",
        asset_class="crypto",
        exchange="DELTA",
        instrument_id="BTCUSD",
        symbol="BTCUSD",
        timeframe="5m",
        signal_type=SignalType.BULLISH,
        candle_timestamp=ts,
        price=67500.0,
        ema100=67400.0,
        ema200=67350.0,
        previous_ema100=67300.0,
        previous_ema200=67320.0,
    )

    sig_15m = SignalEvent.create(
        provider="delta",
        asset_class="crypto",
        exchange="DELTA",
        instrument_id="BTCUSD",
        symbol="BTCUSD",
        timeframe="15m",
        signal_type=SignalType.BULLISH,
        candle_timestamp=ts,
        price=67500.0,
        ema100=67400.0,
        ema200=67350.0,
        previous_ema100=67300.0,
        previous_ema200=67320.0,
    )

    assert await dedup.register_signal(sig_5m) is True
    assert await dedup.register_signal(sig_15m) is True
