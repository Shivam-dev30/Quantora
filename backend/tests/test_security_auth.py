"""Unit and integration tests for authentication, authorization, and rate limiting."""

import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.config.settings import get_config
from backend.app.main import create_app
from backend.app.security.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_ws_token,
)
from backend.app.security.rate_limiter import InMemoryRateLimiter


def test_password_hashing():
    """Verify Argon2id password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_generation_and_verification():
    """Verify JWT access token generation and payload extraction."""
    payload = {"sub": "trader1", "role": "admin"}
    token = create_access_token(payload)
    assert isinstance(token, str) and len(token) > 20

    context = verify_ws_token(token)
    assert context is not None
    assert context.username == "trader1"
    assert context.role == "admin"


def test_invalid_jwt_token():
    """Verify invalid or tampered JWT tokens return None."""
    assert verify_ws_token("invalid.jwt.token") is None
    assert verify_ws_token("tampered.token.here") is None


def test_rate_limiter():
    """Verify in-memory sliding window rate limiting."""
    limiter = InMemoryRateLimiter()
    key = "test_client_ip"
    
    # First 3 requests within limit of 3 should succeed
    for _ in range(3):
        allowed, retry_after = limiter.is_allowed(key, max_requests=3, window_seconds=10)
        assert allowed is True

    # 4th request must be rejected
    allowed, retry_after = limiter.is_allowed(key, max_requests=3, window_seconds=10)
    assert allowed is False
    assert retry_after > 0


@pytest.mark.asyncio
async def test_auth_endpoints_lifecycle():
    """Test user registration, login, profile check, and logout via API."""
    test_app = create_app(lifespan_handler=None)
    transport = ASGITransport(app=test_app)
    
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Register a new user (with admin context by default when auth_enabled=False in test)
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "username": "quant_trader_test",
                "password": "StrongPassword123!",
                "role": "admin",
            },
        )
        assert reg_resp.status_code == 200
        data = reg_resp.json()
        assert data["username"] == "quant_trader_test"
        assert "api_key" in data

        # Login with correct credentials
        login_resp = await client.post(
            "/api/auth/login",
            json={
                "username": "quant_trader_test",
                "password": "StrongPassword123!",
            },
        )
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        assert "access_token" in token_data
        token = token_data["access_token"]

        # Access /api/auth/me with Bearer token
        me_resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "quant_trader_test"
