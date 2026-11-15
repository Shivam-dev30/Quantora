"""Abstract Base Provider for external market data sources."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional
from backend.app.models.candle import MarketCandle
from backend.app.models.instrument import InstrumentDefinition

CandleCallback = Callable[[MarketCandle], Coroutine[Any, Any, None]]


class MarketDataProvider(ABC):
    """Abstract interface that all broker/exchange data providers must implement."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._candle_callback: Optional[CandleCallback] = None
        self._is_connected: bool = False

    def set_candle_callback(self, callback: CandleCallback) -> None:
        """Register the callback triggered when a new candle is received/closed."""
        self._candle_callback = callback

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @abstractmethod
    async def initialize(self) -> None:
        """Authenticate and prepare the provider connection."""
        pass

    @abstractmethod
    async def get_instruments(self) -> List[InstrumentDefinition]:
        """Fetch and normalize all available instruments from the broker/exchange."""
        pass

    @abstractmethod
    async def get_historical_candles(
        self,
        instrument: InstrumentDefinition,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[MarketCandle]:
        """Fetch historical closed OHLCV candles for indicator warm-up and gap-filling."""
        pass

    @abstractmethod
    async def subscribe(
        self,
        instruments: List[InstrumentDefinition],
        timeframes: List[str],
    ) -> None:
        """Subscribe to real-time market data feed for specified instruments."""
        pass

    @abstractmethod
    async def unsubscribe(
        self,
        instruments: List[InstrumentDefinition],
    ) -> None:
        """Unsubscribe from real-time market data feed."""
        pass

    @abstractmethod
    async def reconnect(self) -> None:
        """Perform reconnection and resubscription after connection drop."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider connectivity, session status, and latencies."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Gracefully terminate WebSockets, HTTP sessions, and cleanup resources."""
        pass
