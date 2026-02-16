"""
External Dependency Monitoring
Monitor third-party service dependencies
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

import aiohttp
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DependencyStatus(Enum):
    """Dependency status"""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    UNHEALTHY = 'unhealthy'
    UNKNOWN = 'unknown'


@dataclass
class DependencyCheck:
    """Dependency health check"""
    name: str
    type: str  # http, tcp, custom
    endpoint: str
    method: str = 'GET'
    headers: Dict[str, str] = field(default_factory=dict)
    expected_status: int = 200
    timeout_seconds: int = 10
    check_interval_seconds: int = 60


@dataclass
class DependencyResult:
    """Dependency check result"""
    dependency_name: str
    timestamp: datetime
    status: DependencyStatus
    response_time_ms: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['status'] = self.status.value
        return data


class DependencyMonitor:
    """Monitor external dependencies"""
    
    def __init__(self):
        self.dependencies: Dict[str, DependencyCheck] = {}
        self.results: Dict[str, List[DependencyResult]] = {}
        self.max_results = 1000
        self._check_tasks: Dict[str, asyncio.Task] = {}
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize the monitor"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Load default dependencies
        self._load_default_dependencies()
    
    async def close(self):
        """Close the monitor"""
        for task in self._check_tasks.values():
            task.cancel()
        
        if self._session:
            await self._session.close()
    
    def _load_default_dependencies(self):
        """Load default dependencies to monitor"""
        default_deps = [
            DependencyCheck(
                name='sendgrid',
                type='http',
                endpoint='https://api.sendgrid.com/v3/user/profile',
                headers={'Authorization': f'Bearer {settings.SENDGRID_API_KEY}'},
                timeout_seconds=10
            ),
            DependencyCheck(
                name='stripe',
                type='http',
                endpoint='https://api.stripe.com/v1/charges',
                headers={'Authorization': f'Bearer {settings.STRIPE_SECRET_KEY}'},
                timeout_seconds=10
            ),
            DependencyCheck(
                name='twilio',
                type='http',
                endpoint='https://api.twilio.com/2010-04-01/Accounts.json',
                timeout_seconds=10
            ),
            DependencyCheck(
                name='aws-s3',
                type='http',
                endpoint=f'https://{settings.AWS_S3_BUCKET}.s3.amazonaws.com/',
                timeout_seconds=10
            ),
            DependencyCheck(
                name='google-maps',
                type='http',
                endpoint='https://maps.googleapis.com/maps/api/geocode/json',
                timeout_seconds=10
            ),
            DependencyCheck(
                name='openai',
                type='http',
                endpoint='https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {settings.OPENAI_API_KEY}'},
                timeout_seconds=10
            )
        ]
        
        for dep in default_deps:
            self.add_dependency(dep)
    
    def add_dependency(self, dependency: DependencyCheck):
        """Add a dependency to monitor"""
        self.dependencies[dependency.name] = dependency
        
        # Start monitoring task
        task = asyncio.create_task(self._monitor_loop(dependency))
        self._check_tasks[dependency.name] = task
        
        logger.info(f"Added dependency monitor: {dependency.name}")
    
    async def _monitor_loop(self, dependency: DependencyCheck):
        """Monitor loop for a dependency"""
        while True:
            try:
                result = await self._check_dependency(dependency)
                
                # Store result
                if dependency.name not in self.results:
                    self.results[dependency.name] = []
                
                self.results[dependency.name].append(result)
                
                # Trim old results
                if len(self.results[dependency.name]) > self.max_results:
                    self.results[dependency.name] = self.results[dependency.name][-self.max_results:]
                
                # Alert on status change
                if len(self.results[dependency.name]) > 1:
                    prev_status = self.results[dependency.name][-2].status
                    if prev_status != result.status:
                        await self._alert_status_change(dependency, result)
                
            except Exception as e:
                logger.error(f"Error checking dependency {dependency.name}: {e}")
            
            await asyncio.sleep(dependency.check_interval_seconds)
    
    async def _check_dependency(self, dependency: DependencyCheck) -> DependencyResult:
        """Check a single dependency"""
        start_time = time.time()
        
        try:
            if dependency.type == 'http':
                return await self._check_http_dependency(dependency, start_time)
            elif dependency.type == 'tcp':
                return await self._check_tcp_dependency(dependency, start_time)
            else:
                return DependencyResult(
                    dependency_name=dependency.name,
                    timestamp=datetime.utcnow(),
                    status=DependencyStatus.UNKNOWN,
                    response_time_ms=(time.time() - start_time) * 1000,
                    error_message=f"Unknown check type: {dependency.type}"
                )
        
        except Exception as e:
            return DependencyResult(
                dependency_name=dependency.name,
                timestamp=datetime.utcnow(),
                status=DependencyStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def _check_http_dependency(
        self,
        dependency: DependencyCheck,
        start_time: float
    ) -> DependencyResult:
        """Check HTTP dependency"""
        try:
            async with self._session.request(
                method=dependency.method,
                url=dependency.endpoint,
                headers=dependency.headers,
                timeout=aiohttp.ClientTimeout(total=dependency.timeout_seconds)
            ) as response:
                response_time_ms = (time.time() - start_time) * 1000
                
                # Determine status
                if response.status == dependency.expected_status:
                    status = DependencyStatus.HEALTHY
                elif response.status < 500:
                    status = DependencyStatus.DEGRADED
                else:
                    status = DependencyStatus.UNHEALTHY
                
                return DependencyResult(
                    dependency_name=dependency.name,
                    timestamp=datetime.utcnow(),
                    status=status,
                    response_time_ms=response_time_ms,
                    status_code=response.status,
                    details={'response_headers': dict(response.headers)}
                )
        
        except asyncio.TimeoutError:
            return DependencyResult(
                dependency_name=dependency.name,
                timestamp=datetime.utcnow(),
                status=DependencyStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message='Timeout'
            )
    
    async def _check_tcp_dependency(
        self,
        dependency: DependencyCheck,
        start_time: float
    ) -> DependencyResult:
        """Check TCP dependency"""
        try:
            host, port = dependency.endpoint.split(':')
            port = int(port)
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=dependency.timeout_seconds
            )
            
            writer.close()
            await writer.wait_closed()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return DependencyResult(
                dependency_name=dependency.name,
                timestamp=datetime.utcnow(),
                status=DependencyStatus.HEALTHY,
                response_time_ms=response_time_ms
            )
        
        except Exception as e:
            return DependencyResult(
                dependency_name=dependency.name,
                timestamp=datetime.utcnow(),
                status=DependencyStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def _alert_status_change(self, dependency: DependencyCheck, result: DependencyResult):
        """Alert on dependency status change"""
        logger.warning(
            f"Dependency {dependency.name} status changed to {result.status.value}"
        )
        # Would send alert via notification system
    
    def get_dependency_status(self, dependency_name: str) -> Optional[Dict[str, Any]]:
        """Get current status of a dependency"""
        if dependency_name not in self.results or not self.results[dependency_name]:
            return None
        
        latest = self.results[dependency_name][-1]
        
        # Calculate uptime
        recent_results = self.results[dependency_name][-100:]
        healthy_count = sum(1 for r in recent_results if r.status == DependencyStatus.HEALTHY)
        uptime_pct = (healthy_count / len(recent_results)) * 100 if recent_results else 0
        
        return {
            'name': dependency_name,
            'status': latest.status.value,
            'last_check': latest.timestamp.isoformat(),
            'response_time_ms': latest.response_time_ms,
            'uptime_percentage_24h': uptime_pct,
            'error_message': latest.error_message
        }
    
    def get_all_statuses(self) -> List[Dict[str, Any]]:
        """Get status of all dependencies"""
        return [
            self.get_dependency_status(name)
            for name in self.dependencies.keys()
        ]
    
    def get_dependency_history(
        self,
        dependency_name: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get dependency check history"""
        if dependency_name not in self.results:
            return []
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        history = [r for r in self.results[dependency_name] if r.timestamp > cutoff]
        
        return [r.to_dict() for r in history]


# Global dependency monitor
dependency_monitor = DependencyMonitor()
