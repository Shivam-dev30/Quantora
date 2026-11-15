"""Unified Instrument domain models and filtering specifications."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

AssetClass = Literal["equity", "equity_futures", "equity_options", "commodity", "crypto"]


class InstrumentDefinition(BaseModel):
    """Complete specification of a tradable instrument."""

    provider: str
    exchange: str
    symbol: str
    instrument_id: str
    name: Optional[str] = None
    asset_class: AssetClass
    instrument_type: Optional[str] = None  # EQUITY, FUTIDX, OPTIDX, FUTSTK, OPTSTK, FUTCOM, PERP, etc.
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[Literal["CE", "PE"]] = None
    lot_size: int = 1
    tick_size: float = 0.05
    is_active: bool = True
    underlying: Optional[str] = None

    def display_name(self) -> str:
        """Formatted human-readable instrument name."""
        if self.asset_class == "equity_options":
            return f"{self.underlying or self.symbol} {self.strike} {self.option_type} ({self.expiry})"
        if self.asset_class in ("equity_futures", "commodity") and self.expiry:
            return f"{self.symbol} ({self.expiry})"
        return self.symbol


class InstrumentFilter(BaseModel):
    """Criteria for filtering the universe to monitor."""

    asset_classes: Optional[List[AssetClass]] = None
    exchanges: Optional[List[str]] = None
    symbols: Optional[List[str]] = None
    exclude_symbols: Optional[List[str]] = None
    mode: Literal["all", "selected"] = "selected"
    expiry_mode: Optional[Literal["current", "next", "specific"]] = "current"
    monitor_underlying_only: bool = False
