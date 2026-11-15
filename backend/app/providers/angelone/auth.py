"""Angel One SmartAPI Authentication and Session Management."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx
import pyotp
from backend.app.core.exceptions import AuthenticationError
from backend.app.core.logging import get_logger

logger = get_logger("angelone_auth")

SMARTAPI_BASE_URL = "https://apiconnect.angelone.in"


class AngelOneAuthManager:
    """Manages SmartAPI login, TOTP verification, JWT tokens, and automatic token refresh."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_code: Optional[str] = None,
        password: Optional[str] = None,
        totp_secret: Optional[str] = None,
        base_url: str = SMARTAPI_BASE_URL,
    ) -> None:
        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.totp_secret = totp_secret
        self.base_url = base_url

        self.jwt_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        """Returns True if all required credentials are present."""
        return bool(
            self.api_key and self.client_code and self.password and self.totp_secret
        )

    def generate_totp(self) -> str:
        """Generate time-based 6-digit TOTP token using pyotp."""
        if not self.totp_secret:
            raise AuthenticationError("Angel One TOTP secret is missing.")
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()

    def get_auth_headers(self) -> Dict[str, str]:
        """Headers required by SmartAPI secure endpoints."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "106.193.147.98",
            "X-MACAddress": "fe80::216e:6507:4b90:3719",
            "X-PrivateKey": self.api_key or "",
        }
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        return headers

    async def login(self) -> Dict[str, str]:
        """Perform login using client code, password, and TOTP."""
        if not self.is_configured:
            logger.warning(
                "Angel One credentials incomplete. Running in simulation/mock mode."
            )
            self.jwt_token = "mock_angel_jwt_token"
            self.refresh_token = "mock_angel_refresh_token"
            self.feed_token = "mock_angel_feed_token"
            self.token_expiry = datetime.utcnow() + timedelta(hours=8)
            return {
                "jwtToken": self.jwt_token,
                "refreshToken": self.refresh_token,
                "feedToken": self.feed_token,
            }

        async with self._lock:
            totp = self.generate_totp()
            payload = {
                "clientcode": self.client_code,
                "password": self.password,
                "totp": totp,
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "106.193.147.98",
                "X-MACAddress": "fe80::216e:6507:4b90:3719",
                "X-PrivateKey": self.api_key or "",
            }

            url = f"{self.base_url}/rest/auth/angelbroking/user/v1/loginByPassword"
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp_data = resp.json()

                    if resp.status_code != 200 or not resp_data.get("status"):
                        error_msg = resp_data.get("message", "Unknown login failure")
                        logger.error(f"Angel One login failed: {error_msg}")
                        raise AuthenticationError(f"SmartAPI login rejected: {error_msg}")

                    data = resp_data.get("data", {})
                    self.jwt_token = data.get("jwtToken")
                    self.refresh_token = data.get("refreshToken")
                    self.feed_token = data.get("feedToken")
                    # Tokens typically valid for 24h, refresh every 6 hours
                    self.token_expiry = datetime.utcnow() + timedelta(hours=6)

                    logger.info("Angel One SmartAPI login successful. Session initialized.")
                    return {
                        "jwtToken": self.jwt_token or "",
                        "refreshToken": self.refresh_token or "",
                        "feedToken": self.feed_token or "",
                    }
            except httpx.HTTPError as e:
                logger.error(f"Network error during Angel One login: {e}")
                raise AuthenticationError(f"Angel One connection failed: {e}")

    async def get_valid_jwt(self) -> str:
        """Returns valid JWT token, refreshing if needed."""
        if not self.jwt_token or (
            self.token_expiry and datetime.utcnow() >= self.token_expiry
        ):
            await self.login()
        return self.jwt_token or ""
