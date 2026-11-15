"""SQLAlchemy ORM models for instruments, signals, candles, deliveries, and audit events."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class InstrumentModel(Base):
    """Normalized instrument master cached in database."""

    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(32), nullable=False, index=True)
    exchange = Column(String(32), nullable=False, index=True)
    symbol = Column(String(64), nullable=False, index=True)
    instrument_id = Column(String(64), nullable=False, index=True)  # Token or provider product ID
    name = Column(String(64), nullable=True)
    asset_class = Column(String(32), nullable=False, index=True)  # equity, equity_futures, etc.
    instrument_type = Column(String(32), nullable=True)
    expiry = Column(String(32), nullable=True, index=True)
    strike = Column(Float, nullable=True)
    option_type = Column(String(8), nullable=True)  # CE or PE
    lot_size = Column(Integer, default=1)
    tick_size = Column(Float, default=0.05)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_inst_provider_exchange_token", "provider", "exchange", "instrument_id"),
        Index("idx_inst_provider_symbol", "provider", "symbol"),
    )


class CandleMetadataModel(Base):
    """Tracks state and latest timestamp of ingested candles per instrument and timeframe."""

    __tablename__ = "candles_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(32), nullable=False)
    exchange = Column(String(32), nullable=False)
    instrument_id = Column(String(64), nullable=False)
    symbol = Column(String(64), nullable=False)
    timeframe = Column(String(16), nullable=False)
    last_candle_timestamp = Column(DateTime, nullable=False)
    last_close_price = Column(Float, nullable=False)
    total_candles_processed = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_candle_meta_unique", "provider", "instrument_id", "timeframe", unique=True),
    )


class SignalModel(Base):
    """Persistent storage of generated crossover signals with deduplication key."""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(191), nullable=False, unique=True, index=True)
    provider = Column(String(32), nullable=False, index=True)
    asset_class = Column(String(32), nullable=False, index=True)
    exchange = Column(String(32), nullable=False, index=True)
    instrument_id = Column(String(64), nullable=False)
    symbol = Column(String(64), nullable=False, index=True)
    timeframe = Column(String(16), nullable=False, index=True)
    signal_type = Column(String(16), nullable=False, index=True)  # BULLISH | BEARISH
    candle_timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Float, nullable=False)
    ema100 = Column(Float, nullable=False)
    ema200 = Column(Float, nullable=False)
    previous_ema100 = Column(Float, nullable=False)
    previous_ema200 = Column(Float, nullable=False)
    strategy_version = Column(String(32), nullable=False, default="ema100_200_v1")
    is_catchup = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    deliveries = relationship(
        "NotificationDeliveryModel", back_populates="signal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_sig_query", "asset_class", "exchange", "symbol", "timeframe", "created_at"),
    )


class NotificationDeliveryModel(Base):
    """Tracks delivery status of an alert to a specific notification channel."""

    __tablename__ = "notification_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(191), ForeignKey("signals.signal_id"), nullable=False, index=True)
    channel = Column(String(32), nullable=False, index=True)  # telegram, email, whatsapp
    status = Column(String(16), nullable=False, index=True)  # PENDING, SENT, FAILED
    attempt_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    signal = relationship("SignalModel", back_populates="deliveries")

    __table_args__ = (
        Index("idx_delivery_sig_chan", "signal_id", "channel"),
    )


class SystemEventModel(Base):
    """Audit log for system lifecycle events, connection drops, and recoveries."""

    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(64), nullable=False, index=True)
    provider = Column(String(32), nullable=True, index=True)
    description = Column(Text, nullable=False)
    severity = Column(String(16), default="INFO")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class UserModel(Base):
    """User account model for authentication, RBAC, and multi-tenant access."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="admin")  # admin, trader, viewer
    api_key = Column(String(128), nullable=True, unique=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

