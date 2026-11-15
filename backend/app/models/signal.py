"""Signal definitions, crossover types, and deterministic signal identity generator."""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class SignalType(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NONE = "NONE"


def generate_signal_id(
    provider: str,
    exchange: str,
    instrument_id: str,
    timeframe: str,
    candle_timestamp: datetime,
    signal_type: SignalType | str,
    strategy_version: str = "ema100_200_v1",
) -> str:
    """Generate a deterministic, tamper-proof signal identity string for deduplication."""
    # Format timestamp to ISO 8601 UTC with seconds precision
    ts_str = candle_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    sig_str = signal_type.value if isinstance(signal_type, SignalType) else str(signal_type)

    return (
        f"{provider.lower()}:{exchange.upper()}:{instrument_id}:{timeframe}:"
        f"{ts_str}:{sig_str.upper()}:{strategy_version}"
    )


class SignalEvent(BaseModel):
    """Payload representing an identified technical indicator crossover signal."""

    signal_id: str = Field(description="Deterministic deduplication identity string")
    provider: str
    asset_class: str
    exchange: str
    instrument_id: str
    symbol: str
    timeframe: str
    signal_type: SignalType
    candle_timestamp: datetime
    price: float
    ema100: float
    ema200: float
    previous_ema100: float
    previous_ema200: float
    strategy_version: str = "ema100_200_v1"
    is_catchup: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        provider: str,
        asset_class: str,
        exchange: str,
        instrument_id: str,
        symbol: str,
        timeframe: str,
        signal_type: SignalType,
        candle_timestamp: datetime,
        price: float,
        ema100: float,
        ema200: float,
        previous_ema100: float,
        previous_ema200: float,
        strategy_version: str = "ema100_200_v1",
        is_catchup: bool = False,
    ) -> "SignalEvent":
        sig_id = generate_signal_id(
            provider=provider,
            exchange=exchange,
            instrument_id=instrument_id,
            timeframe=timeframe,
            candle_timestamp=candle_timestamp,
            signal_type=signal_type,
            strategy_version=strategy_version,
        )
        return cls(
            signal_id=sig_id,
            provider=provider,
            asset_class=asset_class,
            exchange=exchange,
            instrument_id=instrument_id,
            symbol=symbol,
            timeframe=timeframe,
            signal_type=signal_type,
            candle_timestamp=candle_timestamp,
            price=price,
            ema100=ema100,
            ema200=ema200,
            previous_ema100=previous_ema100,
            previous_ema200=previous_ema200,
            strategy_version=strategy_version,
            is_catchup=is_catchup,
        )
