"""Authentication, Argon2id password verification, JWT handling, and Role-Based Access Control."""

from datetime import datetime, timedelta
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, Query, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from backend.app.config.settings import get_config
from backend.app.core.logging import get_logger
from backend.app.database.models import UserModel
from backend.app.database.session import get_db_session

logger = get_logger("security_auth")

# Argon2id primary password context with bcrypt compatibility
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__type="ID",  # Argon2id variant
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,  # 3 iterations
    argon2__parallelism=4,  # 4 threads
)

security_bearer = HTTPBearer(auto_error=False)


class UserContext(BaseModel):
    """Context object representing the authenticated caller."""
    user_id: Optional[int] = None
    username: str
    role: str = "admin"  # "admin" | "trader" | "viewer"
    is_admin: bool = True
    is_authenticated: bool = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against Argon2id hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Compute Argon2id hash of a password."""
    return pwd_context.hash(password)


def generate_api_key() -> str:
    """Generate high-entropy random API key (32 bytes hex)."""
    return f"qy_{secrets.token_hex(24)}"


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode JWT token with payload, expiration, and HMAC-SHA256 signature."""
    cfg = get_config()
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=cfg.settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(
        to_encode,
        cfg.settings.secret_key,
        algorithm=cfg.settings.jwt_algorithm,
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT access token, returning payload or None."""
    cfg = get_config()
    try:
        payload = jwt.decode(
            token,
            cfg.settings.secret_key,
            algorithms=[cfg.settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.debug(f"JWT verification failed: {e}")
        return None


async def get_current_user(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> UserContext:
    """
    FastAPI dependency to authenticate requests.
    Validates:
      1. Bearer Token (Authorization: Bearer <token>)
      2. Cookie (quantora_access_token=<token>)
      3. Custom Header (X-API-Key: <key>)
    If auth is disabled (dev mode) and not production, returns dev_admin context.
    """
    cfg = get_config()

    # 1. Check API Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        if cfg.settings.admin_api_key and secrets.compare_digest(api_key, cfg.settings.admin_api_key):
            return UserContext(username="api_admin", role="admin", is_admin=True)

        async with get_db_session() as session:
            stmt = select(UserModel).where(UserModel.api_key == api_key, UserModel.is_active == True)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            if user:
                return UserContext(
                    user_id=user.id,
                    username=user.username,
                    role=user.role,
                    is_admin=(user.role == "admin"),
                )

    # 2. Extract JWT token from Bearer header or cookie
    token = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    else:
        token = request.cookies.get("quantora_access_token")

    if token:
        payload = verify_token(token)
        if payload and "sub" in payload:
            username = payload["sub"]
            role = payload.get("role", "viewer")

            try:
                async with get_db_session() as session:
                    stmt = select(UserModel).where(UserModel.username == username, UserModel.is_active == True)
                    res = await session.execute(stmt)
                    user = res.scalar_one_or_none()
                    if user:
                        return UserContext(
                            user_id=user.id,
                            username=user.username,
                            role=user.role,
                            is_admin=(user.role == "admin"),
                        )
            except Exception:
                pass

            return UserContext(
                username=username,
                role=role,
                is_admin=(role == "admin"),
            )
        elif cfg.settings.auth_enabled or cfg.settings.is_production():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or tampered authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Development fallback when authentication is explicitly disabled and no credentials provided
    if not cfg.settings.auth_enabled and not cfg.settings.is_production():
        return UserContext(
            user_id=1,
            username="dev_admin",
            role="admin",
            is_admin=True,
            is_authenticated=True,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Bearer token or API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Enforces that the caller has administrative privileges."""
    if not user.is_admin and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to perform this action.",
        )
    return user


async def require_viewer(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Enforces that the caller has at least viewer access."""
    if not user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid authentication credentials required.",
        )
    return user


def verify_ws_token(token: Optional[str]) -> Optional[UserContext]:
    """Helper to validate WebSocket handshake query tokens."""
    cfg = get_config()

    # If token is provided (non-empty string), always attempt to validate it first
    if token and token.strip():
        if cfg.settings.admin_api_key and secrets.compare_digest(token, cfg.settings.admin_api_key):
            return UserContext(username="api_ws", role="admin", is_admin=True)

        payload = verify_token(token)
        if payload and "sub" in payload:
            return UserContext(
                username=payload["sub"],
                role=payload.get("role", "viewer"),
                is_admin=(payload.get("role") == "admin"),
            )
        # If a token was provided but failed validation, return None
        return None

    # If no token provided and auth is disabled in dev mode, allow dev user
    if not cfg.settings.auth_enabled and not cfg.settings.is_production():
        return UserContext(username="ws_dev", role="admin", is_admin=True)

    return None
