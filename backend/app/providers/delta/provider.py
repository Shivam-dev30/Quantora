"""Delta Exchange Provider implementing MarketDataProvider interface."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.core.logging import get_logger
from backend.app.models.candle import MarketCandle
from backend.app.models.instrument import InstrumentDefinition
from backend.app.providers.base import MarketDataProvider
from backend.app.providers.delta.client import DeltaClient
from backend.app.providers.delta.websocket import DeltaWebSocket

logger = get_logger("delta_provider")


class DeltaExchangeProvider(MarketDataProvider):
    """Cryptocurrency market data provider via official Delta Exchange REST & WebSocket APIs."""

    def __init__(
        self,
        rest_url: str = "https://api.india.delta.exchange",
        ws_url: str = "wss://socket.india.delta.exchange",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ) -> None:
        super().__init__(name="delta")
        self.client = DeltaClient(
            base_url=rest_url,
            api_key=api_key,
            api_secret=api_secret,
        )
        self.ws = DeltaWebSocket(
            ws_url=ws_url,
            on_candle_received=self._on_raw_candle,
        )
        self._instruments: List[InstrumentDefinition] = []

    async def _on_raw_candle(self, candle: MarketCandle) -> None:
        if self._candle_callback:
            await self._candle_callback(candle)

    async def initialize(self) -> None:
        logger.info("Initializing Delta Exchange provider...")
        self._instruments = await self.client.get_products()
        await self.ws.start()
        self._is_connected = True
        logger.info(f"Delta Exchange provider ready with {len(self._instruments)} crypto products.")

    async def get_instruments(self) -> List[InstrumentDefinition]:
        if not self._instruments:
            self._instruments = await self.client.get_products()
        return self._instruments

    async def get_historical_candles(
        self,
        instrument: InstrumentDefinition,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[MarketCandle]:
        return await self.client.get_historical_candles(instrument, timeframe, start, end)

    async def subscribe(
        self,
        instruments: List[InstrumentDefinition],
        timeframes: List[str],
    ) -> None:
        await self.ws.update_subscriptions(instruments, timeframes)
        logger.info(
            f"Delta Exchange subscribed to {len(instruments)} crypto assets on timeframes {timeframes}"
        )

    async def unsubscribe(self, instruments: List[InstrumentDefinition]) -> None:
        rem_syms = {i.symbol for i in instruments}
        current = [
            i for i in self.ws._subscribed_instruments.values()
            if i.symbol not in rem_syms
        ]
        await self.ws.update_subscriptions(current, self.ws._subscribed_timeframes)

    async def reconnect(self) -> None:
        logger.info("Reconnecting Delta Exchange provider...")
        await self.ws.stop()
        await self.ws.start()

    async def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "connected": self._is_connected,
            "products_count": len(self._instruments),
            "ws_active": self.ws._running,
        }

    async def close(self) -> None:
        logger.info("Closing Delta Exchange provider...")
        await self.ws.stop()
        self._is_connected = False
