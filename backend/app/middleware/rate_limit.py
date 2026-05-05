"""
Rate limiter setup and safe exception handling.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings


def safe_rate_limit_handler(request: Request, exc: Exception):
    if isinstance(exc, RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": f"Rate limit exceeded: {getattr(exc, 'detail', str(exc))}"},
        )
    status_code = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", str(exc))
    return JSONResponse(status_code=status_code, content={"error": detail})


def get_user_or_ip_key(request: Request) -> str:
    """
    Rate-limit key: use authenticated user ID when available, fall back to IP.

    This prevents shared NAT/mobile IPs from exhausting a single IP bucket.
    The user ID is extracted from the JWT Bearer token without a full DB round-trip.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            import jwt as _jwt
            payload = _jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False},  # expiry checked separately by deps
            )
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass  # fall through to IP-based key
    return get_remote_address(request)


# Monkey-patch slowapi's global fallback handler
import slowapi.extension
import slowapi.middleware
slowapi.extension._rate_limit_exceeded_handler = safe_rate_limit_handler
slowapi.middleware._rate_limit_exceeded_handler = safe_rate_limit_handler

limiter = Limiter(
    key_func=get_user_or_ip_key,
    default_limits=["200/minute", "2000/hour"],
    storage_uri=settings.redis_url,
)
