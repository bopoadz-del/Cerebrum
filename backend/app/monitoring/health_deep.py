"""
Deep Health Probes - Comprehensive Health Checks
Implements liveness, readiness, and deep health probes.
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
import asyncio
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ProbeType(Enum):
    """Types of health probes."""
    LIVENESS = "liveness"      # Is the process running?
    READINESS = "readiness"    # Is it ready to serve traffic?
    STARTUP = "startup"        # Has it started successfully?
    DEEP = "deep"              # Comprehensive health check


@dataclass
class HealthCheck:
    """Individual health check."""
    name: str
    check_func: Callable[[], Dict[str, Any]]
    probe_types: List[ProbeType] = field(default_factory=lambda: [ProbeType.DEEP])
    timeout_seconds: float = 5.0
    critical: bool = False  # If True, failure makes entire system unhealthy


@dataclass
class HealthResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus
    timestamp: datetime
    version: str
    uptime_seconds: float
    checks: List[HealthResult]
    
    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY)
    
    @property
    def degraded_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED)
    
    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "summary": {
                "healthy": self.healthy_count,
                "degraded": self.degraded_count,
                "unhealthy": self.unhealthy_count,
                "total": len(self.checks)
            },
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "response_time_ms": c.response_time_ms,
                    "error": c.error,
                    "details": c.details
                }
                for c in self.checks
            ]
        }


class HealthCheckManager:
    """Manages health checks for the application."""
    
    def __init__(self, version: str = "unknown"):
        self.version = version
        self.start_time = datetime.utcnow()
        self.checks: List[HealthCheck] = []
        self._cache: Dict[str, tuple] = {}  # (result, timestamp)
        self._cache_ttl_seconds = 5
    
    def register_check(self, check: HealthCheck):
        """Register a health check."""
        self.checks.append(check)
        logger.info(f"Registered health check: {check.name}")
    
    def register_database_check(self, db_pool, critical: bool = True):
        """Register database health check."""
        async def check_db():
            start = time.time()
            try:
                # Execute simple query
                async with db_pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                    return {
                        "status": HealthStatus.HEALTHY.value,
                        "response_time_ms": (time.time() - start) * 1000,
                        "details": {"connected": result == 1}
                    }
            except Exception as e:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "error": str(e)
                }
        
        self.register_check(HealthCheck(
            name="database",
            check_func=check_db,
            probe_types=[ProbeType.READINESS, ProbeType.DEEP],
            critical=critical
        ))
    
    def register_redis_check(self, redis_client, critical: bool = True):
        """Register Redis health check."""
        async def check_redis():
            start = time.time()
            try:
                await redis_client.ping()
                info = await redis_client.info()
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "details": {
                        "version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients")
                    }
                }
            except Exception as e:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "error": str(e)
                }
        
        self.register_check(HealthCheck(
            name="redis",
            check_func=check_redis,
            probe_types=[ProbeType.READINESS, ProbeType.DEEP],
            critical=critical
        ))
    
    def register_celery_check(self, celery_app, critical: bool = True):
        """Register Celery health check."""
        def check_celery():
            start = time.time()
            try:
                # Check broker connection
                with celery_app.connection() as conn:
                    conn.ensure_connection(max_retries=1)
                
                # Get worker stats
                stats = celery_app.control.inspect().stats()
                active_workers = len(stats) if stats else 0
                
                return {
                    "status": HealthStatus.HEALTHY.value if active_workers > 0 else HealthStatus.DEGRADED.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "details": {"active_workers": active_workers}
                }
            except Exception as e:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "error": str(e)
                }
        
        self.register_check(HealthCheck(
            name="celery",
            check_func=check_celery,
            probe_types=[ProbeType.READINESS, ProbeType.DEEP],
            critical=critical
        ))
    
    def register_disk_check(self, path: str = "/", threshold_percent: float = 90.0):
        """Register disk space health check."""
        import shutil
        
        def check_disk():
            start = time.time()
            try:
                usage = shutil.disk_usage(path)
                used_percent = (usage.used / usage.total) * 100
                
                status = HealthStatus.HEALTHY
                if used_percent > threshold_percent:
                    status = HealthStatus.UNHEALTHY
                elif used_percent > threshold_percent * 0.8:
                    status = HealthStatus.DEGRADED
                
                return {
                    "status": status.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "details": {
                        "path": path,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "used_percent": round(used_percent, 2)
                    }
                }
            except Exception as e:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "error": str(e)
                }
        
        self.register_check(HealthCheck(
            name="disk_space",
            check_func=check_disk,
            probe_types=[ProbeType.DEEP],
            critical=False
        ))
    
    def register_memory_check(self, threshold_percent: float = 90.0):
        """Register memory health check."""
        import psutil
        
        def check_memory():
            start = time.time()
            try:
                memory = psutil.virtual_memory()
                
                status = HealthStatus.HEALTHY
                if memory.percent > threshold_percent:
                    status = HealthStatus.UNHEALTHY
                elif memory.percent > threshold_percent * 0.8:
                    status = HealthStatus.DEGRADED
                
                return {
                    "status": status.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "details": {
                        "total_gb": round(memory.total / (1024**3), 2),
                        "available_gb": round(memory.available / (1024**3), 2),
                        "used_percent": memory.percent
                    }
                }
            except Exception as e:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "response_time_ms": (time.time() - start) * 1000,
                    "error": str(e)
                }
        
        self.register_check(HealthCheck(
            name="memory",
            check_func=check_memory,
            probe_types=[ProbeType.DEEP],
            critical=False
        ))
    
    async def run_check(self, check: HealthCheck) -> HealthResult:
        """Run a single health check."""
        start = time.time()
        timestamp = datetime.utcnow()
        
        try:
            # Check cache
            if check.name in self._cache:
                cached_result, cached_time = self._cache[check.name]
                if (timestamp - cached_time).total_seconds() < self._cache_ttl_seconds:
                    return cached_result
            
            # Run check with timeout
            result = await asyncio.wait_for(
                self._run_check_func(check.check_func),
                timeout=check.timeout_seconds
            )
            
            response_time = (time.time() - start) * 1000
            
            health_result = HealthResult(
                name=check.name,
                status=HealthStatus(result.get("status", "unknown")),
                response_time_ms=response_time,
                timestamp=timestamp,
                details=result.get("details", {}),
                error=result.get("error")
            )
            
            # Cache result
            self._cache[check.name] = (health_result, timestamp)
            
            return health_result
        
        except asyncio.TimeoutError:
            return HealthResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=check.timeout_seconds * 1000,
                timestamp=timestamp,
                error=f"Timeout after {check.timeout_seconds}s"
            )
        
        except Exception as e:
            return HealthResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start) * 1000,
                timestamp=timestamp,
                error=str(e)
            )
    
    async def _run_check_func(self, func: Callable) -> Dict[str, Any]:
        """Run check function, handling both sync and async."""
        import inspect
        
        if inspect.iscoroutinefunction(func):
            return await func()
        return func()
    
    async def check_health(self, probe_type: ProbeType = ProbeType.DEEP) -> SystemHealth:
        """Run health checks for specified probe type."""
        timestamp = datetime.utcnow()
        uptime = (timestamp - self.start_time).total_seconds()
        
        # Filter checks by probe type
        checks_to_run = [
            c for c in self.checks 
            if probe_type in c.probe_types
        ]
        
        # Run all checks concurrently
        results = await asyncio.gather(*[
            self.run_check(check) for check in checks_to_run
        ])
        
        # Determine overall status
        critical_failures = [
            r for r in results 
            if r.status == HealthStatus.UNHEALTHY and 
            any(c.critical for c in checks_to_run if c.name == r.name)
        ]
        
        if critical_failures:
            overall_status = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall_status = HealthStatus.DEGRADED
        elif any(r.status == HealthStatus.DEGRADED for r in results):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return SystemHealth(
            status=overall_status,
            timestamp=timestamp,
            version=self.version,
            uptime_seconds=uptime,
            checks=list(results)
        )
    
    async def liveness_check(self) -> SystemHealth:
        """Quick liveness check."""
        return await self.check_health(ProbeType.LIVENESS)
    
    async def readiness_check(self) -> SystemHealth:
        """Readiness check for traffic."""
        return await self.check_health(ProbeType.READINESS)
    
    async def deep_check(self) -> SystemHealth:
        """Comprehensive health check."""
        return await self.check_health(ProbeType.DEEP)


# FastAPI integration
from fastapi import APIRouter, Response, status

health_router = APIRouter(prefix="/health", tags=["health"])

# Global health manager
_health_manager: Optional[HealthCheckManager] = None


def get_health_manager() -> HealthCheckManager:
    """Get global health manager."""
    global _health_manager
    if _health_manager is None:
        _health_manager = HealthCheckManager()
    return _health_manager


def set_health_manager(manager: HealthCheckManager):
    """Set global health manager."""
    global _health_manager
    _health_manager = manager


@health_router.get("/live")
async def liveness_probe():
    """Kubernetes liveness probe."""
    manager = get_health_manager()
    health = await manager.liveness_check()
    
    if health.status == HealthStatus.UNHEALTHY:
        return Response(
            content=health.to_dict(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
    
    return health.to_dict()


@health_router.get("/ready")
async def readiness_probe():
    """Kubernetes readiness probe."""
    manager = get_health_manager()
    health = await manager.readiness_check()
    
    if health.status == HealthStatus.UNHEALTHY:
        return Response(
            content=health.to_dict(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
    
    return health.to_dict()


@health_router.get("")
async def health_check():
    """Deep health check."""
    manager = get_health_manager()
    health = await manager.deep_check()
    
    if health.status == HealthStatus.UNHEALTHY:
        return Response(
            content=health.to_dict(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
    
    return health.to_dict()
