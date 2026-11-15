"""Market hours and trading session verification across multiple asset classes."""

from datetime import datetime, time
from typing import Dict, Optional
import pytz

UTC = pytz.UTC
IST = pytz.timezone("Asia/Kolkata")


class MarketHoursManager:
    """Evaluates trading session hours and converts timestamps between UTC and local timezones."""

    def __init__(self, display_tz: str = "Asia/Kolkata", respect_hours: bool = True) -> None:
        self.display_tz_name = display_tz
        self.display_tz = pytz.timezone(display_tz)
        self.respect_hours = respect_hours

        # Standard Indian Market trading hours in IST (Monday=0 to Friday=4)
        self.sessions: Dict[str, Dict[str, time]] = {
            "NSE": {
                "open": time(9, 15),
                "close": time(15, 30),
            },
            "NFO": {
                "open": time(9, 15),
                "close": time(15, 30),
            },
            "MCX": {
                "open": time(9, 0),
                "close": time(23, 30),
            },
        }

    def is_market_open(self, exchange: str, check_time_utc: Optional[datetime] = None) -> bool:
        """
        Check if an exchange is currently open.
        - Crypto (DELTA): Always True (24/7/365).
        - If respect_hours is False: Always True.
        - Indian markets (NSE, NFO, MCX): Checked against IST session schedule.
        """
        exchange_upper = exchange.upper()

        # Crypto is 24/7
        if exchange_upper in ("DELTA", "CRYPTO", "BINANCE"):
            return True

        if not self.respect_hours:
            return True

        if check_time_utc is None:
            check_time_utc = datetime.now(UTC)
        elif check_time_utc.tzinfo is None:
            check_time_utc = UTC.localize(check_time_utc)

        # Convert to IST for evaluation
        ist_now = check_time_utc.astimezone(IST)

        # Indian markets are closed on Saturday (5) and Sunday (6)
        if ist_now.weekday() >= 5:
            return False

        current_time = ist_now.time()
        session = self.sessions.get(exchange_upper)
        if not session:
            # Default fallback for unknown exchanges: assume open
            return True

        return session["open"] <= current_time <= session["close"]

    def to_display_time(self, dt_utc: datetime, format_str: str = "%d %b %Y %H:%M %Z") -> str:
        """Convert a UTC datetime to formatted display timezone string (e.g. Asia/Kolkata)."""
        if dt_utc.tzinfo is None:
            dt_utc = UTC.localize(dt_utc)
        local_dt = dt_utc.astimezone(self.display_tz)
        return local_dt.strftime(format_str)

    def to_utc(self, dt: datetime, from_tz: Optional[str] = None) -> datetime:
        """Ensure a datetime is timezone-aware UTC."""
        if dt.tzinfo is None:
            source_tz = pytz.timezone(from_tz) if from_tz else self.display_tz
            dt = source_tz.localize(dt)
        return dt.astimezone(UTC)
