"""
Health Probes - Kubernetes-style Health Checks
Liveness, readiness, and startup probes for container orchestration.
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    response_time_ms: float
    message: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'status': self.status.value,
            'response_time_ms': self.response_time_ms,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class HealthReport:
    """Overall health report."""
    status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime
    version: str
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'checks': [c.to_dict() for c in self.checks],
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'uptime_seconds': self.uptime_seconds
        }


class HealthCheck:
    """Base class for health checks."""
    
    def __init__(
        self,
        name: str,
        check_func: Callable[[], Coroutine[Any, Any, Dict[str, Any]]],
        timeout_seconds: float = 5.0,
        critical: bool = True
    ):
        self.name = name
        self.check_func = check_func
        self.timeout_seconds = timeout_seconds
        self.critical = critical
        self.logger = logging.getLogger(f"health.{name}")
    
    async def execute(self) -> HealthCheckResult:
        """Execute the health check."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                self.check_func(),
                timeout=self.timeout_seconds
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status from result
            is_healthy = result.get('healthy', True)
            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
            message = result.get('message', 'OK')
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                response_time_ms=response_time,
                message=message,
                timestamp=datetime.utcnow(),
                metadata=result.get('metadata', {})
            )
            
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f'Health check timed out after {self.timeout_seconds}s',
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(f"Health check failed: {e}")
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f'Health check error: {str(e)}',
                timestamp=datetime.utcnow()
            )


class HealthProbeManager:
    """Manager for Kubernetes-style health probes."""
    
    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self.start_time = time.time()
        
        # Health checks by category
        self.liveness_checks: List[HealthCheck] = []
        self.readiness_checks: List[HealthCheck] = []
        self.startup_checks: List[HealthCheck] = []
        
        # Startup tracking
        self.startup_complete = False
        self.startup_failures = 0
        
        self.logger = logging.getLogger(__name__)
    
    def add_liveness_check(self, check: HealthCheck):
        """Add a liveness check."""
        self.liveness_checks.append(check)
    
    def add_readiness_check(self, check: HealthCheck):
        """Add a readiness check."""
        self.readiness_checks.append(check)
    
    def add_startup_check(self, check: HealthCheck):
        """Add a startup check."""
        self.startup_checks.append(check)
    
    async def check_liveness(self) -> HealthReport:
        """Run liveness checks.
        
        Liveness probes determine if the application is running.
        If liveness fails, Kubernetes will restart the container.
        """
        return await self._run_checks(
            self.liveness_checks,
            "Liveness check failed - application may be deadlocked"
        )
    
    async def check_readiness(self) -> HealthReport:
        """Run readiness checks.
        
        Readiness probes determine if the application is ready to serve traffic.
        If readiness fails, Kubernetes will remove the pod from service endpoints.
        """
        # If startup not complete, report not ready
        if not self.startup_complete:
            return HealthReport(
                status=HealthStatus.UNHEALTHY,
                checks=[],
                timestamp=datetime.utcnow(),
                version=self.version,
                uptime_seconds=time.time() - self.start_time
            )
        
        return await self._run_checks(
            self.readiness_checks,
            "Readiness check failed - application not ready for traffic"
        )
    
    async def check_startup(self) -> HealthReport:
        """Run startup checks.
        
        Startup probes determine if the application has started successfully.
        Disabled/disables liveness and readiness checks until complete.
        """
        if self.startup_complete:
            return HealthReport(
                status=HealthStatus.HEALTHY,
                checks=[],
                timestamp=datetime.utcnow(),
                version=self.version,
                uptime_seconds=time.time() - self.start_time
            )
        
        report = await self._run_checks(
            self.startup_checks,
            "Startup check failed - application failed to start"
        )
        
        if report.status == HealthStatus.HEALTHY:
            self.startup_complete = True
            self.logger.info("Startup checks passed - application is ready")
        else:
            self.startup_failures += 1
            self.logger.warning(
                f"Startup check failed (attempt {self.startup_failures}): {report.checks}"
            )
        
        return report
    
    async def _run_checks(
        self,
        checks: List[HealthCheck],
        failure_message: str
    ) -> HealthReport:
        """Run a set of health checks."""
        if not checks:
            return HealthReport(
                status=HealthStatus.HEALTHY,
                checks=[],
                timestamp=datetime.utcnow(),
                version=self.version,
                uptime_seconds=time.time() - self.start_time
            )
        
        # Run all checks concurrently
        results = await asyncio.gather(*[check.execute() for check in checks])
        
        # Determine overall status
        critical_failures = [
            r for r in results
            if r.status == HealthStatus.UNHEALTHY and
            any(c.name == r.name and c.critical for c in checks)
        ]
        
        any_failures = any(r.status == HealthStatus.UNHEALTHY for r in results)
        any_degraded = any(r.status == HealthStatus.DEGRADED for r in results)
        
        if critical_failures:
            overall_status = HealthStatus.UNHEALTHY
        elif any_failures:
            overall_status = HealthStatus.DEGRADED
        elif any_degraded:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return HealthReport(
            status=overall_status,
            checks=list(results),
            timestamp=datetime.utcnow(),
            version=self.version,
            uptime_seconds=time.time() - self.start_time
        )
    
    async def check_all(self) -> Dict[str, HealthReport]:
        """Run all health checks."""
        return {
            'liveness': await self.check_liveness(),
            'readiness': await self.check_readiness(),
            'startup': await self.check_startup()
        }


# Common health check implementations
async def database_health_check(db_pool) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        # Execute simple query
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            
        if result == 1:
            return {
                'healthy': True,
                'message': 'Database connection OK'
            }
        else:
            return {
                'healthy': False,
                'message': 'Database check returned unexpected result'
            }
            
    except Exception as e:
        return {
            'healthy': False,
            'message': f'Database connection failed: {str(e)}'
        }


async def redis_health_check(redis_client) -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        result = await redis_client.ping()
        
        if result:
            info = await redis_client.info('server')
            return {
                'healthy': True,
                'message': 'Redis connection OK',
                'metadata': {
                    'redis_version': info.get('redis_version', 'unknown'),
                    'uptime_in_seconds': info.get('uptime_in_seconds', 0)
                }
            }
        else:
            return {
                'healthy': False,
                'message': 'Redis ping failed'
            }
            
    except Exception as e:
        return {
            'healthy': False,
            'message': f'Redis connection failed: {str(e)}'
        }


async def celery_health_check(celery_app) -> Dict[str, Any]:
    """Check Celery worker status."""
    try:
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        
        if stats:
            worker_count = len(stats)
            return {
                'healthy': True,
                'message': f'{worker_count} Celery workers active',
                'metadata': {
                    'worker_count': worker_count,
                    'workers': list(stats.keys())
                }
            }
        else:
            return {
                'healthy': False,
                'message': 'No Celery workers available'
            }
            
    except Exception as e:
        return {
            'healthy': False,
            'message': f'Celery check failed: {str(e)}'
        }


async def disk_space_health_check(
    path: str = '/',
    min_free_percent: float = 10.0
) -> Dict[str, Any]:
    """Check available disk space."""
    try:
        import shutil
        
        total, used, free = shutil.disk_usage(path)
        free_percent = (free / total) * 100
        
        if free_percent >= min_free_percent:
            return {
                'healthy': True,
                'message': f'Disk space OK ({free_percent:.1f}% free)',
                'metadata': {
                    'total_bytes': total,
                    'free_bytes': free,
                    'free_percent': free_percent
                }
            }
        else:
            return {
                'healthy': False,
                'message': f'Low disk space ({free_percent:.1f}% free)',
                'metadata': {
                    'total_bytes': total,
                    'free_bytes': free,
                    'free_percent': free_percent
                }
            }
            
    except Exception as e:
        return {
            'healthy': False,
            'message': f'Disk space check failed: {str(e)}'
        }


async def memory_health_check(
    max_usage_percent: float = 90.0
) -> Dict[str, Any]:
    """Check memory usage."""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        
        if memory.percent <= max_usage_percent:
            return {
                'healthy': True,
                'message': f'Memory usage OK ({memory.percent:.1f}%)',
                'metadata': {
                    'total_bytes': memory.total,
                    'available_bytes': memory.available,
                    'used_percent': memory.percent
                }
            }
        else:
            return {
                'healthy': False,
                'message': f'High memory usage ({memory.percent:.1f}%)',
                'metadata': {
                    'total_bytes': memory.total,
                    'available_bytes': memory.available,
                    'used_percent': memory.percent
                }
            }
            
    except Exception as e:
        return {
            'healthy': False,
            'message': f'Memory check failed: {str(e)}'
        }


# Singleton instance
health_probe_manager = HealthProbeManager()
