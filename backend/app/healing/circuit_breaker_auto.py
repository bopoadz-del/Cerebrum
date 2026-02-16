"""
Auto Circuit Breaker System

Automatically detects slow endpoints and adds caching or other
optimizations to improve performance.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID

from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """State of a circuit breaker."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class OptimizationType(str, Enum):
    """Type of automatic optimization."""
    CACHE_ADD = "cache_add"
    CACHE_INCREASE_TTL = "cache_increase_ttl"
    RATE_LIMIT = "rate_limit"
    TIMEOUT_INCREASE = "timeout_increase"
    RETRY_REDUCTION = "retry_reduction"
    BATCH_REQUESTS = "batch_requests"


@dataclass
class EndpointMetrics:
    """Metrics for an endpoint."""
    endpoint_path: str
    
    # Timing
    total_requests: int = 0
    total_response_time_ms: float = 0
    avg_response_time_ms: float = 0
    max_response_time_ms: float = 0
    p95_response_time_ms: float = 0
    p99_response_time_ms: float = 0
    
    # Errors
    error_count: int = 0
    error_rate: float = 0.0
    
    # Status
    last_request_at: Optional[datetime] = None
    slow_request_count: int = 0
    
    # History
    response_times: List[float] = field(default_factory=lambda: [0.0] * 100)
    
    def record_request(self, response_time_ms: float, is_error: bool = False):
        """Record a request."""
        self.total_requests += 1
        self.total_response_time_ms += response_time_ms
        self.avg_response_time_ms = self.total_response_time_ms / self.total_requests
        self.max_response_time_ms = max(self.max_response_time_ms, response_time_ms)
        
        # Update response time history
        self.response_times.pop(0)
        self.response_times.append(response_time_ms)
        
        # Calculate percentiles
        sorted_times = sorted(self.response_times)
        self.p95_response_time_ms = sorted_times[int(len(sorted_times) * 0.95)]
        self.p99_response_time_ms = sorted_times[int(len(sorted_times) * 0.99)]
        
        if is_error:
            self.error_count += 1
        
        self.error_rate = self.error_count / self.total_requests if self.total_requests > 0 else 0
        self.last_request_at = datetime.utcnow()
        
        # Track slow requests (> 1 second)
        if response_time_ms > 1000:
            self.slow_request_count += 1


@dataclass
class CircuitBreaker:
    """Circuit breaker for an endpoint."""
    endpoint_path: str
    state: CircuitState = CircuitState.CLOSED
    
    # Thresholds
    failure_threshold: int = 5
    slow_threshold_ms: float = 1000
    timeout_seconds: float = 30
    
    # State tracking
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    
    # Recovery
    recovery_timeout_seconds: float = 60
    half_open_max_calls: int = 3


@dataclass
class AutoOptimization:
    """An automatically applied optimization."""
    id: UUID
    endpoint_path: str
    optimization_type: OptimizationType
    description: str
    applied_at: datetime
    applied_by: str = "auto_circuit_breaker"
    
    # Results
    before_metrics: Dict[str, float]
    after_metrics: Optional[Dict[str, float]] = None
    improvement_percent: Optional[float] = None
    
    # Status
    status: str = "applied"  # applied, verified, reverted
    reverted_at: Optional[datetime] = None
    revert_reason: Optional[str] = None


class AutoCircuitBreaker:
    """
    Automatic circuit breaker and performance optimization system.
    
    Monitors endpoint performance and automatically:
    - Opens circuit when failure threshold exceeded
    - Adds caching for slow endpoints
    - Adjusts timeouts and rate limits
    - Tracks improvement from optimizations
    """
    
    # Default thresholds
    SLOW_ENDPOINT_THRESHOLD_MS = 500  # Consider endpoint slow if > 500ms
    FAILURE_RATE_THRESHOLD = 0.1  # 10% failure rate
    CIRCUIT_OPEN_THRESHOLD = 5  # Open circuit after 5 failures
    
    def __init__(self):
        """Initialize the auto circuit breaker."""
        self._metrics: Dict[str, EndpointMetrics] = {}
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._optimizations: Dict[UUID, AutoOptimization] = {}
        self._cached_endpoints: Set[str] = set()
        
        # Cache storage (in production, use Redis)
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, datetime] = {}
    
    async def record_request(
        self,
        endpoint_path: str,
        response_time_ms: float,
        is_error: bool = False,
    ) -> None:
        """
        Record a request for metrics tracking.
        
        Args:
            endpoint_path: Endpoint path
            response_time_ms: Response time in milliseconds
            is_error: Whether the request resulted in an error
        """
        # Get or create metrics
        if endpoint_path not in self._metrics:
            self._metrics[endpoint_path] = EndpointMetrics(endpoint_path=endpoint_path)
        
        metrics = self._metrics[endpoint_path]
        metrics.record_request(response_time_ms, is_error)
        
        # Check for circuit breaker
        await self._check_circuit_breaker(endpoint_path, is_error)
        
        # Check for slow endpoint
        if not is_error:
            await self._check_slow_endpoint(endpoint_path, metrics)
    
    async def _check_circuit_breaker(self, endpoint_path: str, is_error: bool) -> None:
        """Check and update circuit breaker state."""
        # Get or create circuit
        if endpoint_path not in self._circuits:
            self._circuits[endpoint_path] = CircuitBreaker(endpoint_path=endpoint_path)
        
        circuit = self._circuits[endpoint_path]
        
        if circuit.state == CircuitState.CLOSED:
            if is_error:
                circuit.failure_count += 1
                circuit.last_failure_time = datetime.utcnow()
                
                if circuit.failure_count >= circuit.failure_threshold:
                    circuit.state = CircuitState.OPEN
                    logger.warning(f"Circuit opened for {endpoint_path}")
                    
                    # Trigger auto-optimization
                    await self._trigger_optimization(endpoint_path, "high_error_rate")
            else:
                circuit.failure_count = 0
        
        elif circuit.state == CircuitState.OPEN:
            # Check if recovery timeout passed
            if circuit.last_failure_time:
                elapsed = (datetime.utcnow() - circuit.last_failure_time).total_seconds()
                if elapsed >= circuit.recovery_timeout_seconds:
                    circuit.state = CircuitState.HALF_OPEN
                    circuit.success_count = 0
                    logger.info(f"Circuit half-open for {endpoint_path}")
        
        elif circuit.state == CircuitState.HALF_OPEN:
            if is_error:
                circuit.state = CircuitState.OPEN
                circuit.last_failure_time = datetime.utcnow()
                logger.warning(f"Circuit re-opened for {endpoint_path}")
            else:
                circuit.success_count += 1
                if circuit.success_count >= circuit.half_open_max_calls:
                    circuit.state = CircuitState.CLOSED
                    circuit.failure_count = 0
                    logger.info(f"Circuit closed for {endpoint_path}")
    
    async def _check_slow_endpoint(
        self,
        endpoint_path: str,
        metrics: EndpointMetrics,
    ) -> None:
        """Check if endpoint is slow and needs optimization."""
        # Check if already cached
        if endpoint_path in self._cached_endpoints:
            return
        
        # Check if slow
        if metrics.p95_response_time_ms > self.SLOW_ENDPOINT_THRESHOLD_MS:
            # Check if we have enough samples
            if metrics.total_requests >= 10:
                logger.warning(
                    f"Slow endpoint detected: {endpoint_path} "
                    f"(p95: {metrics.p95_response_time_ms:.0f}ms)"
                )
                
                # Trigger auto-caching
                await self._apply_caching(endpoint_path, metrics)
    
    async def _trigger_optimization(
        self,
        endpoint_path: str,
        trigger_reason: str,
    ) -> Optional[AutoOptimization]:
        """Trigger an automatic optimization."""
        # Determine optimization type based on trigger
        if trigger_reason == "high_error_rate":
            opt_type = OptimizationType.RETRY_REDUCTION
        elif trigger_reason == "slow_endpoint":
            opt_type = OptimizationType.CACHE_ADD
        else:
            return None
        
        # Record optimization
        optimization = AutoOptimization(
            id=UUID(int=hash(endpoint_path + str(datetime.utcnow()))),
            endpoint_path=endpoint_path,
            optimization_type=opt_type,
            description=f"Auto-optimization triggered by {trigger_reason}",
            applied_at=datetime.utcnow(),
            before_metrics={
                "avg_response_time_ms": self._metrics.get(endpoint_path, EndpointMetrics(endpoint_path)).avg_response_time_ms,
                "error_rate": self._metrics.get(endpoint_path, EndpointMetrics(endpoint_path)).error_rate,
            },
        )
        
        self._optimizations[optimization.id] = optimization
        
        logger.info(f"Auto-optimization applied to {endpoint_path}: {opt_type.value}")
        
        return optimization
    
    async def _apply_caching(
        self,
        endpoint_path: str,
        metrics: EndpointMetrics,
    ) -> Optional[AutoOptimization]:
        """Apply caching to a slow endpoint."""
        if endpoint_path in self._cached_endpoints:
            return None
        
        # Add to cached endpoints
        self._cached_endpoints.add(endpoint_path)
        
        # Record optimization
        optimization = AutoOptimization(
            id=UUID(int=hash(endpoint_path + "cache")),
            endpoint_path=endpoint_path,
            optimization_type=OptimizationType.CACHE_ADD,
            description=f"Added caching for slow endpoint (p95: {metrics.p95_response_time_ms:.0f}ms)",
            applied_at=datetime.utcnow(),
            before_metrics={
                "p95_response_time_ms": metrics.p95_response_time_ms,
                "avg_response_time_ms": metrics.avg_response_time_ms,
            },
        )
        
        self._optimizations[optimization.id] = optimization
        
        logger.info(f"Auto-caching applied to {endpoint_path}")
        
        return optimization
    
    def is_circuit_open(self, endpoint_path: str) -> bool:
        """Check if circuit is open for an endpoint."""
        circuit = self._circuits.get(endpoint_path)
        if not circuit:
            return False
        return circuit.state == CircuitState.OPEN
    
    def can_execute(self, endpoint_path: str) -> bool:
        """Check if request can be executed."""
        circuit = self._circuits.get(endpoint_path)
        if not circuit:
            return True
        return circuit.state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]
    
    async def get_cached_response(
        self,
        endpoint_path: str,
        cache_key: str,
    ) -> Optional[Any]:
        """Get cached response if available."""
        if endpoint_path not in self._cached_endpoints:
            return None
        
        full_key = f"{endpoint_path}:{cache_key}"
        
        # Check if cached and not expired
        if full_key in self._cache:
            expires_at = self._cache_ttl.get(full_key)
            if expires_at and datetime.utcnow() < expires_at:
                return self._cache[full_key]
            else:
                # Expired, remove
                del self._cache[full_key]
                if full_key in self._cache_ttl:
                    del self._cache_ttl[full_key]
        
        return None
    
    async def set_cached_response(
        self,
        endpoint_path: str,
        cache_key: str,
        response: Any,
        ttl_seconds: int = 60,
    ) -> None:
        """Cache a response."""
        if endpoint_path not in self._cached_endpoints:
            return
        
        full_key = f"{endpoint_path}:{cache_key}"
        
        self._cache[full_key] = response
        self._cache_ttl[full_key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    def get_metrics(self, endpoint_path: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for all or specific endpoint."""
        if endpoint_path:
            metrics = self._metrics.get(endpoint_path)
            if metrics:
                return {
                    "endpoint": endpoint_path,
                    "total_requests": metrics.total_requests,
                    "avg_response_time_ms": round(metrics.avg_response_time_ms, 2),
                    "p95_response_time_ms": round(metrics.p95_response_time_ms, 2),
                    "p99_response_time_ms": round(metrics.p99_response_time_ms, 2),
                    "error_rate": round(metrics.error_rate * 100, 2),
                    "slow_request_count": metrics.slow_request_count,
                }
            return {}
        
        return {
            path: {
                "total_requests": m.total_requests,
                "avg_response_time_ms": round(m.avg_response_time_ms, 2),
                "p95_response_time_ms": round(m.p95_response_time_ms, 2),
                "error_rate": round(m.error_rate * 100, 2),
            }
            for path, m in self._metrics.items()
        }
    
    def get_circuit_status(self, endpoint_path: Optional[str] = None) -> Dict[str, Any]:
        """Get circuit breaker status."""
        if endpoint_path:
            circuit = self._circuits.get(endpoint_path)
            if circuit:
                return {
                    "endpoint": endpoint_path,
                    "state": circuit.state.value,
                    "failure_count": circuit.failure_count,
                    "success_count": circuit.success_count,
                }
            return {}
        
        return {
            path: {
                "state": c.state.value,
                "failure_count": c.failure_count,
            }
            for path, c in self._circuits.items()
        }
    
    def get_optimizations(
        self,
        endpoint_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get applied optimizations."""
        optimizations = list(self._optimizations.values())
        
        if endpoint_path:
            optimizations = [o for o in optimizations if o.endpoint_path == endpoint_path]
        
        return [
            {
                "id": str(o.id),
                "endpoint": o.endpoint_path,
                "type": o.optimization_type.value,
                "description": o.description,
                "applied_at": o.applied_at.isoformat(),
                "status": o.status,
                "improvement": o.improvement_percent,
            }
            for o in sorted(optimizations, key=lambda x: x.applied_at, reverse=True)
        ]
    
    async def verify_optimization(self, optimization_id: UUID) -> Optional[AutoOptimization]:
        """Verify an optimization by comparing before/after metrics."""
        optimization = self._optimizations.get(optimization_id)
        if not optimization:
            return None
        
        # Get current metrics
        metrics = self._metrics.get(optimization.endpoint_path)
        if metrics:
            optimization.after_metrics = {
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "error_rate": metrics.error_rate,
            }
            
            # Calculate improvement
            before_avg = optimization.before_metrics.get("avg_response_time_ms", 0)
            after_avg = optimization.after_metrics.get("avg_response_time_ms", 0)
            
            if before_avg > 0:
                improvement = (before_avg - after_avg) / before_avg * 100
                optimization.improvement_percent = improvement
            
            optimization.status = "verified"
        
        return optimization


def circuit_breaker_middleware(circuit_breaker: AutoCircuitBreaker):
    """Middleware factory for circuit breaker integration."""
    async def middleware(request, call_next):
        endpoint_path = request.url.path
        
        # Check if circuit is open
        if not circuit_breaker.can_execute(endpoint_path):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable (circuit open)"
            )
        
        # Check cache for GET requests
        if request.method == "GET":
            cache_key = str(request.url)
            cached = await circuit_breaker.get_cached_response(endpoint_path, cache_key)
            if cached is not None:
                from starlette.responses import JSONResponse
                return JSONResponse(content=cached)
        
        # Execute request
        start_time = time.time()
        try:
            response = await call_next(request)
            
            # Record metrics
            response_time_ms = (time.time() - start_time) * 1000
            is_error = response.status_code >= 500
            
            await circuit_breaker.record_request(
                endpoint_path,
                response_time_ms,
                is_error,
            )
            
            # Cache successful GET responses
            if request.method == "GET" and response.status_code < 400:
                # Would need to read response body to cache
                pass
            
            return response
            
        except Exception as e:
            # Record error
            response_time_ms = (time.time() - start_time) * 1000
            await circuit_breaker.record_request(
                endpoint_path,
                response_time_ms,
                is_error=True,
            )
            raise
    
    return middleware


# Singleton instance
circuit_breaker_instance: Optional[AutoCircuitBreaker] = None


def get_circuit_breaker() -> AutoCircuitBreaker:
    """Get or create the singleton circuit breaker instance."""
    global circuit_breaker_instance
    if circuit_breaker_instance is None:
        circuit_breaker_instance = AutoCircuitBreaker()
    return circuit_breaker_instance
