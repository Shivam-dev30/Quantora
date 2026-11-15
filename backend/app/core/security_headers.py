"""HTTP Security Headers Middleware (OWASP Secure Headers Project Aligned)."""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces defensive HTTP response headers across all API and static responses."""

    def __init__(self, app, is_production: bool = False):
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Anti-Clickjacking: prevent dashboard embedding in untrusted iframes
        response.headers["X-Frame-Options"] = "DENY"

        # Anti-MIME Sniffing: force browser to adhere to declared content-type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer Policy: restrict cross-origin referrer leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy: disable unused hardware features
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=()"

        # Content Security Policy (CSP): restrict resource execution
        # Permits self, inline scripts/styles needed for compiled Vite React bundle and WebSocket feeds
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        # HSTS: Enforce HTTPS in production environments
        if self.is_production or request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
