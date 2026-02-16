"""
Sentry Integration

Provides error tracking and performance monitoring using Sentry SDK.
"""

import logging
from typing import Any, Optional

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry SDK for error tracking.
    
    Configures Sentry with appropriate integrations and sampling
    based on the environment.
    """
    if not settings.SENTRY_ENABLED or not settings.SENTRY_DSN:
        logger.info("Sentry is disabled")
        return
    
    # Configure logging integration
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )
    
    # Initialize Sentry
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        release=settings.APP_VERSION,
        
        # Tracing configuration
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        
        # Enable profiling in production
        profiles_sample_rate=0.1 if settings.is_production else 0.0,
        
        # Integrations
        integrations=[
            sentry_logging,
            StarletteIntegration(),
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
            AsyncioIntegration(),
        ],
        
        # Additional configuration
        send_default_pii=False,  # Don't send personally identifiable information
        attach_stacktrace=True,
        include_source_context=True,
        include_local_variables=False,  # Security: don't include local variables
        
        # Before send hook for filtering
        before_send=before_send_event,
        
        # Tags
        default_tags={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
        },
    )
    
    logger.info(
        "Sentry initialized",
        environment=settings.SENTRY_ENVIRONMENT,
        release=settings.APP_VERSION,
    )


def before_send_event(event: dict, hint: dict) -> Optional[dict]:
    """
    Filter events before sending to Sentry.
    
    Args:
        event: Sentry event
        hint: Event hint
        
    Returns:
        Filtered event or None to drop
    """
    # Filter out certain exceptions
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        
        # Don't report certain expected exceptions
        if exc_type.__name__ in ["HTTPException", "ValidationError"]:
            return None
        
        # Don't report 404 errors
        if hasattr(exc_value, "status_code") and exc_value.status_code == 404:
            return None
    
    # Sanitize sensitive data
    event = sanitize_event(event)
    
    return event


def sanitize_event(event: dict) -> dict:
    """
    Sanitize sensitive data from event.
    
    Args:
        event: Sentry event
        
    Returns:
        Sanitized event
    """
    # List of keys to sanitize
    sensitive_keys = {
        "password", "token", "secret", "api_key", "apikey",
        "authorization", "auth", "cookie", "session",
        "credit_card", "ssn", "social_security",
    }
    
    def sanitize_value(key: str, value: Any) -> Any:
        """Sanitize a single value."""
        if isinstance(key, str):
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                return "[REDACTED]"
        
        if isinstance(value, dict):
            return {k: sanitize_value(k, v) for k, v in value.items()}
        
        if isinstance(value, list):
            return [sanitize_value("", item) for item in value]
        
        return value
    
    # Sanitize request data
    if "request" in event:
        request = event["request"]
        
        if "headers" in request:
            request["headers"] = sanitize_value("headers", request["headers"])
        
        if "data" in request:
            request["data"] = sanitize_value("data", request["data"])
        
        if "cookies" in request:
            request["cookies"] = "[REDACTED]"
    
    # Sanitize user data
    if "user" in event:
        user = event["user"]
        if "email" in user:
            user["email"] = "[REDACTED]"
    
    # Sanitize extra data
    if "extra" in event:
        event["extra"] = sanitize_value("extra", event["extra"])
    
    return event


def capture_exception(error: Exception, **context: Any) -> Optional[str]:
    """
    Capture an exception in Sentry.
    
    Args:
        error: Exception to capture
        **context: Additional context
        
    Returns:
        Event ID if captured
    """
    if not settings.SENTRY_ENABLED:
        return None
    
    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_extra(key, value)
        
        event_id = sentry_sdk.capture_exception(error)
        return event_id


def capture_message(message: str, level: str = "info", **context: Any) -> Optional[str]:
    """
    Capture a message in Sentry.
    
    Args:
        message: Message to capture
        level: Log level
        **context: Additional context
        
    Returns:
        Event ID if captured
    """
    if not settings.SENTRY_ENABLED:
        return None
    
    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_extra(key, value)
        
        event_id = sentry_sdk.capture_message(message, level=level)
        return event_id


def set_user_context(user_id: str, email: Optional[str] = None, **extra: Any) -> None:
    """
    Set user context for Sentry events.
    
    Args:
        user_id: User ID
        email: User email (will be hashed)
        **extra: Additional user data
    """
    if not settings.SENTRY_ENABLED:
        return
    
    import hashlib
    
    # Hash email for privacy
    email_hash = None
    if email:
        email_hash = hashlib.sha256(email.encode()).hexdigest()[:16]
    
    sentry_sdk.set_user({
        "id": user_id,
        "email_hash": email_hash,
        **extra,
    })


def clear_user_context() -> None:
    """Clear user context."""
    if settings.SENTRY_ENABLED:
        sentry_sdk.set_user(None)


def add_breadcrumb(
    message: str,
    category: Optional[str] = None,
    level: str = "info",
    data: Optional[dict] = None,
) -> None:
    """
    Add a breadcrumb for debugging context.
    
    Args:
        message: Breadcrumb message
        category: Breadcrumb category
        level: Log level
        data: Additional data
    """
    if not settings.SENTRY_ENABLED:
        return
    
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )
