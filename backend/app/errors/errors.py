"""
User-Friendly Error Handling for Cerebrum

This module provides centralized, user-friendly error messages
that replace technical details with clear, actionable guidance.
"""

import logging
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for user-friendly mapping."""
    NETWORK = auto()
    DATABASE = auto()
    AUTHENTICATION = auto()
    AUTHORIZATION = auto()
    VALIDATION = auto()
    NOT_FOUND = auto()
    RATE_LIMIT = auto()
    TIMEOUT = auto()
    SERVICE_UNAVAILABLE = auto()
    UNKNOWN = auto()
    FILE_ERROR = auto()
    CONFIGURATION = auto()
    EXTERNAL_SERVICE = auto()


@dataclass
class UserFriendlyError:
    """User-friendly error response."""
    category: ErrorCategory
    user_message: str
    suggestion: str
    action_buttons: list
    retry_allowed: bool
    log_level: str = "error"
    technical_detail: Optional[str] = None


# Centralized error message mappings
ERROR_MAPPINGS: Dict[str, Dict[str, Any]] = {
    # HTTP Status Codes
    "HTTP 400": {
        "category": ErrorCategory.VALIDATION,
        "user_message": "We couldn't process your request.",
        "suggestion": "Please check your input and try again. Make sure all required fields are filled correctly.",
        "retry_allowed": True,
    },
    "HTTP 401": {
        "category": ErrorCategory.AUTHENTICATION,
        "user_message": "You need to sign in to do that.",
        "suggestion": "Please sign in to your account and try again.",
        "retry_allowed": False,
        "action_buttons": [{"label": "Sign In", "action": "navigate:/login"}],
    },
    "HTTP 403": {
        "category": ErrorCategory.AUTHORIZATION,
        "user_message": "You don't have permission to do that.",
        "suggestion": "If you believe this is an error, please contact your administrator.",
        "retry_allowed": False,
    },
    "HTTP 404": {
        "category": ErrorCategory.NOT_FOUND,
        "user_message": "We couldn't find what you're looking for.",
        "suggestion": "The item may have been moved or deleted. Try searching for it or check the URL.",
        "retry_allowed": True,
        "action_buttons": [{"label": "Go Home", "action": "navigate:/"}],
    },
    "HTTP 429": {
        "category": ErrorCategory.RATE_LIMIT,
        "user_message": "You've made too many requests. Please slow down.",
        "suggestion": "Wait a moment and try again. If this keeps happening, contact support.",
        "retry_allowed": True,
    },
    "HTTP 500": {
        "category": ErrorCategory.SERVICE_UNAVAILABLE,
        "user_message": "Something went wrong on our end.",
        "suggestion": "We're working on fixing this. Please try again in a few moments.",
        "retry_allowed": True,
    },
    "HTTP 502": {
        "category": ErrorCategory.SERVICE_UNAVAILABLE,
        "user_message": "We're experiencing temporary issues.",
        "suggestion": "Our servers are having trouble connecting. Please try again shortly.",
        "retry_allowed": True,
    },
    "HTTP 503": {
        "category": ErrorCategory.SERVICE_UNAVAILABLE,
        "user_message": "Service temporarily unavailable.",
        "suggestion": "We're doing some maintenance or experiencing high traffic. Please try again soon.",
        "retry_allowed": True,
    },
    "HTTP 504": {
        "category": ErrorCategory.TIMEOUT,
        "user_message": "The request took too long to complete.",
        "suggestion": "This might be due to high traffic. Please try again in a moment.",
        "retry_allowed": True,
    },
    
    # Network errors
    "connection refused": {
        "category": ErrorCategory.NETWORK,
        "user_message": "Unable to connect to the service.",
        "suggestion": "Please check your internet connection and try again.",
        "retry_allowed": True,
    },
    "network error": {
        "category": ErrorCategory.NETWORK,
        "user_message": "Connection issue detected.",
        "suggestion": "Please check your internet connection and try again.",
        "retry_allowed": True,
    },
    "timeout": {
        "category": ErrorCategory.TIMEOUT,
        "user_message": "The request timed out.",
        "suggestion": "This might be due to slow internet or high traffic. Please try again.",
        "retry_allowed": True,
    },
    "connection reset": {
        "category": ErrorCategory.NETWORK,
        "user_message": "Connection was interrupted.",
        "suggestion": "Your connection was lost. Please check your internet and try again.",
        "retry_allowed": True,
    },
    "dns resolution": {
        "category": ErrorCategory.NETWORK,
        "user_message": "Could not reach the server.",
        "suggestion": "There may be a network issue. Please check your connection and try again.",
        "retry_allowed": True,
    },
    
    # Database errors
    "database": {
        "category": ErrorCategory.DATABASE,
        "user_message": "Service temporarily unavailable.",
        "suggestion": "We're having trouble with our database. Please try again in a few moments.",
        "retry_allowed": True,
    },
    "sql": {
        "category": ErrorCategory.DATABASE,
        "user_message": "Service temporarily unavailable.",
        "suggestion": "We're experiencing a data issue. Please try again shortly.",
        "retry_allowed": True,
    },
    "deadlock": {
        "category": ErrorCategory.DATABASE,
        "user_message": "The system is busy. Please try again.",
        "suggestion": "Too many people are using this feature right now. Wait a moment and retry.",
        "retry_allowed": True,
    },
    "connection pool": {
        "category": ErrorCategory.DATABASE,
        "user_message": "Service temporarily unavailable.",
        "suggestion": "We're at capacity right now. Please try again in a moment.",
        "retry_allowed": True,
    },
    
    # File errors
    "file not found": {
        "category": ErrorCategory.FILE_ERROR,
        "user_message": "We couldn't find that file.",
        "suggestion": "The file may have been moved or deleted. Please check the name and try again.",
        "retry_allowed": True,
    },
    "permission denied": {
        "category": ErrorCategory.FILE_ERROR,
        "user_message": "We can't access that file.",
        "suggestion": "You may not have permission to access this file. Check your permissions and try again.",
        "retry_allowed": False,
    },
    "disk full": {
        "category": ErrorCategory.FILE_ERROR,
        "user_message": "Not enough storage space.",
        "suggestion": "Please free up some space and try again.",
        "retry_allowed": True,
    },
    
    # Validation errors
    "invalid": {
        "category": ErrorCategory.VALIDATION,
        "user_message": "That doesn't look right.",
        "suggestion": "Please check your input and make sure it's in the correct format.",
        "retry_allowed": True,
    },
    "required": {
        "category": ErrorCategory.VALIDATION,
        "user_message": "Please fill in all required fields.",
        "suggestion": "Some information is missing. Please complete all required fields and try again.",
        "retry_allowed": True,
    },
    "already exists": {
        "category": ErrorCategory.VALIDATION,
        "user_message": "That already exists.",
        "suggestion": "Try using a different name or check if you meant to update the existing item.",
        "retry_allowed": True,
    },
    
    # External service errors
    "external service": {
        "category": ErrorCategory.EXTERNAL_SERVICE,
        "user_message": "A connected service is having issues.",
        "suggestion": "One of our partners is experiencing problems. Please try again shortly.",
        "retry_allowed": True,
    },
    "api error": {
        "category": ErrorCategory.EXTERNAL_SERVICE,
        "user_message": "We're having trouble with an external service.",
        "suggestion": "A service we rely on is not responding. Please try again in a few moments.",
        "retry_allowed": True,
    },
    
    # Economics/cost estimation errors
    "need building_type": {
        "category": ErrorCategory.VALIDATION,
        "user_message": "I need more details to calculate costs.",
        "suggestion": "Try: 'Estimate 5000 sq ft office building' or 'Cost of concrete per cubic yard'",
        "retry_allowed": True,
    },
    "need item_id": {
        "category": ErrorCategory.VALIDATION,
        "user_message": "I need more details to calculate costs.",
        "suggestion": "Try: 'Estimate 5000 sq ft office building' or 'Cost of concrete per cubic yard'",
        "retry_allowed": True,
    },
    
    # Unknown/catch-all
    "unknown": {
        "category": ErrorCategory.UNKNOWN,
        "user_message": "Something unexpected happened.",
        "suggestion": "Please try again. If this keeps happening, contact support.",
        "retry_allowed": True,
        "action_buttons": [{"label": "Contact Support", "action": "navigate:/support"}],
    },
}


def categorize_error(error_message: str, error_type: Optional[str] = None) -> ErrorCategory:
    """Categorize an error based on its message."""
    error_lower = error_message.lower()
    
    # Check for specific patterns
    if any(code in error_lower for code in ["401", "unauthorized", "auth", "login", "signin"]):
        return ErrorCategory.AUTHENTICATION
    elif any(code in error_lower for code in ["403", "forbidden", "permission", "access denied"]):
        return ErrorCategory.AUTHORIZATION
    elif any(code in error_lower for code in ["404", "not found", "doesn't exist", "does not exist"]):
        return ErrorCategory.NOT_FOUND
    elif any(code in error_lower for code in ["429", "rate limit", "too many"]):
        return ErrorCategory.RATE_LIMIT
    elif any(code in error_lower for code in ["500", "502", "503", "service unavailable"]):
        return ErrorCategory.SERVICE_UNAVAILABLE
    elif any(code in error_lower for code in ["504", "timeout", "timed out"]):
        return ErrorCategory.TIMEOUT
    elif any(code in error_lower for code in ["network", "connection", "refused", "reset", "dns"]):
        return ErrorCategory.NETWORK
    elif any(code in error_lower for code in ["database", "sql", "db ", "postgres", "mysql", "sqlite"]):
        return ErrorCategory.DATABASE
    elif any(code in error_lower for code in ["file", "disk", "storage", "path"]):
        return ErrorCategory.FILE_ERROR
    elif any(code in error_lower for code in ["invalid", "validation", "required", "missing", "format"]):
        return ErrorCategory.VALIDATION
    elif any(code in error_lower for code in ["external", "api", "service", "third-party"]):
        return ErrorCategory.EXTERNAL_SERVICE
    
    return ErrorCategory.UNKNOWN


def get_user_friendly_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> UserFriendlyError:
    """
    Convert a technical error into a user-friendly error.
    
    Args:
        error: The original exception
        context: Additional context (endpoint, operation, user_id, etc.)
        
    Returns:
        UserFriendlyError with user-friendly message and suggestions
    """
    error_message = str(error)
    error_type = type(error).__name__
    error_lower = error_message.lower()
    context = context or {}
    
    # Log the technical error for debugging
    logger.error(
        f"Error occurred: {error_type}: {error_message}",
        extra={"context": context, "error_type": error_type}
    )
    
    # Try to find a matching error pattern
    for pattern, mapping in ERROR_MAPPINGS.items():
        if pattern.lower() in error_lower:
            return UserFriendlyError(
                category=mapping.get("category", ErrorCategory.UNKNOWN),
                user_message=mapping["user_message"],
                suggestion=mapping["suggestion"],
                action_buttons=mapping.get("action_buttons", []),
                retry_allowed=mapping.get("retry_allowed", True),
                technical_detail=error_message if context.get("debug_mode") else None,
            )
    
    # Handle common Python exception types
    if isinstance(error, ValueError):
        return UserFriendlyError(
            category=ErrorCategory.VALIDATION,
            user_message="That value doesn't look right.",
            suggestion="Please check your input and try again with the correct format.",
            action_buttons=[],
            retry_allowed=True,
        )
    elif isinstance(error, KeyError):
        return UserFriendlyError(
            category=ErrorCategory.NOT_FOUND,
            user_message="We couldn't find what you're looking for.",
            suggestion="The item may have been removed or the reference is incorrect.",
            action_buttons=[],
            retry_allowed=True,
        )
    elif isinstance(error, FileNotFoundError):
        return UserFriendlyError(
            category=ErrorCategory.FILE_ERROR,
            user_message="We couldn't find that file.",
            suggestion="Please check the file name and location, then try again.",
            action_buttons=[],
            retry_allowed=True,
        )
    elif isinstance(error, PermissionError):
        return UserFriendlyError(
            category=ErrorCategory.AUTHORIZATION,
            user_message="You don't have permission to do that.",
            suggestion="Check your permissions or contact an administrator for access.",
            action_buttons=[],
            retry_allowed=False,
        )
    elif isinstance(error, ConnectionError):
        return UserFriendlyError(
            category=ErrorCategory.NETWORK,
            user_message="Connection issue. Check your internet.",
            suggestion="Please check your network connection and try again.",
            action_buttons=[],
            retry_allowed=True,
        )
    elif isinstance(error, TimeoutError):
        return UserFriendlyError(
            category=ErrorCategory.TIMEOUT,
            user_message="The request took too long.",
            suggestion="This might be due to high traffic. Please try again in a moment.",
            action_buttons=[],
            retry_allowed=True,
        )
    
    # Default unknown error
    return UserFriendlyError(
        category=ErrorCategory.UNKNOWN,
        user_message="Something unexpected happened. Please try again.",
        suggestion="If this keeps happening, please contact support with details of what you were doing.",
        action_buttons=[
            {"label": "Try Again", "action": "retry"},
            {"label": "Contact Support", "action": "navigate:/support"},
        ],
        retry_allowed=True,
        technical_detail=error_message if context.get("debug_mode") else None,
    )


def format_error_response(
    error: Exception,
    operation: Optional[str] = None,
    include_retry: bool = True,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format an error as a standardized JSON response.
    
    Args:
        error: The original exception
        operation: Description of what was being attempted
        include_retry: Whether to include retry button
        context: Additional context
        
    Returns:
        Standardized error response dictionary
    """
    friendly = get_user_friendly_error(error, context)
    
    response = {
        "success": False,
        "error": {
            "message": friendly.user_message,
            "suggestion": friendly.suggestion,
            "category": friendly.category.name.lower(),
            "retry_allowed": friendly.retry_allowed and include_retry,
        }
    }
    
    if operation:
        response["error"]["operation"] = operation
    
    # Add action buttons
    if friendly.action_buttons:
        response["error"]["actions"] = friendly.action_buttons
    elif include_retry and friendly.retry_allowed:
        response["error"]["actions"] = [{"label": "Try Again", "action": "retry"}]
    
    # Include technical details only in debug mode
    if context and context.get("debug_mode"):
        response["error"]["technical_detail"] = str(error)
        response["error"]["error_type"] = type(error).__name__
    
    return response


# Decorator for automatic error handling
def handle_errors(operation_name: Optional[str] = None, include_retry: bool = True):
    """
    Decorator to automatically convert exceptions to user-friendly errors.
    
    Usage:
        @handle_errors(operation_name="creating project")
        async def create_project(data: ProjectCreate):
            # ... code that might raise exceptions
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Don't re-wrap HTTPExceptions that already have user-friendly messages
                from fastapi import HTTPException
                if isinstance(e, HTTPException):
                    # Check if it already has a user-friendly format
                    if isinstance(e.detail, dict) and "message" in e.detail:
                        raise
                
                context = {
                    "operation": operation_name or func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs),
                }
                
                friendly = get_user_friendly_error(e, context)
                
                raise HTTPException(
                    status_code=_get_http_status(friendly.category),
                    detail=format_error_response(
                        e, 
                        operation=operation_name,
                        include_retry=include_retry,
                        context=context
                    )["error"]
                )
        
        return wrapper
    return decorator


def _get_http_status(category: ErrorCategory) -> int:
    """Map error category to HTTP status code."""
    mapping = {
        ErrorCategory.VALIDATION: 400,
        ErrorCategory.AUTHENTICATION: 401,
        ErrorCategory.AUTHORIZATION: 403,
        ErrorCategory.NOT_FOUND: 404,
        ErrorCategory.RATE_LIMIT: 429,
        ErrorCategory.TIMEOUT: 504,
        ErrorCategory.SERVICE_UNAVAILABLE: 503,
        ErrorCategory.DATABASE: 503,
        ErrorCategory.NETWORK: 503,
        ErrorCategory.EXTERNAL_SERVICE: 502,
    }
    return mapping.get(category, 500)


# Legacy compatibility aliases
get_friendly_error = get_user_friendly_error
format_friendly_error = format_error_response