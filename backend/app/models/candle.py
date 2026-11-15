"""Unified Market Candle data model across Indian and Crypto providers."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class MarketCandle(BaseModel):
    """Normalized OHLCV candle representation."""

    provider: str = Field(description="Data provider name: angelone, delta, etc.")
    asset_class: Literal["equity", "equity_futures", "equity_options", "commodity", "crypto"] = (
        Field(description="Asset classification")
    )
    exchange: str = Field(description="Exchange identifier: NSE, NFO, MCX, DELTA")
    symbol: str = Field(description="Trading symbol: RELIANCE, NIFTY26OCTFUT, BTCUSD")
    instrument_id: str = Field(description="Broker token or product ID")
    timeframe: str = Field(description="Candle timeframe: 1m, 5m, 15m, 1h, 1d")
    timestamp: datetime = Field(description="UTC start timestamp of the candle")
    open: float = Field(description="Opening price")
    high: float = Field(description="Highest price")
    low: float = Field(description="Lowest price")
    close: float = Field(description="Closing price")
    volume: float = Field(default=0.0, description="Volume traded")
    is_closed: bool = Field(
        default=True,
        description="Whether this candle is finalized and closed (True) or forming in real-time (False)",
    )

    @field_validator("timestamp")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            # Convert to naive UTC or ensure UTC
            return v.replace(tzinfo=None)
        return v

    def to_summary(self) -> str:
        return (
            f"[{self.exchange}:{self.symbol}] {self.timeframe} "
            f"O:{self.open} H:{self.high} L:{self.low} C:{self.close} V:{self.volume} "
            f"@ {self.timestamp.isoformat()} (closed={self.is_closed})"
        )
