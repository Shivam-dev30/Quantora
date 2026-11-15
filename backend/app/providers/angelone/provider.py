"""Angel One SmartAPI Provider implementing the MarketDataProvider interface."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.core.logging import get_logger
from backend.app.models.candle import MarketCandle
from backend.app.models.instrument import InstrumentDefinition
from backend.app.providers.base import MarketDataProvider
from backend.app.providers.angelone.auth import AngelOneAuthManager
from backend.app.providers.angelone.client import AngelOneClient
from backend.app.providers.angelone.instruments import AngelOneInstrumentService
from backend.app.providers.angelone.websocket import AngelOneWebSocket

logger = get_logger("angelone_provider")


class AngelOneProvider(MarketDataProvider):
    """Complete Angel One SmartAPI integration for Indian Equity, F&O, and Commodities."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_code: Optional[str] = None,
        password: Optional[str] = None,
        totp_secret: Optional[str] = None,
    ) -> None:
        super().__init__(name="angelone")
        self.auth = AngelOneAuthManager(
            api_key=api_key,
            client_code=client_code,
            password=password,
            totp_secret=totp_secret,
        )
        self.instrument_service = AngelOneInstrumentService()
        self.client = AngelOneClient(self.auth)
        self.ws = AngelOneWebSocket(self.auth, self._on_raw_candle)
        self._instruments: List[InstrumentDefinition] = []

    async def _on_raw_candle(self, candle: MarketCandle) -> None:
        if self._candle_callback:
            await self._candle_callback(candle)

    async def initialize(self) -> None:
        """Authenticate session and download instrument master."""
        logger.info("Initializing Angel One SmartAPI provider...")
        try:
            await self.auth.login()
        except Exception as e:
            logger.warning(f"Angel One login exception: {e}. Provider will operate with seed data.")

        self._instruments = await self.instrument_service.fetch_instruments()
        await self.ws.start()
        self._is_connected = True
        logger.info(f"Angel One provider initialized with {len(self._instruments)} instruments.")

    async def get_instruments(self) -> List[InstrumentDefinition]:
        if not self._instruments:
            self._instruments = await self.instrument_service.fetch_instruments()
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
        self.ws.update_subscriptions(instruments, timeframes)
        logger.info(
            f"Angel One subscribed to {len(instruments)} instruments across timeframes: {timeframes}"
        )

    async def unsubscribe(self, instruments: List[InstrumentDefinition]) -> None:
        # Filter out from WS subscription set
        remove_ids = {i.instrument_id for i in instruments}
        current = [
            i for i in self.ws._subscribed_instruments.values()
            if i.instrument_id not in remove_ids
        ]
        self.ws.update_subscriptions(current, self.ws._subscribed_timeframes)

    async def reconnect(self) -> None:
        logger.info("Reconnecting Angel One provider...")
        await self.ws.stop()
        await self.auth.login()
        await self.ws.start()

    async def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "configured": self.auth.is_configured,
            "connected": self._is_connected,
            "instruments_count": len(self._instruments),
            "jwt_valid": bool(self.auth.jwt_token),
            "ws_active": self.ws._running,
        }

    async def close(self) -> None:
        logger.info("Closing Angel One provider resources...")
        await self.ws.stop()
        self._is_connected = False
