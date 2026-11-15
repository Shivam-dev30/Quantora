# Angel One SmartAPI Integration Guide

## 1. Overview
The platform integrates directly with the official Angel One SmartAPI for Indian market data covering:
- **NSE Cash Equity** (e.g. RELIANCE, TCS, INFY)
- **NFO Equity Derivatives** (Futures: NIFTY, BANKNIFTY; Options: CE/PE)
- **MCX Commodities** (CRUDEOIL, NATURALGAS, GOLD, SILVER)

---

## 2. Authentication & Session Flow
Angel One uses a two-step TOTP login to issue session JWTs:
- **Endpoint**: `POST https://apiconnect.angelbroking.com/rest/secure/angelbroking/user/v1/loginByPassword`
- **Headers**:
  ```http
  Content-Type: application/json
  Accept: application/json
  X-UserType: USER
  X-SourceID: WEB
  X-ClientLocalIP: 127.0.0.1
  X-ClientPublicIP: 106.193.147.98
  X-MACAddress: fe80::216e:6507:4b90:3719
  X-PrivateKey: <YOUR_API_KEY>
  ```
- **Payload**:
  ```json
  {
    "clientcode": "<CLIENT_ID>",
    "password": "<PASSWORD>",
    "totp": "<6_DIGIT_TOTP>"
  }
  ```
- **TOTP Generation**: Generated automatically in real-time using `pyotp.TOTP(totp_secret).now()`.
- **Token Management**: The issued `jwtToken` is refreshed every 6 hours via `POST /rest/secure/angelbroking/jwt/v1/generateTokens`.

---

## 3. Dynamic Instrument Master (Scrip Master)
The platform never hardcodes instruments. Instead, it downloads and caches the official Angel One Scrip Master JSON:
- **URL**: `https://margincalculator.angelbroking.com/OpenAPI-File/files/OpenAPIScripMaster.json`
- **Fields parsed**:
  - `token`: Instrument token (e.g. "2885" for RELIANCE)
  - `symbol`: Trading symbol (e.g. "RELIANCE-EQ", "NIFTY29OCT26FUT")
  - `name`: Root underlying name
  - `exch_seg`: "NSE", "NFO", "MCX"
  - `instrumenttype`: "EQUITY", "FUTIDX", "OPTIDX", "FUTCOM"
  - `expiry`: Contract expiry date
  - `strike`: Strike price in decimal rupees
  - `lotsize`: Contract lot size

---

## 4. Historical Candles API
Used during system initialization to warm up the EMA100 and EMA200 indicators (requiring 200+ historical bars):
- **Endpoint**: `POST https://apiconnect.angelbroking.com/rest/secure/angelbroking/historical/v1/getCandleData`
- **Interval Mapping**:
  - `1m` -> `ONE_MINUTE`
  - `5m` -> `FIVE_MINUTE`
  - `15m` -> `FIFTEEN_MINUTE`
  - `1h` -> `ONE_HOUR`
  - `1d` -> `ONE_DAY`
- **Date Format**: `YYYY-MM-DD HH:MM` (in IST).

---

## 5. SmartStream WebSocket
- **URL**: `wss://smartapisocket.angelone.in/smart-stream`
- **Headers**:
  ```http
  Authorization: Bearer <jwtToken>
  x-api-key: <api_key>
  x-client-code: <client_code>
  x-feed-token: <feed_token>
  ```
- **Binary Quote Packet**: LTP and quote values are received in binary Little-Endian format and routed through the `ClosedCandleTracker`.
