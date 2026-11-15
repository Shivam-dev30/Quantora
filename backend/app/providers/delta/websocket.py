"""Delta Exchange WebSocket Client for real-time cryptocurrency candle feeds."""

import asyncio
import json
from datetime import datetime, timedelta
import math
from typing import Any, Callable, Coroutine, Dict, List, Optional
import websockets
from backend.app.core.logging import get_logger
from backend.app.models.candle import MarketCandle
from backend.app.models.instrument import InstrumentDefinition

logger = get_logger("delta_ws")

DELTA_WS_URL = "wss://socket.india.delta.exchange"


class DeltaWebSocket:
    """Manages real-time streaming WebSocket connection to Delta Exchange."""

    def __init__(
        self,
        ws_url: str = DELTA_WS_URL,
        on_candle_received: Optional[Callable[[MarketCandle], Coroutine[Any, Any, None]]] = None,
    ) -> None:
        self.ws_url = ws_url
        self.on_candle = on_candle_received
        self._ws: Optional[Any] = None
        self._running: bool = False
        self._subscribed_instruments: Dict[str, InstrumentDefinition] = {}
        self._subscribed_timeframes: List[str] = ["15m"]
        self._worker_task: Optional[asyncio.Task] = None
        self._simulation_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._running = True
        self._worker_task = asyncio.create_task(self._connection_loop())

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        if self._simulation_task:
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass
            self._simulation_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Delta WebSocket client stopped.")

    async def update_subscriptions(
        self, instruments: List[InstrumentDefinition], timeframes: List[str]
    ) -> None:
        for inst in instruments:
            self._subscribed_instruments[inst.symbol] = inst
        self._subscribed_timeframes = timeframes
        if self._ws and self._running:
            try:
                await self._send_subscriptions()
            except Exception as e:
                logger.warning(f"Error sending updated Delta subscriptions: {e}")

    async def _connection_loop(self) -> None:
        backoff = 2.0
        ws_endpoints = [
            self.ws_url,
            "wss://socket.india.delta.exchange",
            "wss://socket.delta.exchange",
        ]
        endpoint_idx = 0

        while self._running:
            target_url = ws_endpoints[endpoint_idx % len(ws_endpoints)]
            try:
                logger.info(f"Connecting to Delta Exchange WebSocket at {target_url}...")
                async with websockets.connect(
                    target_url,
                    ping_interval=30,
                    ping_timeout=10,
                    open_timeout=10,
                ) as ws:
                    self._ws = ws
                    backoff = 2.0
                    logger.info(f"Connected to Delta Exchange WebSocket ({target_url}).")

                    await self._send_subscriptions()
                    ping_task = asyncio.create_task(self._ping_loop(ws))

                    try:
                        while self._running:
                            message = await ws.recv()
                            await self._handle_message(message)
                    finally:
                        ping_task.cancel()

            except (websockets.ConnectionClosed, asyncio.TimeoutError) as e:
                logger.warning(f"Delta WebSocket connection closed: {e}. Reconnecting in {backoff}s...")
                endpoint_idx += 1
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
            except Exception as e:
                logger.warning(f"Delta WebSocket error: {e}. Retrying...")
                endpoint_idx += 1
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def _ping_loop(self, ws: Any) -> None:
        """Periodic ping required by Delta WebSocket protocol."""
        while self._running:
            try:
                await asyncio.sleep(25)
                await ws.send(json.dumps({"type": "ping"}))
            except Exception:
                break

    async def _send_subscriptions(self) -> None:
        if not self._ws or not self._subscribed_instruments:
            return

        symbols = list(self._subscribed_instruments.keys())
        if not symbols:
            return

        channels = []
        for tf in self._subscribed_timeframes:
            channel_name = f"candlestick_{tf}"
            channels.append({"name": channel_name, "symbols": symbols})

        payload = {
            "type": "subscribe",
            "payload": {
                "channels": channels,
            },
        }

        await self._ws.send(json.dumps(payload))
        logger.info(f"Subscribed to Delta channels: {len(symbols)} symbols on {self._subscribed_timeframes}")

    async def _handle_message(self, message: Any) -> None:
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type.startswith("candlestick_"):
                tf = msg_type.replace("candlestick_", "")
                symbol = data.get("symbol")
                candle_data = data.get("candle") or data.get("data") or data

                if candle_data and self.on_candle:
                    if isinstance(candle_data, dict):
                        start_time = candle_data.get("candle_start_time") or candle_data.get("timestamp") or candle_data.get("time")
                        if start_time:
                            raw_val = float(start_time)
                            if raw_val > 1e14:  # microseconds
                                ts_sec = raw_val / 1_000_000.0
                            elif raw_val > 1e11:  # milliseconds
                                ts_sec = raw_val / 1_000.0
                            else:
                                ts_sec = raw_val
                            ts = datetime.utcfromtimestamp(ts_sec)
                        else:
                            ts = datetime.utcnow()

                        c_open = float(candle_data.get("open", 0.0) or 0.0)
                        c_high = float(candle_data.get("high", 0.0) or 0.0)
                        c_low = float(candle_data.get("low", 0.0) or 0.0)
                        c_close = float(candle_data.get("close", 0.0) or 0.0)
                        c_vol = float(candle_data.get("volume", 0.0) or 0.0)
                    elif isinstance(candle_data, list) and len(candle_data) >= 5:
                        raw_ts = float(candle_data[0])
                        ts_sec = raw_ts / 1_000_000.0 if raw_ts > 1e14 else (raw_ts / 1_000.0 if raw_ts > 1e11 else raw_ts)
                        ts = datetime.utcfromtimestamp(ts_sec)
                        c_open = float(candle_data[1])
                        c_high = float(candle_data[2])
                        c_low = float(candle_data[3])
                        c_close = float(candle_data[4])
                        c_vol = float(candle_data[5]) if len(candle_data) > 5 else 0.0
                    else:
                        return

                    if c_close <= 0.0 or not symbol:
                        return

                    inst = self._subscribed_instruments.get(symbol)
                    inst_id = inst.instrument_id if inst else symbol

                    candle = MarketCandle(
                        provider="delta",
                        asset_class="crypto",
                        exchange="DELTA",
                        symbol=symbol,
                        instrument_id=inst_id,
                        timeframe=tf,
                        timestamp=ts,
                        open=c_open,
                        high=c_high,
                        low=c_low,
                        close=c_close,
                        volume=c_vol,
                        is_closed=False,
                    )
                    await self.on_candle(candle)

        except Exception as e:
            logger.debug(f"Error handling Delta WS message: {e}")

    async def _simulation_loop(self) -> None:
        """Simulate real-time cryptocurrency ticks for offline/test environments."""
        step = 0
        while self._running:
            await asyncio.sleep(5.0)
            step += 1
            now_utc = datetime.utcnow()

            for symbol, inst in list(self._subscribed_instruments.items()):
                for tf in self._subscribed_timeframes:
                    base_price = 67200.0 if "BTC" in symbol else 3500.0
                    change = math.sin(step * 0.4) * (base_price * 0.001)
                    c_price = round(base_price + change, 2)

                    candle = MarketCandle(
                        provider="delta",
                        asset_class="crypto",
                        exchange="DELTA",
                        symbol=symbol,
                        instrument_id=inst.instrument_id,
                        timeframe=tf,
                        timestamp=now_utc,
                        open=c_price - 5.0,
                        high=c_price + 10.0,
                        low=c_price - 10.0,
                        close=c_price,
                        volume=12.5,
                        is_closed=False,
                    )
                    if self.on_candle:
                        await self.on_candle(candle)
