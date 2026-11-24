"""Security middleware, headers, admin authorization, and rate limiting."""

import uuid

from fastapi import HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# Rate limiter instance (in-memory per client IP, SECURITY.md T6)
limiter = Limiter(key_func=get_remote_address, default_limits=[])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce strict HTTP security headers on all API responses (SECURITY.md §2)."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        path = request.url.path

        # Relaxed CSP ONLY for interactive documentation routes
        # Swagger UI and ReDoc require JS/CSS from cdn.jsdelivr.net and logos from fastapi.tiangolo.com
        if path in {"/docs", "/redoc", "/openapi.json"} or path.startswith(("/docs/", "/redoc/")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "connect-src 'self'"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=(), interest-cohort=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request has a correlation ID for structured observability."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def verify_localhost_admin(request: Request) -> None:
    """Enforce localhost-only access for administrative operations (SECURITY.md T7).

    Rejects:
    1. Any non-localhost client host (must be 127.0.0.1, ::1, or localhost).
    2. Any request carrying proxy forwarding headers (X-Forwarded-For, X-Forwarded-Host, X-Real-IP, Forwarded).
       Only direct local calls (e.g. curl to 127.0.0.1:8000) may use admin endpoints.
    """
    client_host = request.client.host if request.client else ""
    allowed_hosts = {"127.0.0.1", "::1", "localhost"}
    if client_host not in allowed_hosts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin endpoints are accessible only from localhost.",
        )

    # Reject any request arriving via reverse proxies (SECURITY.md T7)
    proxy_headers = ("x-forwarded-for", "x-forwarded-host", "x-real-ip", "forwarded")
    for hdr in proxy_headers:
        if hdr in request.headers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin endpoints cannot be accessed through reverse proxies ({hdr} detected).",
            )
