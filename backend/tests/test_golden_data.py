"""Golden dataset tests verifying identical indicator & crossover logic across all 4 asset classes."""

from datetime import datetime, timedelta
import pytest
from backend.app.config.settings import StrategyConfig
from backend.app.database.session import init_db
from backend.app.indicators.indicator_engine import IndicatorEngine
from backend.app.models.candle import MarketCandle
from backend.app.models.signal import SignalType
from backend.app.signals.signal_engine import SignalEngine


def generate_golden_series(
    provider: str,
    asset_class: str,
    exchange: str,
    symbol: str,
    instrument_id: str,
    base_price: float,
) -> list[MarketCandle]:
    """
    Constructs a deterministic multi-regime candle sequence designed to produce:
    1. 200 flat warm-up bars at base_price (satisfies EMA200 readiness barrier)
    2. 100 decline bars at 0.7 * base_price (forces EMA100 well below EMA200)
    3. 100 rally bars at 1.4 * base_price (triggers BULLISH crossover)
    4. 100 drop bars at 0.6 * base_price (triggers BEARISH crossover)
    """
    candles = []
    start_dt = datetime(2026, 8, 1, 9, 15)

    prices = (
        [base_price] * 200
        + [base_price * 0.70] * 100
        + [base_price * 1.40] * 100
        + [base_price * 0.60] * 100
    )

    for i, price in enumerate(prices):
        ts = start_dt + timedelta(minutes=15 * i)
        candles.append(
            MarketCandle(
                provider=provider,
                asset_class=asset_class,
                exchange=exchange,
                symbol=symbol,
                instrument_id=instrument_id,
                timeframe="15m",
                timestamp=ts,
                open=round(price - 1.0, 2),
                high=round(price + 2.0, 2),
                low=round(price - 2.0, 2),
                close=round(price, 2),
                volume=1000.0,
                is_closed=True,
            )
        )
    return candles


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,asset_class,exchange,symbol,instrument_id,base_price",
    [
        ("angelone", "equity", "NSE", "RELIANCE", "2885", 1540.0),
        ("angelone", "equity_futures", "NFO", "NIFTY26OCTFUT", "35001", 25000.0),
        ("angelone", "commodity", "MCX", "CRUDEOIL19OCTFUT", "230001", 6200.0),
        ("delta", "crypto", "DELTA", "BTCUSD", "delta_btcusd", 67000.0),
    ],
)
async def test_golden_dataset_crossover_across_all_asset_classes(
    provider, asset_class, exchange, symbol, instrument_id, base_price
):
    """
    Verify that identical mathematical indicator logic produces consistent Bullish
    and Bearish crossover signals across:
    1. Indian Equities (NSE)
    2. Indian Equity F&O (NFO)
    3. Indian Commodity Futures (MCX)
    4. Cryptocurrency (Delta)
    """
    await init_db()

    strategy_cfg = StrategyConfig(ema_fast=100, ema_slow=200, timeframes=["15m"])
    indicator_engine = IndicatorEngine(strategy_cfg)

    detected_signals = []

    async def on_sig(sig):
        detected_signals.append(sig)

    signal_engine = SignalEngine(
        strategy_version=f"golden_{asset_class}",
        on_signal_detected=on_sig,
    )

    candles = generate_golden_series(
        provider=provider,
        asset_class=asset_class,
        exchange=exchange,
        symbol=symbol,
        instrument_id=instrument_id,
        base_price=base_price,
    )

    for candle in candles:
        ind_event = indicator_engine.process_closed_candle(candle)
        if ind_event:
            await signal_engine.process_indicator_update(ind_event)

    # Must have detected crossovers
    assert len(detected_signals) >= 2, f"Expected at least 2 crossovers, got {len(detected_signals)}"
    sig_types = [s.signal_type for s in detected_signals]
    assert SignalType.BULLISH in sig_types
    assert SignalType.BEARISH in sig_types

    # Find first bullish signal and verify validity
    bullish_sig = next(s for s in detected_signals if s.signal_type == SignalType.BULLISH)
    assert bullish_sig.symbol == symbol
    assert bullish_sig.exchange == exchange
    assert bullish_sig.asset_class == asset_class
    assert bullish_sig.ema100 > bullish_sig.ema200
    assert bullish_sig.previous_ema100 <= bullish_sig.previous_ema200

    # Find first bearish signal and verify validity
    bearish_sig = next(s for s in detected_signals if s.signal_type == SignalType.BEARISH)
    assert bearish_sig.symbol == symbol
    assert bearish_sig.exchange == exchange
    assert bearish_sig.ema100 < bearish_sig.ema200
    assert bearish_sig.previous_ema100 >= bearish_sig.previous_ema200
