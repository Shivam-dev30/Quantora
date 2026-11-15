"""Angel One SmartAPI WebSocket Client (SmartStream)."""

import asyncio
import json
import struct
from datetime import datetime, timedelta
import math
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
import websockets
from backend.app.core.exceptions import WebSocketConnectionError
from backend.app.core.logging import get_logger
from backend.app.models.candle import MarketCandle
from backend.app.models.instrument import InstrumentDefinition
from backend.app.providers.angelone.auth import AngelOneAuthManager

logger = get_logger("angelone_ws")

SMART_STREAM_WS_URL = "wss://smartapisocket.angelone.in/smart-stream"

EXCHANGE_TYPE_MAP = {
    "NSE": 1,
    "NFO": 2,
    "BSE": 3,
    "BFO": 4,
    "MCX": 5,
    "NCX": 7,
    "CDE": 13,
}


class AngelOneWebSocket:
    """Manages real-time streaming WebSocket connection to Angel One SmartStream."""

    def __init__(
        self,
        auth_manager: AngelOneAuthManager,
        on_candle_received: Callable[[MarketCandle], Coroutine[Any, Any, None]],
    ) -> None:
        self.auth = auth_manager
        self.on_candle = on_candle_received
        self._ws: Optional[Any] = None
        self._running: bool = False
        self._subscribed_instruments: Dict[str, InstrumentDefinition] = {}
        self._subscribed_timeframes: List[str] = ["15m"]
        self._worker_task: Optional[asyncio.Task] = None
        self._simulation_task: Optional[asyncio.Task] = None
        self._last_heartbeat: Optional[datetime] = None

    async def start(self) -> None:
        """Start the streaming connection or simulation loop."""
        self._running = True
        if self.auth.is_configured:
            self._worker_task = asyncio.create_task(self._connection_loop())
        else:
            logger.info("Angel One unconfigured: Starting real-time simulation stream.")
            self._simulation_task = asyncio.create_task(self._simulation_loop())

    async def stop(self) -> None:
        """Gracefully disconnect WebSocket and terminate tasks."""
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
        logger.info("Angel One WebSocket client stopped.")

    def update_subscriptions(
        self, instruments: List[InstrumentDefinition], timeframes: List[str]
    ) -> None:
        """Update subscribed instruments and timeframes."""
        for inst in instruments:
            self._subscribed_instruments[inst.instrument_id] = inst
        self._subscribed_timeframes = timeframes

    async def _connection_loop(self) -> None:
        """Persistent loop maintaining WebSocket connection with backoff."""
        backoff = 2.0
        while self._running:
            try:
                jwt = await self.auth.get_valid_jwt()
                headers = {
                    "Authorization": f"Bearer {jwt}",
                    "x-api-key": self.auth.api_key or "",
                    "x-client-code": self.auth.client_code or "",
                    "x-feed-token": self.auth.feed_token or "",
                }

                logger.info("Connecting to Angel One SmartStream WebSocket...")
                # websockets v14+ uses additional_headers, older versions used extra_headers
                ws_kwargs = {"ping_interval": 30, "ping_timeout": 10}
                try:
                    import inspect
                    sig = inspect.signature(websockets.connect)
                    if "additional_headers" in sig.parameters:
                        ws_kwargs["additional_headers"] = headers
                    else:
                        ws_kwargs["extra_headers"] = headers
                except Exception:
                    ws_kwargs["additional_headers"] = headers

                async with websockets.connect(
                    SMART_STREAM_WS_URL,
                    **ws_kwargs,
                ) as ws:
                    self._ws = ws
                    backoff = 2.0
                    logger.info("Connected to Angel One SmartStream WebSocket.")

                    await self._send_subscriptions()

                    while self._running:
                        message = await ws.recv()
                        self._last_heartbeat = datetime.utcnow()
                        await self._handle_message(message)

            except (websockets.ConnectionClosed, asyncio.TimeoutError) as e:
                logger.warning(f"Angel One WebSocket dropped: {e}. Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
            except Exception as e:
                logger.exception(f"Unexpected error in Angel One WS loop: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def _send_subscriptions(self) -> None:
        """Send SmartStream subscription payload for active instruments."""
        if not self._ws or not self._subscribed_instruments:
            return

        # Group tokens by exchange
        grouped: Dict[int, List[str]] = {}
        for inst in self._subscribed_instruments.values():
            exch_code = EXCHANGE_TYPE_MAP.get(inst.exchange.upper(), 1)
            grouped.setdefault(exch_code, []).append(inst.instrument_id)

        token_list = [
            {"exchangeType": exch, "tokens": tokens} for exch, tokens in grouped.items()
        ]

        payload = {
            "correlationID": f"sub_{int(datetime.utcnow().timestamp())}",
            "action": 1,  # 1 for subscribe
            "params": {
                "mode": 2,  # Mode 2 = Quote
                "tokenList": token_list,
            },
        }

        await self._ws.send(json.dumps(payload))
        logger.info(f"Subscribed to {len(self._subscribed_instruments)} Angel One instruments.")

    async def _handle_message(self, message: Any) -> None:
        """Parse binary SmartStream packet or JSON ping/response."""
        if isinstance(message, str):
            try:
                data = json.loads(message)
                # Check for heartbeat or acknowledgment
                return
            except json.JSONDecodeError:
                return

        if isinstance(message, bytes) and len(message) >= 43:
            # SmartStream binary packet parsing:
            # Byte 0: Subscription mode
            # Byte 1: Exchange Type
            # Bytes 2-26: Token (25 bytes null-padded string)
            # Bytes 27-34: Sequence number (int64)
            # Bytes 35-42: Exchange timestamp (int64)
            # Bytes 43-50: LTP in paise (int64)
            try:
                token_bytes = message[2:27]
                token = token_bytes.decode("ascii").strip("\x00").strip()
                ltp_paise = struct.unpack("<q", message[43:51])[0] if len(message) >= 51 else 0
                ltp = ltp_paise / 100.0

                inst = self._subscribed_instruments.get(token)
                if inst and ltp > 0:
                    # Dispatch price update to candle normalizer / closed-candle tracker
                    now_utc = datetime.utcnow()
                    for tf in self._subscribed_timeframes:
                        candle = MarketCandle(
                            provider="angelone",
                            asset_class=inst.asset_class,
                            exchange=inst.exchange,
                            symbol=inst.symbol,
                            instrument_id=inst.instrument_id,
                            timeframe=tf,
                            timestamp=now_utc,
                            open=ltp,
                            high=ltp,
                            low=ltp,
                            close=ltp,
                            volume=1.0,
                            is_closed=False,
                        )
                        await self.on_candle(candle)
            except Exception as e:
                logger.debug(f"Error parsing SmartStream binary packet: {e}")

    async def _simulation_loop(self) -> None:
        """Simulate real-time candle close ticks for configured instruments when offline."""
        logger.info("Angel One simulation loop active.")
        step = 0
        while self._running:
            await asyncio.sleep(5.0)  # Emit periodic tick
            step += 1
            now_utc = datetime.utcnow()

            for inst in list(self._subscribed_instruments.values()):
                for tf in self._subscribed_timeframes:
                    base_price = 1540.0
                    if "NIFTY" in inst.symbol:
                        base_price = 25100.0
                    elif "CRUDEOIL" in inst.symbol:
                        base_price = 6250.0

                    # Generate realistic simulated candle
                    fluctuation = math.sin(step * 0.5) * 10.0
                    c_price = round(base_price + fluctuation, 2)

                    candle = MarketCandle(
                        provider="angelone",
                        asset_class=inst.asset_class,
                        exchange=inst.exchange,
                        symbol=inst.symbol,
                        instrument_id=inst.instrument_id,
                        timeframe=tf,
                        timestamp=now_utc,
                        open=c_price - 1.0,
                        high=c_price + 2.0,
                        low=c_price - 2.0,
                        close=c_price,
                        volume=500.0,
                        is_closed=False,
                    )
                    await self.on_candle(candle)
