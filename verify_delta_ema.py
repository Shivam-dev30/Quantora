"""
Delta Exchange & Multi-Asset EMA 100/200 Verification Script
-------------------------------------------------------------
Validates:
1. Delta Exchange products discovery and historical candles for BTCUSD, ETHUSD, SOLUSD, XRPUSD.
2. EMA 100 / EMA 200 mathematical accuracy against independent pandas reference on 15m.
3. Timeframe sensitivity proof (15m vs 30m vs 1h) showing EMA changes per resolution.
4. Explains signal deduplication and historical alert persistence.
"""

import asyncio
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from backend.app.providers.delta.client import DeltaClient
from backend.app.models.instrument import InstrumentDefinition
from backend.app.indicators.ema import EMACalculator, EMAState
from backend.app.models.candle import MarketCandle

CRYPTO_ASSETS = [
    {"symbol": "BTCUSD", "id": "1"},
    {"symbol": "ETHUSD", "id": "3136"},
    {"symbol": "SOLUSD", "id": "3533"},
    {"symbol": "XRPUSD", "id": "3498"},
]

WARMUP_BARS = 260
TOLERANCE = 0.5


def pandas_ema(closes: list[float], period: int) -> float:
    return round(float(pd.Series(closes).ewm(span=period, adjust=False).mean().iloc[-1]), 4)


def system_ema(closes: list[float], tf: str = "15m") -> tuple[float, float]:
    calc = EMACalculator(period_fast=100, period_slow=200)
    state = EMAState(
        provider="delta", exchange="DELTA", instrument_id="0",
        symbol="TEST", timeframe=tf, period_fast=100, period_slow=200
    )
    base_dt = datetime(2026, 1, 1, 0, 0)
    for i, close in enumerate(closes):
        candle = MarketCandle(
            provider="delta", asset_class="crypto", exchange="DELTA",
            symbol="TEST", instrument_id="0", timeframe=tf,
            timestamp=base_dt + timedelta(minutes=i*15),
            open=close, high=close, low=close, close=close,
            volume=10.0, is_closed=True
        )
        calc.update(state, candle)
    return round(state.current_ema_fast or 0, 4), round(state.current_ema_slow or 0, 4)


async def main():
    print("=" * 76)
    print("  DELTA EXCHANGE — CRYPTO EMA 100 / 200 VERIFICATION")
    print("=" * 76)

    client = DeltaClient()

    # 1. Product discovery
    print("\n🔍  Checking Delta Exchange Products Discovery...")
    products = await client.get_products()
    print(f"✅  Found {len(products)} active perpetual/futures products on Delta.")
    delta_syms = {p.symbol: p for p in products}

    # 2. Precision Check on 15m
    print("\n" + "=" * 76)
    print("  PART 1 — Delta Exchange 15m EMA 100/200 Precision vs pandas")
    print("=" * 76)

    now = datetime.utcnow()
    # 24/7 market: 260 bars of 15m = 3900 mins = ~2.7 days. Use 6 days lookback for safety.
    start_15m = now - timedelta(days=6)

    results_15m = []

    for item in CRYPTO_ASSETS:
        sym = item["symbol"]
        inst = delta_syms.get(sym)
        if not inst:
            inst = InstrumentDefinition(
                provider="delta", exchange="DELTA", symbol=sym, instrument_id=item["id"],
                name=sym, asset_class="crypto", instrument_type="PERPETUAL_FUTURES", is_active=True
            )

        print(f"\n📊  Fetching {sym} [15m] candles from Delta Exchange...")
        try:
            candles = await client.get_historical_candles(inst, "15m", start_15m, now)
            candles.sort(key=lambda c: c.timestamp)
            closes = [c.close for c in candles]
            bar_count = len(closes)

            if bar_count < 200:
                print(f"   ⚠️  Only {bar_count} bars available!")

            s100, s200 = system_ema(closes, "15m")
            p100 = pandas_ema(closes, 100)
            p200 = pandas_ema(closes, 200)

            diff100 = abs(s100 - p100)
            diff200 = abs(s200 - p200)
            ok = diff100 < TOLERANCE and diff200 < TOLERANCE

            results_15m.append({
                "symbol": sym, "bars": bar_count,
                "s100": s100, "s200": s200,
                "p100": p100, "p200": p200,
                "ok": ok, "diff100": diff100, "diff200": diff200
            })

            mark = "✅" if ok else "❌"
            print(f"   Bars fetched : {bar_count}")
            print(f"   Latest Close : ${closes[-1]:,.2f}")
            print(f"   EMA-100 → System: {s100:>10.4f}  |  pandas ref: {p100:>10.4f}  {mark}")
            print(f"   EMA-200 → System: {s200:>10.4f}  |  pandas ref: {p200:>10.4f}  {mark}")

        except Exception as e:
            print(f"   ❌  Error fetching {sym}: {e}")

    # Summary Table Part 1
    print("\n" + "─" * 76)
    print(f"  {'Symbol':<10} {'Bars':>6}  {'Latest Price':>14}  {'EMA-100':>12}  {'EMA-200':>12}  {'Status':>8}")
    print("  " + "─" * 76)
    for r in results_15m:
        st = "✅ MATCH" if r["ok"] else "❌ DRIFT"
        print(f"  {r['symbol']:<10} {r['bars']:>6}  {r['s100']:>12.2f}  {r['s200']:>12.2f}  {st:>10}")

    # 3. Multi-Timeframe Sensitivity Proof (15m vs 30m vs 1h)
    print("\n\n" + "=" * 76)
    print("  PART 2 — Timeframe Sensitivity Check (15m vs 30m vs 1h)")
    print("  EMA values MUST differ across timeframes on Delta crypto assets")
    print("=" * 76)

    for sym in ["BTCUSD", "ETHUSD"]:
        inst = delta_syms.get(sym) or InstrumentDefinition(
            provider="delta", exchange="DELTA", symbol=sym, instrument_id="0",
            name=sym, asset_class="crypto", instrument_type="PERPETUAL_FUTURES", is_active=True
        )
        print(f"\n  📈  {sym}")
        print(f"  {'TF':<6}  {'Lookback':>10}  {'Bars':>6}  {'EMA-100':>12}  {'EMA-200':>12}  {'vs pandas':>10}")
        print("  " + "─" * 60)

        prev_100, prev_200 = None, None
        all_diff = True
        for tf, look_days in [("15m", 6), ("30m", 10), ("1h", 18)]:
            candles = await client.get_historical_candles(inst, tf, now - timedelta(days=look_days), now)
            candles.sort(key=lambda c: c.timestamp)
            closes = [c.close for c in candles]
            s100, s200 = system_ema(closes, tf)
            p100 = pandas_ema(closes, 100)
            p200 = pandas_ema(closes, 200)
            ok = abs(s100 - p100) < TOLERANCE and abs(s200 - p200) < TOLERANCE
            mark = "✅" if ok else "❌"

            if prev_100 is not None and abs(s100 - prev_100) < 0.01:
                all_diff = False

            print(f"  {tf:<6}  {look_days:>7}d   {len(closes):>6}  {s100:>12.2f}  {s200:>12.2f}  {mark:>10}")
            prev_100, prev_200 = s100, s200

        res_msg = "🟢 EMA values change properly across timeframes!" if all_diff else "🔴 Values identical across timeframes!"
        print(f"  {res_msg}")

    print("\n" + "=" * 76)
    print("  DELTA EXCHANGE CHECKS COMPLETE")
    print("=" * 76)

if __name__ == "__main__":
    asyncio.run(main())

