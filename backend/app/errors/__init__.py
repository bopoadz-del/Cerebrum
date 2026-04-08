"""
Error handling module for user-friendly error messages.

This module provides centralized error handling with user-friendly messages
that replace technical details with clear, actionable guidance.
"""

from .errors import (
    ErrorCategory,
    UserFriendlyError,
    get_user_friendly_error,
    format_error_response,
    handle_errors,
    categorize_error,
    ERROR_MAPPINGS,
)

__all__ = [
    "ErrorCategory",
    "UserFriendlyError",
    "get_user_friendly_error",
    "format_error_response",
    "handle_errors",
    "categorize_error",
    "ERROR_MAPPINGS",
]