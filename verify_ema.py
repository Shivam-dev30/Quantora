"""
EMA 100 & 200 Verification Script
-----------------------------------
Validates the system's EMACalculator against:
  1. pandas ewm(adjust=False) — independent mathematical reference
  2. User-provided TradingView reference values on 15m timeframe

Also proves EMA values CHANGE correctly across timeframes (15m vs 30m vs 1h).

Warm-up uses ONLY native-TF candles with market-hour-aware calendar lookback —
no cross-timeframe mixing (which was the previous bug causing wrong values).
"""

import asyncio
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── Load .env ──────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

import pandas as pd
import pytz

from backend.app.providers.angelone.auth import AngelOneAuthManager
from backend.app.providers.angelone.client import AngelOneClient
from backend.app.models.instrument import InstrumentDefinition
from backend.app.indicators.ema import EMACalculator, EMAState
from backend.app.models.candle import MarketCandle

IST = pytz.timezone("Asia/Kolkata")

# ── Stocks to verify ───────────────────────────────────────────────────────────
STOCKS = [
    {"symbol": "RELIANCE", "token": "2885",     "exchange": "NSE"},
    {"symbol": "TCS",      "token": "11536",    "exchange": "NSE"},
    {"symbol": "INFY",     "token": "1594",     "exchange": "NSE"},
    {"symbol": "HDFCBANK", "token": "1333",     "exchange": "NSE"},
    {"symbol": "NIFTY 50", "token": "99926000", "exchange": "NSE"},
]

# User-provided TradingView reference values (15m timeframe)
TV_REFERENCE = {
    "RELIANCE": {"ema100": 1284.44, "ema200": 1253.59},
    "TCS":      {"ema100": 2481.99, "ema200": 2476.61},
    "INFY":     {"ema100": 1149.03, "ema200": 1144.75},
}

WARMUP_BARS = 260       # target number of native-TF bars
TOLERANCE   = 2.0       # max acceptable drift vs pandas reference (₹)
TV_TOLERANCE = 15.0     # max acceptable drift vs TradingView (₹) — TV uses
                        # slightly different EMA initialization & session filters

MARKET_MINS_PER_DAY = 375   # 9:15–15:30 IST


def warmup_lookback_days(timeframe: str, bars: int) -> int:
    """Market-hour-aware calendar lookback — mirrors StreamManager._warmup_lookback_days()."""
    tf = timeframe.lower()
    if tf.endswith("m"):
        tf_min = int(tf[:-1])
    elif tf.endswith("h"):
        tf_min = int(tf[:-1]) * 60
    elif tf.endswith("d"):
        return max(int(bars * 1.5), 60)
    else:
        tf_min = 15
    trading_days = (bars * tf_min) / MARKET_MINS_PER_DAY
    cal_days = math.ceil(trading_days * (7 / 5) * 1.8)
    return max(cal_days, 30)


def pandas_ema(closes: list[float], period: int) -> float:
    """EMA via pandas ewm(adjust=False) — matches TradingView's RMA-style EMA."""
    return round(float(pd.Series(closes).ewm(span=period, adjust=False).mean().iloc[-1]), 4)


def system_ema(closes: list[float], tf: str = "15m") -> tuple[float, float]:
    """Run the system's own EMACalculator on a close-price list."""
    calc  = EMACalculator(period_fast=100, period_slow=200)
    state = EMAState(
        provider="angelone", exchange="NSE",
        instrument_id="0", symbol="TEST", timeframe=tf,
        period_fast=100, period_slow=200,
    )
    base_dt = datetime(2026, 1, 1, 9, 15)
    for i, close in enumerate(closes):
        candle = MarketCandle(
            provider="angelone", asset_class="equity",
            exchange="NSE", symbol="TEST", instrument_id="0",
            timeframe=tf, timestamp=base_dt + timedelta(minutes=i),
            open=close, high=close, low=close, close=close,
            volume=1000.0, is_closed=True,
        )
        calc.update(state, candle)
    return round(state.current_ema_fast or 0, 4), round(state.current_ema_slow or 0, 4)


async def fetch_native_closes(
    client: AngelOneClient, stock: dict, timeframe: str
) -> tuple[list[float], int]:
    """
    Fetch native-TF candles using market-hour-aware lookback.
    Returns (close_prices, bar_count).
    Uses ONLY the requested timeframe — no cross-TF mixing.
    """
    inst = InstrumentDefinition(
        provider="angelone",
        exchange=stock["exchange"],
        symbol=stock["symbol"],
        instrument_id=stock["token"],
        name=stock["symbol"],
        asset_class="equity",
        instrument_type="EQUITY",
        is_active=True,
    )
    lookback = warmup_lookback_days(timeframe, WARMUP_BARS)
    now      = datetime.now(tz=IST)
    start    = now - timedelta(days=lookback)

    candles = await client.get_historical_candles(
        instrument=inst, timeframe=timeframe, start=start, end=now,
    )
    candles.sort(key=lambda c: c.timestamp)   # oldest → newest
    closes = [c.close for c in candles]
    return closes, len(closes)


async def main():
    api_key     = os.environ.get("ANGEL_API_KEY", "")
    client_code = os.environ.get("ANGEL_CLIENT_CODE", "")
    password    = os.environ.get("ANGEL_PASSWORD", "")
    totp_secret = os.environ.get("ANGEL_TOTP_SECRET", "")

    if not api_key:
        print("❌  ANGEL_API_KEY not found in .env")
        return

    auth   = AngelOneAuthManager(api_key=api_key, client_code=client_code,
                                  password=password, totp_secret=totp_secret)
    client = AngelOneClient(auth_manager=auth)

    print("\n🔐  Logging in to Angel One SmartAPI...")
    await auth.get_valid_jwt()
    print("✅  Login successful.\n")

    # ══════════════════════════════════════════════════════════════════════════
    # PART 1 — 15m verification vs TradingView reference
    # ══════════════════════════════════════════════════════════════════════════
    TF = "15m"
    lookback = warmup_lookback_days(TF, WARMUP_BARS)
    print("=" * 76)
    print(f"  PART 1 — EMA Precision Check on {TF}  (lookback: {lookback} calendar days)")
    print(f"  TradingView reference values provided by user")
    print("=" * 76)

    part1_results = []
    for stock in STOCKS:
        sym = stock["symbol"]
        print(f"\n📊  {sym} [{TF}]")
        try:
            closes, bar_count = await fetch_native_closes(client, stock, TF)

            if bar_count < 200:
                print(f"   ⚠  Only {bar_count} bars available — EMA-200 may not be fully converged")

            # System EMA
            s100, s200 = system_ema(closes, TF)
            # Pandas reference
            p100 = pandas_ema(closes, 100)
            p200 = pandas_ema(closes, 200)

            sys_ok   = abs(s100 - p100) < TOLERANCE and abs(s200 - p200) < TOLERANCE
            tv_ref   = TV_REFERENCE.get(sym)
            tv_ok100 = tv_ok200 = None
            if tv_ref:
                tv_ok100 = abs(s100 - tv_ref["ema100"]) < TV_TOLERANCE
                tv_ok200 = abs(s200 - tv_ref["ema200"]) < TV_TOLERANCE

            part1_results.append({
                "symbol": sym, "bars": bar_count,
                "s100": s100, "s200": s200,
                "p100": p100, "p200": p200,
                "sys_ok": sys_ok,
                "tv_ref": tv_ref,
                "tv_ok100": tv_ok100, "tv_ok200": tv_ok200,
            })

            sm = "✅" if sys_ok else "❌"
            print(f"   Bars fetched : {bar_count}  (lookback {lookback}d)")
            print(f"   EMA-100 → System: {s100:>10.4f}  |  pandas ref: {p100:>10.4f}  {sm}")
            print(f"   EMA-200 → System: {s200:>10.4f}  |  pandas ref: {p200:>10.4f}  {sm}")
            if tv_ref:
                t1 = "✅" if tv_ok100 else "⚠"
                t2 = "✅" if tv_ok200 else "⚠"
                print(f"   EMA-100 vs TradingView: {s100:>10.4f}  vs  {tv_ref['ema100']:>10.2f}  "
                      f"(Δ {abs(s100-tv_ref['ema100']):.2f})  {t1}")
                print(f"   EMA-200 vs TradingView: {s200:>10.4f}  vs  {tv_ref['ema200']:>10.2f}  "
                      f"(Δ {abs(s200-tv_ref['ema200']):.2f})  {t2}")

        except Exception as e:
            print(f"   ❌  Error: {e}")
            part1_results.append({"symbol": sym, "error": str(e)})

    # ── Part 1 Summary ─────────────────────────────────────────────────────────
    print("\n" + "─" * 76)
    print(f"  {'Symbol':<12} {'Bars':>5}  {'EMA-100':>10}  {'EMA-200':>10}  "
          f"{'vs pandas':>10}  {'vs TV-100':>9}  {'vs TV-200':>9}")
    print("  " + "─" * 72)
    for r in part1_results:
        if "error" in r:
            print(f"  {r['symbol']:<12}  ERROR: {r['error']}")
            continue
        sm = "✅" if r["sys_ok"] else "❌"
        t1 = ("✅" if r["tv_ok100"] else "⚠ ") if r["tv_ok100"] is not None else "N/A"
        t2 = ("✅" if r["tv_ok200"] else "⚠ ") if r["tv_ok200"] is not None else "N/A"
        tv = r["tv_ref"]
        d1 = f"{abs(r['s100']-tv['ema100']):>+.2f}" if tv else " N/A"
        d2 = f"{abs(r['s200']-tv['ema200']):>+.2f}" if tv else " N/A"
        print(f"  {r['symbol']:<12} {r['bars']:>5}  {r['s100']:>10.2f}  {r['s200']:>10.2f}  "
              f"{sm:>10}  {d1} {t1}  {d2} {t2}")

    # ══════════════════════════════════════════════════════════════════════════
    # PART 2 — Multi-timeframe proof: 15m vs 30m vs 1h (EMA values MUST differ)
    # ══════════════════════════════════════════════════════════════════════════
    print("\n\n" + "=" * 76)
    print("  PART 2 — Timeframe Sensitivity Proof")
    print("  EMA values MUST differ across timeframes (using native-TF candles only)")
    print("=" * 76)

    TF_LIST = ["15m", "30m", "1h"]
    # Test on first 3 stocks only for brevity
    for stock in STOCKS[:3]:
        sym = stock["symbol"]
        print(f"\n  📈  {sym}")
        print(f"  {'TF':<6}  {'Bars':>5}  {'EMA-100':>10}  {'EMA-200':>10}  {'vs pandas':>10}")
        print("  " + "─" * 48)
        prev_e100, prev_e200 = None, None
        all_different = True
        for tf in TF_LIST:
            try:
                closes, bar_count = await fetch_native_closes(client, stock, tf)
                s100, s200 = system_ema(closes, tf)
                p100 = pandas_ema(closes, 100)
                p200 = pandas_ema(closes, 200)
                sm = "✅" if (abs(s100 - p100) < TOLERANCE and abs(s200 - p200) < TOLERANCE) else "❌"
                note = ""
                if prev_e100 is not None:
                    if abs(s100 - prev_e100) < 0.01 and abs(s200 - prev_e200) < 0.01:
                        note = "  ⚠ SAME as previous TF!"
                        all_different = False
                print(f"  {tf:<6}  {bar_count:>5}  {s100:>10.2f}  {s200:>10.2f}  {sm}{note}")
                prev_e100, prev_e200 = s100, s200
            except Exception as e:
                print(f"  {tf:<6}  ERROR: {e}")

        verdict = "🟢 EMA values differ correctly across timeframes" if all_different else \
                  "🔴 EMA values identical across timeframes — data issue!"
        print(f"  {verdict}")

    # ══════════════════════════════════════════════════════════════════════════
    # PART 3 — Warm-up adequacy check
    # ══════════════════════════════════════════════════════════════════════════
    print("\n\n" + "=" * 76)
    print("  PART 3 — Warm-up Lookback Table (calendar days per TF for 260 bars)")
    print("=" * 76)
    print(f"  {'Timeframe':<10}  {'Lookback (days)':>16}  {'Expected bars':>14}  {'Adequate?':>10}")
    print("  " + "─" * 56)
    for tf in ["15m", "30m", "1h"]:
        days = warmup_lookback_days(tf, WARMUP_BARS)
        tf_m = int(tf[:-1]) * (60 if tf.endswith("h") else 1)
        exp  = int(days * 5 / 7 * MARKET_MINS_PER_DAY / tf_m)
        ok   = "🟢 YES" if exp >= 200 else "🔴 NO"
        print(f"  {tf:<10}  {days:>16}  {exp:>14}  {ok:>10}")

    print("\n  EMA-200 requires ≥ 200 native-TF bars for mathematical convergence.")
    print("  All lookbacks above provide well above that threshold.")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
