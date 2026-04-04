"""
Circuit Breaker - pybreaker Implementation
Implements circuit breaker pattern for resilient service calls.
"""
from typing import Optional, Callable, Any, Type, List
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps
import time
import threading
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = auto()      # Normal operation
    OPEN = auto()        # Failing, reject calls
    HALF_OPEN = auto()   # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    
    # Failure threshold
    fail_max: int = 5
    
    # Recovery timeout (seconds)
    reset_timeout: float = 60.0
    
    # Half-open test calls
    expected_exception: Type[Exception] = Exception
    exclude_exceptions: Optional[List[Type[Exception]]] = None
    
    # Monitoring
    name: str = "circuit_breaker"
    
    def __post_init__(self):
        if self.exclude_exceptions is None:
            self.exclude_exceptions = []


class CircuitBreaker:
    """Circuit breaker implementation."""
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.RLock()
        
        # Metrics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejections = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        with self._lock:
            return self._failure_count
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection."""
        with self._lock:
            self._total_calls += 1
            
            # Check if circuit is open
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info(f"Circuit {self.config.name} entering HALF_OPEN state")
                else:
                    self._total_rejections += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.config.name} is OPEN"
                    )
        
        # Execute the call
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure(e)
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Async call with circuit breaker protection."""
        import asyncio
        
        with self._lock:
            self._total_calls += 1
            
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                    logger.info(f"Circuit {self.config.name} entering HALF_OPEN state")
                else:
                    self._total_rejections += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.config.name} is OPEN"
                    )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.reset_timeout
    
    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self._total_successes += 1
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                
                # If enough successes, close the circuit
                if self._success_count >= self.config.fail_max:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit {self.config.name} CLOSED (recovered)")
            
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0
    
    def _on_failure(self, exception: Exception):
        """Handle failed call."""
        # Check if exception should be excluded
        for excluded in self.config.exclude_exceptions:
            if isinstance(exception, excluded):
                raise exception
        
        # Check if exception is expected
        if not isinstance(exception, self.config.expected_exception):
            raise exception
        
        with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Failed in half-open, go back to open
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit {self.config.name} OPEN (failed in half-open)"
                )
            
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.fail_max:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit {self.config.name} OPEN ({self._failure_count} failures)"
                    )
    
    def get_metrics(self) -> dict:
        """Get circuit breaker metrics."""
        with self._lock:
            return {
                "name": self.config.name,
                "state": self._state.name,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "total_calls": self._total_calls,
                "total_failures": self._total_failures,
                "total_successes": self._total_successes,
                "total_rejections": self._total_rejections,
                "last_failure_time": self._last_failure_time,
                "failure_rate": (
                    self._total_failures / self._total_calls * 100
                    if self._total_calls > 0 else 0
                )
            }
    
    def reset(self):
        """Manually reset circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit {self.config.name} manually reset to CLOSED")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Circuit breaker registry
_circuit_breakers: dict = {}


def get_circuit_breaker(name: str, 
                        config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create circuit breaker."""
    if name not in _circuit_breakers:
        cfg = config or CircuitBreakerConfig(name=name)
        _circuit_breakers[name] = CircuitBreaker(cfg)
    return _circuit_breakers[name]


# Decorator for circuit breaker
def circuit_breaker(name: str, fail_max: int = 5, reset_timeout: float = 60.0):
    """Decorator to add circuit breaker to function."""
    def decorator(func: Callable) -> Callable:
        config = CircuitBreakerConfig(
            name=name,
            fail_max=fail_max,
            reset_timeout=reset_timeout
        )
        breaker = get_circuit_breaker(name, config)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)
        
        # Attach circuit breaker for manual control
        wrapper.circuit_breaker = breaker
        async_wrapper.circuit_breaker = breaker
        
        # Return appropriate wrapper
        import asyncio
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


# Pre-configured circuit breakers for common services
EXTERNAL_SERVICE_BREAKERS = {
    "email_service": CircuitBreakerConfig(
        name="email_service",
        fail_max=3,
        reset_timeout=300.0  # 5 minutes
    ),
    "payment_gateway": CircuitBreakerConfig(
        name="payment_gateway",
        fail_max=2,
        reset_timeout=60.0
    ),
    "external_api": CircuitBreakerConfig(
        name="external_api",
        fail_max=5,
        reset_timeout=120.0
    ),
    "database": CircuitBreakerConfig(
        name="database",
        fail_max=10,
        reset_timeout=30.0
    ),
    "redis": CircuitBreakerConfig(
        name="redis",
        fail_max=5,
        reset_timeout=30.0
    ),
}


# Example usage
if __name__ == "__main__":
    # Create circuit breaker
    breaker = CircuitBreaker(CircuitBreakerConfig(
        name="example_service",
        fail_max=3,
        reset_timeout=10.0
    ))
    
    # Function to protect
    def unreliable_service():
        import random
        if random.random() < 0.7:
            raise Exception("Service failed")
        return "Success"
    
    # Call with circuit breaker
    for i in range(10):
        try:
            result = breaker.call(unreliable_service)
            print(f"Call {i+1}: {result}")
        except CircuitBreakerOpenError:
            print(f"Call {i+1}: Circuit is OPEN - request rejected")
        except Exception as e:
            print(f"Call {i+1}: {e}")
        
        time.sleep(1)
