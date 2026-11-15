# Delta Exchange API Integration Guide

## 1. Overview
The platform monitors cryptocurrency perpetual futures and spot pairs 24/7/365 via official Delta Exchange endpoints:
- REST API Base: `https://api.delta.exchange`
- WebSocket Base: `wss://socket.delta.exchange`

---

## 2. Dynamic Product Discovery
The cryptocurrency universe is discovered dynamically via REST:
- **Endpoint**: `GET /v2/products`
- **Response**: Array of product objects containing `id`, `symbol` (e.g. `BTCUSD`, `ETHUSD`, `SOLUSD`), `tick_size`, and `contract_type`.
- **Filtering**: Filters operational products according to the `symbols` whitelist defined in `config.yaml`.

---

## 3. Historical Candles API
Used during warm-up to initialize EMA100 and EMA200 indicators:
- **Endpoint**: `GET /v2/history/candles`
- **Parameters**:
  - `resolution`: `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1d`
  - `symbol`: e.g. `BTCUSD`
  - `start`: Unix timestamp (in seconds)
  - `end`: Unix timestamp (in seconds)
- **Response format**:
  ```json
  {
    "success": true,
    "result": [
      {
        "time": 1696809600,
        "open": 67100.5,
        "high": 67250.0,
        "low": 67050.2,
        "close": 67185.4,
        "volume": 125.43
      }
    ]
  }
  ```

---

## 4. Delta WebSocket Streaming
- **URL**: `wss://socket.delta.exchange`
- **Subscription message**:
  ```json
  {
    "type": "subscribe",
    "payload": {
      "channels": [
        {
          "name": "candlestick_15m",
          "symbols": ["BTCUSD", "ETHUSD"]
        }
      ]
    }
  }
  ```
- **Ping/Pong Heartbeat**: Client sends `{"type": "ping"}` every 25 seconds; Delta responds with `{"type": "pong"}`.
- **Reconnection**: Handled automatically with exponential backoff on connection drops.
