"""Audit logging utilities for security and system events."""

from datetime import datetime
from typing import Optional
from backend.app.core.logging import get_logger
from backend.app.database.models import SystemEventModel
from backend.app.database.session import get_db_session

logger = get_logger("audit")


async def log_security_event(
    event_type: str,
    message: str,
    severity: str = "INFO",
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    client_ip: Optional[str] = None,
    component: str = "security",
) -> None:
    """Persist security event to SystemEventModel and system log."""
    log_msg = f"[{severity}] [{event_type}] user={username or 'anonymous'} ip={client_ip or 'unknown'}: {message}"
    if severity == "CRITICAL" or severity == "ERROR":
        logger.error(log_msg)
    elif severity == "WARNING":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    try:
        async with get_db_session() as session:
            event = SystemEventModel(
                event_type=event_type,
                provider=component,
                description=f"{message} (user={username or 'unknown'}, ip={client_ip or 'unknown'})",
                severity=severity,
                created_at=datetime.utcnow(),
            )
            session.add(event)
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to persist security audit event to database: {e}")
