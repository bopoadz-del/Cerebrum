"""
Rate Limiting

Provides rate limiting using slowapi with Redis backend.
"""

from typing import Optional

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request, Response

from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import get_rate_limit_redis

logger = get_logger(__name__)


class RateLimitManager:
    """
    Rate limiting manager with Redis backend.
    
    Provides configurable rate limits for different endpoints
    and user types.
    """
    
    def __init__(self) -> None:
        """Initialize rate limit manager."""
        self._limiter: Optional[Limiter] = None
    
    def get_limiter(self) -> Limiter:
        """
        Get or create rate limiter instance.
        
        Returns:
            Limiter instance
        """
        if self._limiter is None:
            # Create Redis storage for rate limiting
            redis_client = get_rate_limit_redis()
            
            self._limiter = Limiter(
                key_func=self._get_rate_limit_key,
                default_limits=[settings.RATE_LIMIT_DEFAULT],
                storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/3",
                storage_options={"password": settings.REDIS_PASSWORD} if settings.REDIS_PASSWORD else {},
                strategy="fixed-window-elastic-expiry",
                enabled=settings.RATE_LIMIT_ENABLED,
            )
            
            logger.info("Rate limiter initialized")
        
        return self._limiter
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Get rate limit key for request.
        
        Uses user ID if authenticated, otherwise uses IP address.
        
        Args:
            request: HTTP request
            
        Returns:
            Rate limit key
        """
        # Try to get user ID from request state
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return f"user:{user.id}"
        
        # Fall back to IP address
        return get_remote_address(request)
    
    def setup_rate_limiting(self, app) -> None:
        """
        Set up rate limiting for FastAPI application.
        
        Args:
            app: FastAPI application
        """
        limiter = self.get_limiter()
        
        # Add limiter to app state
        app.state.limiter = limiter
        
        # Add exception handler for rate limit exceeded
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        
        logger.info("Rate limiting configured")


# Global rate limit manager
rate_limit_manager = RateLimitManager()


def setup_rate_limiting(app) -> None:
    """Set up rate limiting for application."""
    rate_limit_manager.setup_rate_limiting(app)


# Rate limit decorators

def limit(
    limit_string: str,
    per_minute: Optional[int] = None,
    per_hour: Optional[int] = None,
    per_day: Optional[int] = None,
):
    """
    Rate limit decorator.
    
    Args:
        limit_string: Rate limit string (e.g., "100/minute")
        per_minute: Requests per minute
        per_hour: Requests per hour
        per_day: Requests per day
        
    Returns:
        Decorator function
        
    Example:
        @router.get("/items")
        @limit("100/minute")
        async def get_items():
            return {"items": []}
    """
    limiter = rate_limit_manager.get_limiter()
    return limiter.limit(limit_string)


def limit_by_user(
    requests: int,
    period: str = "minute",
):
    """
    Rate limit by user ID.
    
    Args:
        requests: Number of requests allowed
        period: Time period (minute, hour, day)
        
    Returns:
        Decorator function
    """
    limit_string = f"{requests}/{period}"
    return limit(limit_string)


def limit_by_ip(
    requests: int,
    period: str = "minute",
):
    """
    Rate limit by IP address.
    
    Args:
        requests: Number of requests allowed
        period: Time period (minute, hour, day)
        
    Returns:
        Decorator function
    """
    limit_string = f"{requests}/{period}"
    limiter = rate_limit_manager.get_limiter()
    return limiter.limit(limit_string, key_func=get_remote_address)


# Common rate limits
LOGIN_RATE_LIMIT = "5/minute"
REGISTER_RATE_LIMIT = "3/hour"
PASSWORD_RESET_RATE_LIMIT = "3/hour"
API_DEFAULT_RATE_LIMIT = "100/minute"
ADMIN_RATE_LIMIT = "50/minute"
