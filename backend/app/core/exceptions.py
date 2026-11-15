"""Standard exception classes for the market alert platform."""


class MarketAlertError(Exception):
    """Base exception for all market alert platform errors."""


class ConfigurationError(MarketAlertError):
    """Raised when configuration or environment parameters are invalid."""


class ProviderError(MarketAlertError):
    """Raised when an external market data provider encounters an error."""


class AuthenticationError(ProviderError):
    """Raised when provider authentication or session creation fails."""


class RateLimitExceededError(ProviderError):
    """Raised when provider API rate limits are hit."""

    def __init__(self, message: str, retry_after: float = 5.0):
        super().__init__(message)
        self.retry_after = retry_after


class WebSocketConnectionError(ProviderError):
    """Raised when WebSocket connection fails or drops unexpectedly."""


class HistoricalDataError(ProviderError):
    """Raised when fetching historical candle data fails."""


class InstrumentNotFoundError(MarketAlertError):
    """Raised when a requested symbol cannot be mapped to a valid instrument."""


class IndicatorError(MarketAlertError):
    """Raised when indicator calculation fails."""


class SignalProcessingError(MarketAlertError):
    """Raised when signal detection or deduplication fails."""


class NotificationError(MarketAlertError):
    """Raised when sending an alert through a notification channel fails."""
