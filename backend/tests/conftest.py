"""Pytest configuration and test isolation fixtures."""

import os
import tempfile
from pathlib import Path
import pytest_asyncio
from sqlalchemy import text
from backend.app.database.session import close_engine, get_db_session, init_db, set_test_engine

_TEST_DB_FILE = Path(tempfile.gettempdir()) / f"quantora_test_{os.getpid()}.db"
_TEST_DB_URL = f"sqlite+aiosqlite:///{_TEST_DB_FILE.as_posix()}"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def configure_test_database():
    """Ensure automated tests use an isolated temporary database, NEVER the production/dev DB."""
    # Ensure any stale test file from a prior crash is removed
    for suffix in ("", "-shm", "-wal"):
        stale = Path(f"{_TEST_DB_FILE}{suffix}")
        if stale.exists():
            try:
                stale.unlink()
            except Exception:
                pass

    # Override environment variable so any config reloads also point to test DB
    os.environ["DATABASE_URL"] = _TEST_DB_URL

    # Configure isolated engine and initialize schema
    await set_test_engine(_TEST_DB_URL)
    await init_db()

    yield

    # Clean teardown: dispose engine and delete temporary files
    await close_engine()
    for suffix in ("", "-shm", "-wal"):
        p = Path(f"{_TEST_DB_FILE}{suffix}")
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Ensure database tables exist and are clean before each test in the isolated DB."""
    async with get_db_session() as session:
        await session.execute(text("DELETE FROM notification_deliveries;"))
        await session.execute(text("DELETE FROM signals;"))
        await session.execute(text("DELETE FROM candles_metadata;"))
        await session.commit()
    yield
