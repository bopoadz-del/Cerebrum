"""
Base Stub Implementation

All service stubs inherit from this base class for consistent behavior.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class StubResponse:
    """Standard stub response wrapper."""
    success: bool = True
    data: Any = None
    message: str = ""
    status: str = "stubbed"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "status": self.status,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class StubError:
    """Standard stub error wrapper."""
    error: str
    code: str = "STUB_ERROR"
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": False,
            "error": self.error,
            "code": self.code,
            "details": self.details or {},
            "status": "error",
        }


class BaseStub(ABC):
    """
    Base class for all service stubs.
    
    Provides:
    - Consistent logging
    - Health check interface
    - Status reporting
    - Response formatting
    """
    
    # Override in subclasses
    service_name: str = "base"
    version: str = "1.0.0"
    
    def __init__(self):
        self.logger = logging.getLogger(f"stubs.{self.service_name}")
        self._call_count = 0
        self._last_called = None
    
    def _log_call(self, method: str, **kwargs):
        """Log stub method call."""
        self._call_count += 1
        self._last_called = datetime.utcnow().isoformat()
        self.logger.debug(f"[{self.service_name}.{method}] Stub call", extra=kwargs)
    
    def health_check(self) -> Dict[str, Any]:
        """Return stub health status."""
        return {
            "service": self.service_name,
            "status": "stubbed",
            "healthy": True,
            "version": self.version,
            "calls": self._call_count,
            "last_called": self._last_called,
        }
    
    def is_available(self) -> bool:
        """Stubs are always available."""
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed stub status."""
        return {
            "service": self.service_name,
            "mode": "stub",
            "available": True,
            "calls": self._call_count,
            "last_called": self._last_called,
            "version": self.version,
        }
    
    def _success_response(self, data: Any = None, message: str = "") -> StubResponse:
        """Create a success response."""
        return StubResponse(
            success=True,
            data=data,
            message=message or f"{self.service_name} stub response",
            status="stubbed",
        )
    
    def _error_response(self, error: str, code: str = "STUB_ERROR") -> StubError:
        """Create an error response."""
        return StubError(error=error, code=code)
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Return stub information. Override in subclasses."""
        pass
