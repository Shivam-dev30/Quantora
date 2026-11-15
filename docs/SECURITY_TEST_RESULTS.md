# Quantora Security Test Results

## 1. Automated Test Execution Summary
- **Execution Date**: November 2026
- **Test Framework**: `pytest 8.4.2` with `pytest-asyncio 1.4.0`
- **Environment**: Python 3.12.10 (Win32) with isolated temporary SQLite database
- **Command Executed**: `python -m pytest backend/tests -v`
- **Total Tests Collected**: 31
- **Passed**: 31 (100%)
- **Failed**: 0
- **Duration**: 3.20 seconds

---

## 2. Test Breakdown by Category

### A. Trading Strategy & Calculations (Non-Negotiable Baseline)
- `test_ema_alpha_multipliers`: **PASSED** (Validated exact EMA 100/200 smoothing factors: 2/101 and 2/201).
- `test_incremental_ema_matches_pandas`: **PASSED** (Incremental O(1) EMA matches pandas reference).
- `test_ema_state_readiness_barrier`: **PASSED** (Barrier prevents signal emission before warmup).
- `test_bullish_crossover`: **PASSED** (EMA 100 crosses strictly above EMA 200).
- `test_bearish_crossover`: **PASSED** (EMA 100 crosses strictly below EMA 200).
- `test_crossover_from_exact_equality`: **PASSED** (Boundary crossover detection verified).
- `test_no_crossover_when_staying_above`: **PASSED** (No false crossovers emitted when staying above).
- `test_no_crossover_when_staying_below`: **PASSED** (No false crossovers emitted when staying below).
- `test_no_crossover_on_identical_flatline`: **PASSED** (Flatline condition emits no signals).

### B. Golden Dataset Verification (Multi-Asset)
- `test_golden_dataset_crossover[angelone-equity-NSE-RELIANCE]`: **PASSED**
- `test_golden_dataset_crossover[angelone-equity_futures-NFO-NIFTY26OCTFUT]`: **PASSED**
- `test_golden_dataset_crossover[angelone-commodity-MCX-CRUDEOIL19OCTFUT]`: **PASSED**
- `test_golden_dataset_crossover[delta-crypto-DELTA-BTCUSD]`: **PASSED**

### C. Signal Deduplication & Closed-Candle Tracking
- `test_deterministic_signal_id`: **PASSED** (Deterministic SHA-256 signal ID generation).
- `test_deduplicator_prevents_duplicate_signals`: **PASSED** (In-memory + SQLite deduplication).
- `test_different_timeframes_produce_distinct_signals`: **PASSED** (Timeframe isolation verified).
- `test_intrabar_ticks_do_not_emit_closed_candles`: **PASSED** (Only closed candles trigger EMA updates).
- `test_duplicate_closed_candle_ignored`: **PASSED** (Duplicate candle barrier verified).

### D. Instrument Classification & Universe Filtering
- `test_angel_one_scrip_classification`: **PASSED** (Scrip master classification verified).
- `test_instrument_manager_universe_filtering`: **PASSED** (Configured universe filtering verified).
- `test_alert_endpoints_lifecycle`: **PASSED** (Alert configuration and atomic YAML persistence).

### E. Notification Isolation
- `test_notification_failure_isolation`: **PASSED** (Telegram/Email/WhatsApp failure isolation).

### F. Application Security & Authentication
- `test_password_hashing`: **PASSED** (Argon2id hashing & verification).
- `test_jwt_token_generation_and_verification`: **PASSED** (JWT payload and expiration).
- `test_invalid_jwt_token`: **PASSED** (Tampered tokens rejected safely).
- `test_rate_limiter`: **PASSED** (Sliding-window rate limiter prevents abuse).
- `test_auth_endpoints_lifecycle`: **PASSED** (Registration, login, me endpoint, and token validation).

### G. Cryptographic Security & Audit Trails
- `test_aes_gcm_key_derivation`: **PASSED** (PBKDF2 32-byte key derivation verified).
- `test_encrypt_and_decrypt_roundtrip`: **PASSED** (AES-256-GCM authenticated encryption roundtrip).
- `test_decrypt_tampered_or_invalid_ciphertext`: **PASSED** (Tamper detection without uncaught crashes).
- `test_audit_log_persistence`: **PASSED** (Security audit events persisted to `SystemEventModel`).

---

## 3. Frontend & Dependency Security Verification
- `npm audit --prefix frontend`: **0 vulnerabilities**
- `tsc -b && vite build --prefix frontend`: **Clean build, 0 TypeScript errors**
