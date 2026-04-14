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


# Monkey-patch slowapi's global fallback handler
import slowapi.extension
import slowapi.middleware
slowapi.extension._rate_limit_exceeded_handler = safe_rate_limit_handler
slowapi.middleware._rate_limit_exceeded_handler = safe_rate_limit_handler

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute", "1000/hour"],
    storage_uri=settings.redis_url,
)
