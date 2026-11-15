"""Security module providing Argon2id password hashing, JWT/API Key auth, RBAC, and rate limiting."""

from backend.app.security.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    require_admin,
    require_viewer,
    verify_password,
    verify_token,
    UserContext,
)
from backend.app.security.rate_limiter import rate_limit

__all__ = [
    "create_access_token",
    "get_current_user",
    "get_password_hash",
    "require_admin",
    "require_viewer",
    "verify_password",
    "verify_token",
    "UserContext",
    "rate_limit",
]
