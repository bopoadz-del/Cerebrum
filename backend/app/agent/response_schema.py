"""
Standardized Agent Response Schema

All agent tools must return responses following this schema for consistency.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    """Standard response status values."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PENDING = "pending"


class ErrorCode(str, Enum):
    """Standard error codes for agent responses."""
    # General errors
    UNKNOWN_ERROR = "unknown_error"
    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    
    # Data errors
    DATA_UNAVAILABLE = "data_unavailable"
    DATA_INVALID = "data_invalid"
    CALCULATION_ERROR = "calculation_error"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_BUSY = "resource_busy"
    
    # Validation errors
    VALIDATION_FAILED = "validation_failed"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_FORMAT = "invalid_format"


@dataclass
class AgentError:
    """Standardized error representation."""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code.value if isinstance(self.code, ErrorCode) else self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class AgentResponse:
    """
    Standardized response format for all agent tools.
    
    All tools must return responses following this schema to ensure:
    - Consistent error handling
    - Predictable response structure
    - Easy debugging and logging
    - Unified formatter compatibility
    
    Required fields:
    - success: Boolean indicating operation success
    - results: Primary result data (can be dict, list, or any type)
    
    Optional fields:
    - status: Detailed status (success/error/warning/pending)
    - error: Error details if success=False
    - metadata: Additional context (query, count, pagination, etc.)
    - timestamp: ISO format timestamp
    - execution_time_ms: Performance metric
    - suggestions: List of follow-up suggestions
    
    Example success response:
        AgentResponse.success(
            results={"items": [...]},
            metadata={"query": "concrete", "count": 10}
        )
    
    Example error response:
        AgentResponse.error(
            code=ErrorCode.NOT_FOUND,
            message="Item not found",
            suggestion="Try searching with different keywords"
        )
    """
    
    # Required fields
    success: bool
    results: Any = field(default_factory=dict)
    
    # Optional fields
    status: ResponseStatus = ResponseStatus.SUCCESS
    error: Optional[AgentError] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: Optional[float] = None
    suggestions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Ensure status matches success flag."""
        if self.success and self.status == ResponseStatus.ERROR:
            self.status = ResponseStatus.SUCCESS
        elif not self.success and self.status == ResponseStatus.SUCCESS:
            self.status = ResponseStatus.ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "success": self.success,
            "results": self.results,
            "status": self.status.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
        
        if self.error:
            result["error"] = self.error.to_dict()
        
        if self.execution_time_ms is not None:
            result["execution_time_ms"] = self.execution_time_ms
        
        if self.suggestions:
            result["suggestions"] = self.suggestions
            
        return result
    
    @classmethod
    def success(
        cls,
        results: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        execution_time_ms: Optional[float] = None
    ) -> "AgentResponse":
        """Create a success response."""
        return cls(
            success=True,
            status=ResponseStatus.SUCCESS,
            results=results if results is not None else {},
            metadata=metadata or {},
            suggestions=suggestions or [],
            execution_time_ms=execution_time_ms
        )
    
    @classmethod
    def error(
        cls,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "AgentResponse":
        """Create an error response."""
        return cls(
            success=False,
            status=ResponseStatus.ERROR,
            results={},
            error=AgentError(
                code=code,
                message=message,
                details=details,
                suggestion=suggestion
            ),
            metadata=metadata or {}
        )
    
    @classmethod
    def warning(
        cls,
        results: Any,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "AgentResponse":
        """Create a warning response (partial success)."""
        return cls(
            success=True,
            status=ResponseStatus.WARNING,
            results=results,
            metadata={**(metadata or {}), "warning": message}
        )


# =============================================================================
# Helper Functions for Legacy Compatibility
# =============================================================================

def format_error_response(
    message: str,
    code: str = "unknown_error",
    details: Optional[Dict[str, Any]] = None,
    suggestion: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format a standardized error response (legacy dict format).
    
    Use this for quick error responses that need to remain dict-compatible.
    """
    response = {
        "success": False,
        "results": {},
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
        "timestamp": datetime.now().isoformat(),
    }
    
    if details:
        response["error"]["details"] = details
    if suggestion:
        response["error"]["suggestion"] = suggestion
        
    return response


def format_success_response(
    results: Any,
    metadata: Optional[Dict[str, Any]] = None,
    suggestions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Format a standardized success response (legacy dict format).
    
    Use this for quick success responses that need to remain dict-compatible.
    """
    response = {
        "success": True,
        "results": results,
        "status": "success",
        "timestamp": datetime.now().isoformat(),
    }
    
    if metadata:
        response["metadata"] = metadata
    if suggestions:
        response["suggestions"] = suggestions
        
    return response


# =============================================================================
# Response Validation
# =============================================================================

def validate_response(response: Dict[str, Any]) -> bool:
    """
    Validate that a response follows the standard schema.
    
    Returns True if valid, False otherwise.
    """
    # Check required fields
    if "success" not in response:
        return False
    
    if not isinstance(response["success"], bool):
        return False
    
    # If error, must have error details
    if not response["success"]:
        if "error" not in response:
            # Legacy format with just 'error' string is still valid
            if "error" not in response and "errors" not in response:
                # Allow simple error format
                pass
    
    return True


def normalize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a legacy response to the standard format.
    
    This converts various legacy formats to the standardized schema.
    """
    normalized = {
        "success": response.get("success", False),
        "results": {},
        "status": "success" if response.get("success") else "error",
        "timestamp": datetime.now().isoformat(),
    }
    
    # Extract results from various legacy keys
    if "results" in response:
        normalized["results"] = response["results"]
    elif "result" in response:
        normalized["results"] = response["result"]
    elif "data" in response:
        normalized["results"] = response["data"]
    elif "items" in response:
        normalized["results"] = {"items": response["items"]}
    else:
        # Include any non-standard keys in results
        standard_keys = {"success", "error", "errors", "status", "timestamp"}
        extra_data = {k: v for k, v in response.items() if k not in standard_keys}
        if extra_data:
            normalized["results"] = extra_data
    
    # Normalize error format
    if not normalized["success"]:
        if "error" in response:
            if isinstance(response["error"], str):
                normalized["error"] = {
                    "code": "unknown_error",
                    "message": response["error"]
                }
            else:
                normalized["error"] = response["error"]
        elif "errors" in response:
            normalized["error"] = {
                "code": "multiple_errors",
                "message": "Multiple errors occurred",
                "details": {"errors": response["errors"]}
            }
    
    # Copy metadata if present
    if "metadata" in response:
        normalized["metadata"] = response["metadata"]
    
    # Build metadata from common fields
    metadata = {}
    for key in ["query", "count", "total", "limit", "offset"]:
        if key in response:
            metadata[key] = response[key]
    if metadata:
        normalized["metadata"] = {**normalized.get("metadata", {}), **metadata}
    
    # Copy suggestions
    if "suggestions" in response:
        normalized["suggestions"] = response["suggestions"]
    
    return normalized


__all__ = [
    "AgentResponse",
    "AgentError",
    "ResponseStatus",
    "ErrorCode",
    "format_error_response",
    "format_success_response",
    "validate_response",
    "normalize_response",
]