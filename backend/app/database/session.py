"""Database connection management and async session context providers."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.app.config.settings import get_config
from backend.app.core.logging import get_logger
from backend.app.database.models import Base

logger = get_logger("database")

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        cfg = get_config()
        db_url = cfg.settings.database_url

        # Ensure sqlite uses check_same_thread=False
        connect_args = {}
        if "sqlite" in db_url:
            connect_args = {"check_same_thread": False}

        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def init_db() -> None:
    """Initialize database tables and set SQLite WAL mode for concurrent operations."""
    engine = get_engine()
    async with engine.begin() as conn:
        # If SQLite, enable WAL journal mode for performance and concurrent readers/writers
        if "sqlite" in engine.url.drivername:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
        await conn.run_sync(Base.metadata.create_all)
        # Ensure is_catchup column exists in signals table
        try:
            await conn.execute(text("ALTER TABLE signals ADD COLUMN is_catchup BOOLEAN DEFAULT 0;"))
        except Exception:
            pass  # Column already exists
    logger.info("Database schema initialized successfully.")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an asynchronous transactional session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
