"""
Retry Logic - Exponential Backoff with Jitter
Implements resilient retry mechanisms with configurable backoff strategies.
"""
import random
import time
import functools
from typing import Callable, Optional, Type, Tuple, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Backoff strategies for retries."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_WITH_JITTER = "exponential_with_jitter"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    # Retry limits
    max_retries: int = 3
    max_delay: float = 60.0
    
    # Backoff settings
    base_delay: float = 1.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_WITH_JITTER
    
    # Jitter settings
    jitter_min: float = 0.0
    jitter_max: float = 1.0
    
    # Exception handling
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
    retry_on_result: Optional[Callable[[Any], bool]] = None
    
    # Callbacks
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
    on_success: Optional[Callable[[Any, int], None]] = None
    on_failure: Optional[Callable[[Exception, int], None]] = None
    
    # Timing
    timeout: Optional[float] = None


class RetryHandler:
    """Handles retry logic with configurable backoff."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        strategy = self.config.backoff_strategy
        base = self.config.base_delay
        
        if strategy == BackoffStrategy.FIXED:
            delay = base
        
        elif strategy == BackoffStrategy.LINEAR:
            delay = base * attempt
        
        elif strategy == BackoffStrategy.EXPONENTIAL:
            delay = base * (2 ** (attempt - 1))
        
        elif strategy == BackoffStrategy.EXPONENTIAL_WITH_JITTER:
            exp_delay = base * (2 ** (attempt - 1))
            jitter = random.uniform(
                self.config.jitter_min,
                self.config.jitter_max
            )
            delay = exp_delay + jitter
        
        elif strategy == BackoffStrategy.FIBONACCI:
            delay = base * self._fibonacci(attempt)
        
        else:
            delay = base
        
        # Cap at max delay
        return min(delay, self.config.max_delay)
    
    def _fibonacci(self, n: int) -> int:
        """Calculate Fibonacci number."""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(2, n):
            a, b = b, a + b
        return b
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(1, self.config.max_retries + 2):
            try:
                result = func(*args, **kwargs)
                
                # Check if result should trigger retry
                if (self.config.retry_on_result and 
                    self.config.retry_on_result(result)):
                    if attempt <= self.config.max_retries:
                        delay = self.calculate_delay(attempt)
                        logger.debug(f"Retrying due to result, attempt {attempt}")
                        time.sleep(delay)
                        continue
                
                # Success
                if self.config.on_success:
                    self.config.on_success(result, attempt)
                
                return result
            
            except self.config.exceptions as e:
                last_exception = e
                
                if attempt <= self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    
                    logger.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if self.config.on_retry:
                        self.config.on_retry(e, attempt, delay)
                    
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_retries} retries exhausted")
                    
                    if self.config.on_failure:
                        self.config.on_failure(e, attempt)
                    
                    raise last_exception
        
        # Should not reach here
        raise last_exception if last_exception else Exception("Unexpected error")
    
    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with retry logic."""
        import asyncio
        
        last_exception = None
        
        for attempt in range(1, self.config.max_retries + 2):
            try:
                result = await func(*args, **kwargs)
                
                if (self.config.retry_on_result and 
                    self.config.retry_on_result(result)):
                    if attempt <= self.config.max_retries:
                        delay = self.calculate_delay(attempt)
                        await asyncio.sleep(delay)
                        continue
                
                if self.config.on_success:
                    await self._maybe_async(self.config.on_success, result, attempt)
                
                return result
            
            except self.config.exceptions as e:
                last_exception = e
                
                if attempt <= self.config.max_retries:
                    delay = self.calculate_delay(attempt)
                    
                    logger.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if self.config.on_retry:
                        await self._maybe_async(self.config.on_retry, e, attempt, delay)
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_retries} retries exhausted")
                    
                    if self.config.on_failure:
                        await self._maybe_async(self.config.on_failure, e, attempt)
                    
                    raise last_exception
        
        raise last_exception if last_exception else Exception("Unexpected error")
    
    async def _maybe_async(self, func: Callable, *args):
        """Call function, handling both sync and async."""
        import asyncio
        import inspect
        
        result = func(*args)
        if inspect.isawaitable(result):
            return await result
        return result


# Convenience retry decorators
def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_WITH_JITTER,
    jitter: bool = True
):
    """Decorator to add retry logic to a function."""
    def decorator(func: Callable) -> Callable:
        config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exceptions=exceptions,
            backoff_strategy=backoff_strategy
        )
        handler = RetryHandler(config)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return handler.execute(func, *args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await handler.execute_async(func, *args, **kwargs)
        
        # Return appropriate wrapper
        import asyncio
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def retry_with_fixed_delay(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Retry with fixed delay between attempts."""
    return retry(
        max_retries=max_retries,
        base_delay=delay,
        max_delay=delay,
        exceptions=exceptions,
        backoff_strategy=BackoffStrategy.FIXED
    )


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    jitter: bool = True
):
    """Retry with exponential backoff."""
    strategy = (BackoffStrategy.EXPONENTIAL_WITH_JITTER if jitter 
                else BackoffStrategy.EXPONENTIAL)
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exceptions=exceptions,
        backoff_strategy=strategy
    )


# Pre-configured retry settings for common scenarios
RETRY_PRESETS = {
    "database": RetryConfig(
        max_retries=5,
        base_delay=0.5,
        max_delay=30.0,
        exceptions=(ConnectionError, TimeoutError),
        backoff_strategy=BackoffStrategy.EXPONENTIAL_WITH_JITTER
    ),
    "external_api": RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        exceptions=(ConnectionError, TimeoutError),
        backoff_strategy=BackoffStrategy.EXPONENTIAL_WITH_JITTER
    ),
    "idempotent_operation": RetryConfig(
        max_retries=10,
        base_delay=0.1,
        max_delay=60.0,
        exceptions=(Exception,),
        backoff_strategy=BackoffStrategy.EXPONENTIAL_WITH_JITTER
    ),
    "network_operation": RetryConfig(
        max_retries=5,
        base_delay=0.5,
        max_delay=30.0,
        exceptions=(ConnectionError, TimeoutError),
        backoff_strategy=BackoffStrategy.EXPONENTIAL_WITH_JITTER
    ),
}


def get_retry_preset(name: str) -> RetryConfig:
    """Get a pre-configured retry preset."""
    return RETRY_PRESETS.get(name, RetryConfig())


# Example usage
if __name__ == "__main__":
    @retry(max_retries=3, base_delay=1.0)
    def unreliable_function():
        import random
        if random.random() < 0.7:
            raise ConnectionError("Network error")
        return "Success"
    
    # Test retry
    for i in range(5):
        try:
            result = unreliable_function()
            print(f"Attempt {i+1}: {result}")
        except Exception as e:
            print(f"Attempt {i+1}: Failed - {e}")
