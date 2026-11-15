# Multi-Asset Market Alert Platform Architecture

## 1. System Mission & Guardrails

The platform is an **ALERT-ONLY SYSTEM** engineered for high-reliability, zero-duplicate real-time market monitoring across:
1. Indian Equities (NSE)
2. Indian Equity F&O (Futures & Options)
3. Indian Commodities (MCX)
4. Cryptocurrency (Delta Exchange)

### Strict Operational Guardrails
The system explicitly does **NOT**:
- Place or execute trades
- Modify or cancel orders
- Manage broker positions or accounts
- Perform automated trading or strategy execution
- Run backtests or optimize portfolios
- Track portfolio P&L

The system's sole duty is:
```text
MARKET DATA → INDICATOR ENGINE → SIGNAL DETECTION → ALERT ENGINE → NOTIFICATION CHANNELS
```

---

## 2. High-Level Architecture

```text
┌──────────────────────────┐      ┌──────────────────────────┐
│   Angel One SmartAPI     │      │   Delta Exchange API     │
│ (NSE, NFO, MCX Markets)  │      │  (24/7 Cryptocurrency)   │
└────────────┬─────────────┘      └────────────┬─────────────┘
             │                                 │
             ▼                                 ▼
┌────────────────────────────────────────────────────────────┐
│                  Provider Abstraction Layer                │
│    (AngelOneProvider & DeltaExchangeProvider Adapters)     │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│              Closed Candle Tracker (Gatekeeper)            │
│  - Prevents intrabar false signals                         │
│  - Flushes finalized closed candles only                   │
│  - Rejects duplicate/replayed timestamps                   │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                     Indicator Engine                       │
│  - EMA 100 (Fast) & EMA 200 (Slow) incremental calculator │
│  - History warm-up (200+ bar mathematical convergence)     │
│  - Multi-timeframe isolation (5m, 15m, 1h)                 │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                      Signal Engine                         │
│  - CrossoverDetector: Bullish / Bearish / Equality         │
│  - Deterministic Signal ID generator                       │
│  - Deduplicator (Memory cache + SQLite unique index)       │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                   Notification Manager                     │
│  - Concurrent delivery with strict failure isolation       │
│  - Formats: MINIMAL, STANDARD, DETAILED                    │
│  - Channels: Telegram Bot, SMTP Email, Official WhatsApp   │
│  - Real-Time WebSocket broadcast to Web Dashboard          │
└────────────────────────────────────────────────────────────┘
```

---

## 3. Data Integrity & Closed-Candle Logic

### A. Intrabar Rejection
A primary cause of false crossover alerts in financial applications is intrabar volatility (the price moving above an EMA mid-candle, then finishing below it before candle close).
- The `ClosedCandleTracker` intercepts all ticks and quotes.
- Forming candles are updated in memory without generating signals.
- Only when the candle timestamp crosses the interval boundary (e.g. at `10:15:00` for a `15m` bar) is the preceding candle marked as `is_closed = True` and dispatched to the indicators.

### B. Signal Identity & Deduplication
Every signal receives a deterministic SHA/string identity:
```text
{provider}:{exchange}:{instrument_id}:{timeframe}:{candle_timestamp}:{signal_type}:{strategy_version}
```
Example:
```text
angelone:NSE:2885:15m:2026-10-09T10:15:00Z:BULLISH:ema100_200_v1
```
Before any notification is sent, the ID is verified against:
1. Fast in-memory hash set.
2. SQLite `signals` table with a unique indexed constraint.

If an identical signal is re-received (due to WebSocket reconnection, REST gap-filling, or worker restart), it is discarded with zero duplicate alert emissions.

---

## 4. Notification Failure Isolation
If Telegram experiences an API timeout or rate-limit error, the `NotificationManager` catches the exception independently, records the failure in `notification_deliveries`, and proceeds with SMTP Email and WhatsApp delivery without interruption.
