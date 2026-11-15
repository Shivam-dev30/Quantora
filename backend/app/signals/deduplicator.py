"""Signal Deduplicator with in-memory cache and persistent database check."""

import asyncio
from typing import Set
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.app.core.logging import get_logger
from backend.app.database.models import SignalModel
from backend.app.database.session import get_db_session
from backend.app.models.signal import SignalEvent

logger = get_logger("signal_deduplicator")


class SignalDeduplicator:
    """Guarantees that identical crossover signals are never emitted or alerted more than once."""

    def __init__(self, memory_cache_size: int = 50000) -> None:
        self._memory_cache: Set[str] = set()
        self._max_cache_size = memory_cache_size
        self._lock = asyncio.Lock()

    async def restore_from_db(self) -> int:
        """Load recent signal IDs from database on startup to prevent post-restart duplicates."""
        count = 0
        try:
            async with get_db_session() as session:
                query = select(SignalModel.signal_id).order_by(SignalModel.id.desc()).limit(10000)
                result = await session.execute(query)
                rows = result.scalars().all()
                for sig_id in rows:
                    self._memory_cache.add(sig_id)
                    count += 1
            logger.info(f"Restored {count} historical signal IDs into deduplication cache.")
        except Exception as e:
            logger.warning(f"Could not restore signal IDs from database: {e}")
        return count

    async def is_duplicate(self, signal_id: str) -> bool:
        """Check if signal_id exists in fast memory cache or database."""
        if signal_id in self._memory_cache:
            return True

        # Secondary check in persistent database
        try:
            async with get_db_session() as session:
                query = select(SignalModel.id).where(SignalModel.signal_id == signal_id)
                result = await session.execute(query)
                exists = result.scalar_one_or_none() is not None
                if exists:
                    self._memory_cache.add(signal_id)
                    return True
        except Exception as e:
            logger.error(f"Error querying database for duplicate signal check: {e}")

        return False

    async def register_signal(self, signal: SignalEvent) -> bool:
        """
        Atomically check and record a new signal.
        Returns True if the signal is NEW and successfully saved.
        Returns False if it is a duplicate.
        """
        async with self._lock:
            if await self.is_duplicate(signal.signal_id):
                logger.info(f"Duplicate signal detected and dropped: {signal.signal_id}")
                return False

            # Persist to database
            try:
                async with get_db_session() as session:
                    db_signal = SignalModel(
                        signal_id=signal.signal_id,
                        provider=signal.provider,
                        asset_class=signal.asset_class,
                        exchange=signal.exchange,
                        instrument_id=signal.instrument_id,
                        symbol=signal.symbol,
                        timeframe=signal.timeframe,
                        signal_type=signal.signal_type.value,
                        candle_timestamp=signal.candle_timestamp,
                        price=signal.price,
                        ema100=signal.ema100,
                        ema200=signal.ema200,
                        previous_ema100=signal.previous_ema100,
                        previous_ema200=signal.previous_ema200,
                        strategy_version=signal.strategy_version,
                        is_catchup=getattr(signal, "is_catchup", False),
                        created_at=signal.created_at,
                    )
                    session.add(db_signal)
                    await session.commit()

                # Add to memory cache
                self._memory_cache.add(signal.signal_id)
                if len(self._memory_cache) > self._max_cache_size:
                    # Drop arbitrary oldest elements to constrain memory
                    self._memory_cache.pop()

                logger.info(f"Unique signal saved to DB: {signal.signal_id}")
                return True

            except IntegrityError:
                logger.info(f"Database rejected duplicate signal_id: {signal.signal_id}")
                self._memory_cache.add(signal.signal_id)
                return False
            except Exception as e:
                logger.exception(f"Error saving signal {signal.signal_id}: {e}")
                return False

    async def mark_catchup(self, signal_id: str) -> None:
        """Mark an existing signal as catch-up in the database."""
        try:
            async with get_db_session() as session:
                stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
                res = await session.execute(stmt)
                db_sig = res.scalar_one_or_none()
                if db_sig:
                    db_sig.is_catchup = True
                    await session.commit()
        except Exception as e:
            logger.warning(f"Could not mark signal {signal_id} as catchup: {e}")
