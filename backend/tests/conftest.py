"""Pytest configuration and test isolation fixtures."""

import pytest_asyncio
from sqlalchemy import text
from backend.app.database.session import get_db_session, init_db


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Ensure database tables exist and are clean before each test."""
    await init_db()
    async with get_db_session() as session:
        await session.execute(text("DELETE FROM notification_deliveries;"))
        await session.execute(text("DELETE FROM signals;"))
        await session.execute(text("DELETE FROM candles_metadata;"))
        await session.commit()
    yield
