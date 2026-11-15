"""Alert notifications and detail mode configurations."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from backend.app.models.signal import SignalEvent


class NotificationDetailMode(str, Enum):
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    DETAILED = "DETAILED"


class AlertNotification(BaseModel):
    """Normalized alert notification ready for multi-channel dispatch."""

    signal: SignalEvent
    detail_mode: NotificationDetailMode = NotificationDetailMode.STANDARD
    display_time: str
    currency_symbol: str = "₹"
    formatted_price: str
    formatted_ema100: str
    formatted_ema200: str
    formatted_prev_ema100: str
    formatted_prev_ema200: str
    market_display_name: str
    current_price: Optional[float] = None
    formatted_current_price: Optional[str] = None
    drift_points: Optional[float] = None
    drift_percent: Optional[float] = None
    elapsed_time_str: Optional[str] = None
