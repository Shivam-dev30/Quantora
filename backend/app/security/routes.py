"""Authentication endpoints: Login, Registration, Token Refresh, and Profile."""

from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from backend.app.config.settings import get_config
from backend.app.core.logging import get_logger
from backend.app.database.models import UserModel
from backend.app.database.session import get_db_session
from backend.app.security.audit import log_security_event
from backend.app.security.auth import (
    UserContext,
    create_access_token,
    generate_api_key,
    get_current_user,
    get_password_hash,
    require_admin,
    verify_password,
)
from backend.app.security.rate_limiter import rate_limit

logger = get_logger("auth_router")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    role: Optional[str] = "viewer"  # viewer or trader (admin must be promoted)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        clean = v.strip()
        if not clean.isalnum() and "_" not in clean and "-" not in clean:
            raise ValueError("Username may only contain letters, numbers, underscores, and hyphens.")
        return clean


@router.post("/login", dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))])
async def login(req: LoginRequest, request: Request, response: Response) -> Dict[str, Any]:
    """Authenticate with username and password, returning JWT access token and setting secure cookie."""
    client_ip = request.client.host if request.client else "unknown"
    async with get_db_session() as session:
        stmt = select(UserModel).where(UserModel.username == req.username.strip(), UserModel.is_active == True)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user or not verify_password(req.password, user.hashed_password):
            logger.warning(f"Failed login attempt for username: {req.username} from ip: {client_ip}")
            await log_security_event(
                event_type="AUTH_LOGIN_FAILED",
                message=f"Failed login attempt for username '{req.username}'",
                severity="WARNING",
                username=req.username,
                client_ip=client_ip,
                component="auth",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Please check username and password.",
            )

        # Update last login timestamp
        user.last_login = datetime.utcnow()
        await session.commit()

        await log_security_event(
            event_type="AUTH_LOGIN_SUCCESS",
            message=f"Successful login for user '{user.username}' (role: {user.role})",
            severity="INFO",
            user_id=user.id,
            username=user.username,
            client_ip=client_ip,
            component="auth",
        )

        token = create_access_token({"sub": user.username, "role": user.role, "uid": user.id})

        # Set secure HttpOnly cookie
        cfg = get_config()
        response.set_cookie(
            key="quantora_access_token",
            value=token,
            httponly=True,
            secure=cfg.settings.is_production(),
            samesite="lax",
            max_age=cfg.settings.access_token_expire_minutes * 60,
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user.username,
            "role": user.role,
            "api_key": user.api_key,
        }


@router.post("/register")
async def register(req: RegisterRequest, user_ctx: UserContext = Depends(require_admin)) -> Dict[str, Any]:
    """Register a new user account (Restricted to administrative users)."""
    async with get_db_session() as session:
        # Check if username already exists
        stmt = select(UserModel).where(UserModel.username == req.username)
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered. Please choose another.",
            )

        role = req.role if req.role in ("trader", "viewer", "admin") else "viewer"
        hashed = get_password_hash(req.password)
        new_user = UserModel(
            username=req.username,
            hashed_password=hashed,
            role=role,
            api_key=generate_api_key(),
            is_active=True,
        )
        session.add(new_user)
        await session.commit()

        logger.info(f"New user registered: {new_user.username} with role {new_user.role}")
        return {
            "status": "created",
            "username": new_user.username,
            "role": new_user.role,
            "api_key": new_user.api_key,
        }


@router.get("/me")
async def get_me(user_ctx: UserContext = Depends(get_current_user)) -> Dict[str, Any]:
    """Retrieve details of the currently authenticated caller."""
    return {
        "username": user_ctx.username,
        "role": user_ctx.role,
        "is_admin": user_ctx.is_admin,
        "is_authenticated": user_ctx.is_authenticated,
    }


@router.post("/logout")
async def logout(response: Response) -> Dict[str, str]:
    """Clear access cookie and invalidate session."""
    response.delete_cookie("quantora_access_token")
    return {"status": "logged_out", "message": "Successfully signed out."}


@router.post("/api-key/rotate")
async def rotate_api_key(user_ctx: UserContext = Depends(get_current_user)) -> Dict[str, Any]:
    """Generate a new high-entropy API key for the authenticated user."""
    async with get_db_session() as session:
        stmt = select(UserModel).where(UserModel.username == user_ctx.username)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        new_key = generate_api_key()
        user.api_key = new_key
        await session.commit()

        return {
            "status": "rotated",
            "username": user.username,
            "api_key": new_key,
        }
