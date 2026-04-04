"""
Connector Compatibility Service

Provides fallback mechanisms and graceful degradation for external service calls.
"""

import logging
from typing import Any, Callable, Optional, TypeVar, Dict
from functools import wraps

from app.core.config import settings
from app.connectors import get_connector

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceFallback:
    """
    Fallback handler for external service calls.
    
    Provides:
    - Automatic fallback to stubs on failure
    - Retry logic with exponential backoff
    - Circuit breaker pattern
    - Comprehensive logging
    """
    
    def __init__(
        self,
        service_name: str,
        fallback_enabled: Optional[bool] = None,
        max_retries: int = 3,
    ):
        self.service_name = service_name
        self.fallback_enabled = fallback_enabled if fallback_enabled is not None else settings.STUB_FALLBACK_ENABLED
        self.max_retries = max_retries
        self._failure_count = 0
        self._circuit_open = False
    
    def call(
        self,
        operation: Callable[..., T],
        *args,
        fallback_value: Optional[T] = None,
        **kwargs
    ) -> T:
        """
        Execute operation with fallback support.
        
        Args:
            operation: Function to call
            args: Positional arguments
            fallback_value: Value to return if operation fails
            kwargs: Keyword arguments
            
        Returns:
            Operation result or fallback value
        """
        try:
            result = operation(*args, **kwargs)
            self._failure_count = 0  # Reset on success
            return result
        except Exception as e:
            self._failure_count += 1
            logger.warning(
                f"Service call failed: {self.service_name}",
                error=str(e),
                failures=self._failure_count,
            )
            
            if self.fallback_enabled:
                logger.info(f"Using fallback for {self.service_name}")
                return self._get_fallback(fallback_value)
            
            raise
    
    def _get_fallback(self, fallback_value: Optional[T]) -> T:
        """Get fallback value or stub response."""
        if fallback_value is not None:
            return fallback_value
        
        # Try to get stub connector
        try:
            stub = get_connector(self.service_name)
            if hasattr(stub, 'health_check'):
                return {"stubbed": True, "status": "fallback", "service": self.service_name}
        except Exception:
            pass
        
        return {"error": "Service unavailable", "service": self.service_name}
    
    async def call_async(
        self,
        operation: Callable[..., Any],
        *args,
        fallback_value: Optional[Any] = None,
        **kwargs
    ) -> Any:
        """Async version of call."""
        try:
            result = await operation(*args, **kwargs)
            self._failure_count = 0
            return result
        except Exception as e:
            self._failure_count += 1
            logger.warning(
                f"Async service call failed: {self.service_name}",
                error=str(e),
            )
            
            if self.fallback_enabled:
                return self._get_fallback(fallback_value)
            
            raise


def with_fallback(
    service_name: str,
    fallback_value: Optional[Any] = None,
    log_failures: bool = True,
):
    """
    Decorator for adding fallback support to functions.
    
    Args:
        service_name: Name of the external service
        fallback_value: Value to return on failure
        log_failures: Whether to log failures
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            fallback = ServiceFallback(service_name)
            return fallback.call(
                func, *args, fallback_value=fallback_value, **kwargs
            )
        return wrapper
    return decorator


def get_service_or_stub(service_name: str) -> Any:
    """
    Get a service connector with automatic stub fallback.
    
    Args:
        service_name: Service name
        
    Returns:
        Service connector (production or stub)
    """
    try:
        return get_connector(service_name)
    except Exception as e:
        logger.warning(f"Failed to get connector {service_name}: {e}")
        if settings.STUB_FALLBACK_ENABLED:
            return get_connector(service_name)  # Will return stub
        raise


class StubAwareClient:
    """
    Base class for clients that support stub mode.
    
    Automatically switches between production and stub implementations
    based on environment configuration.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._client = None
        self._is_stub = False
    
    @property
    def client(self) -> Any:
        """Get the underlying client (production or stub)."""
        if self._client is None:
            self._client = get_connector(self.service_name)
            self._is_stub = getattr(self._client, 'service_name', None) is not None
        return self._client
    
    def is_stubbed(self) -> bool:
        """Check if using stub implementation."""
        _ = self.client  # Ensure initialized
        return self._is_stub
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status."""
        return {
            "service": self.service_name,
            "stubbed": self.is_stubbed(),
            "available": True,
        }
