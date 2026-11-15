"""In-memory Token Bucket / Sliding Window Rate Limiter (DoS & Abuse Prevention)."""

import time
from typing import Callable, Dict, Tuple
from fastapi import HTTPException, Request, status
from backend.app.core.logging import get_logger

logger = get_logger("rate_limiter")


class InMemoryRateLimiter:
    """Sliding-window rate limiter per client IP / identifier."""

    def __init__(self):
        # Key: client_key -> List of timestamps
        self._history: Dict[str, list[float]] = {}
        self._last_cleanup = time.time()

    def is_allowed(self, client_key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - window_seconds

        # Periodic cleanup of keys older than 10 minutes
        if now - self._last_cleanup > 300:
            self._cleanup(cutoff - 300)
            self._last_cleanup = now

        timestamps = self._history.setdefault(client_key, [])
        # Prune timestamps outside current window
        self._history[client_key] = [t for t in timestamps if t > cutoff]

        if len(self._history[client_key]) >= max_requests:
            oldest = self._history[client_key][0]
            retry_after = max(1, int(oldest + window_seconds - now))
            return False, retry_after

        self._history[client_key].append(now)
        return True, 0

    def _cleanup(self, expiration_cutoff: float) -> None:
        stale_keys = [
            k for k, v in self._history.items()
            if not v or v[-1] < expiration_cutoff
        ]
        for k in stale_keys:
            self._history.pop(k, None)


_limiter = InMemoryRateLimiter()


def rate_limit(max_requests: int = 60, window_seconds: int = 60) -> Callable:
    """
    FastAPI dependency factory enforcing rate limits.
    Returns HTTP 429 with Retry-After header when threshold is breached.
    """
    async def _dependency(request: Request):
        # Identify client by IP or API key
        client_ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-Key", "")
        client_key = f"{client_ip}:{api_key[:8]}" if api_key else client_ip

        allowed, retry_after = _limiter.is_allowed(client_key, max_requests, window_seconds)
        if not allowed:
            logger.warning(f"Rate limit exceeded for client {client_ip} on {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency
