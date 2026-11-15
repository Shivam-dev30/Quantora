"""Abstract Notification Provider base class."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from backend.app.models.alert import AlertNotification


class NotificationProvider(ABC):
    """Abstract interface that all notification channels must implement."""

    def __init__(self, name: str, enabled: bool = True) -> None:
        self.name = name
        self.enabled = enabled

    @abstractmethod
    async def send(self, alert: AlertNotification) -> bool:
        """Send formatted alert notification through this channel."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify provider credentials, connection status, and responsiveness."""
        pass
