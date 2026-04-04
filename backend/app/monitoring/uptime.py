"""
Uptime Monitoring
Pingdom/UptimeRobot-style health checks for Cerebrum AI Platform
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import aiohttp
import ssl

from app.core.config import settings

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    """Check status values"""
    UP = 'up'
    DOWN = 'down'
    PAUSED = 'paused'
    UNKNOWN = 'unknown'


class CheckType(Enum):
    """Types of uptime checks"""
    HTTP = 'http'
    HTTPS = 'https'
    TCP = 'tcp'
    PING = 'ping'
    DNS = 'dns'


@dataclass
class CheckResult:
    """Result of an uptime check"""
    check_id: str
    timestamp: datetime
    status: CheckStatus
    response_time_ms: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UptimeCheck:
    """Uptime check configuration"""
    id: str
    name: str
    type: CheckType
    target: str
    interval_seconds: int = 60
    timeout_seconds: int = 30
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    headers: Dict[str, str] = field(default_factory=dict)
    body_match: Optional[str] = None
    ssl_verify: bool = True
    follow_redirects: bool = True
    regions: List[str] = field(default_factory=lambda: ['us-east-1'])
    enabled: bool = True


class UptimeMonitor:
    """Monitor service uptime"""
    
    def __init__(self):
        self.checks: Dict[str, UptimeCheck] = {}
        self.results: Dict[str, List[CheckResult]] = {}
        self.max_results = 1000
        self._tasks: Dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable] = []
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize the monitor"""
        ssl_context = ssl.create_default_context()
        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            limit=100,
            limit_per_host=10
        )
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def close(self):
        """Close the monitor"""
        # Stop all check tasks
        for task in self._tasks.values():
            task.cancel()
        
        if self._session:
            await self._session.close()
    
    def add_check(self, check: UptimeCheck):
        """Add an uptime check"""
        self.checks[check.id] = check
        
        if check.enabled:
            self._start_check(check)
    
    def remove_check(self, check_id: str):
        """Remove an uptime check"""
        if check_id in self._tasks:
            self._tasks[check_id].cancel()
            del self._tasks[check_id]
        
        if check_id in self.checks:
            del self.checks[check_id]
    
    def _start_check(self, check: UptimeCheck):
        """Start a check loop"""
        if check.id in self._tasks:
            return
        
        task = asyncio.create_task(self._check_loop(check))
        self._tasks[check.id] = task
    
    async def _check_loop(self, check: UptimeCheck):
        """Run check in a loop"""
        while True:
            try:
                result = await self._execute_check(check)
                await self._store_result(result)
                await self._notify_callbacks(result)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in check loop for {check.id}: {e}")
            
            await asyncio.sleep(check.interval_seconds)
    
    async def _execute_check(self, check: UptimeCheck) -> CheckResult:
        """Execute a single check"""
        start_time = time.time()
        
        try:
            if check.type in [CheckType.HTTP, CheckType.HTTPS]:
                return await self._execute_http_check(check, start_time)
            elif check.type == CheckType.TCP:
                return await self._execute_tcp_check(check, start_time)
            elif check.type == CheckType.PING:
                return await self._execute_ping_check(check, start_time)
            else:
                raise ValueError(f"Unsupported check type: {check.type}")
                
        except asyncio.TimeoutError:
            return CheckResult(
                check_id=check.id,
                timestamp=datetime.utcnow(),
                status=CheckStatus.DOWN,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Timeout after {check.timeout_seconds}s"
            )
        except Exception as e:
            return CheckResult(
                check_id=check.id,
                timestamp=datetime.utcnow(),
                status=CheckStatus.DOWN,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def _execute_http_check(self, check: UptimeCheck, start_time: float) -> CheckResult:
        """Execute HTTP/HTTPS check"""
        ssl_context = None if check.ssl_verify else False
        
        async with self._session.get(
            check.target,
            headers=check.headers,
            ssl=ssl_context,
            allow_redirects=check.follow_redirects,
            timeout=aiohttp.ClientTimeout(total=check.timeout_seconds)
        ) as response:
            response_time_ms = (time.time() - start_time) * 1000
            
            # Check status code
            if response.status not in check.expected_status_codes:
                return CheckResult(
                    check_id=check.id,
                    timestamp=datetime.utcnow(),
                    status=CheckStatus.DOWN,
                    response_time_ms=response_time_ms,
                    status_code=response.status,
                    error_message=f"Unexpected status code: {response.status}"
                )
            
            # Check body match if specified
            if check.body_match:
                body = await response.text()
                if check.body_match not in body:
                    return CheckResult(
                        check_id=check.id,
                        timestamp=datetime.utcnow(),
                        status=CheckStatus.DOWN,
                        response_time_ms=response_time_ms,
                        status_code=response.status,
                        error_message=f"Body match not found: {check.body_match}"
                    )
            
            return CheckResult(
                check_id=check.id,
                timestamp=datetime.utcnow(),
                status=CheckStatus.UP,
                response_time_ms=response_time_ms,
                status_code=response.status
            )
    
    async def _execute_tcp_check(self, check: UptimeCheck, start_time: float) -> CheckResult:
        """Execute TCP check"""
        import socket
        
        try:
            host, port = check.target.split(':')
            port = int(port)
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=check.timeout_seconds
            )
            
            writer.close()
            await writer.wait_closed()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return CheckResult(
                check_id=check.id,
                timestamp=datetime.utcnow(),
                status=CheckStatus.UP,
                response_time_ms=response_time_ms
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return CheckResult(
                check_id=check.id,
                timestamp=datetime.utcnow(),
                status=CheckStatus.DOWN,
                response_time_ms=response_time_ms,
                error_message=str(e)
            )
    
    async def _execute_ping_check(self, check: UptimeCheck, start_time: float) -> CheckResult:
        """Execute ping check"""
        import subprocess
        
        try:
            proc = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', str(check.timeout_seconds), check.target,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=check.timeout_seconds + 2
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if proc.returncode == 0:
                return CheckResult(
                    check_id=check.id,
                    timestamp=datetime.utcnow(),
                    status=CheckStatus.UP,
                    response_time_ms=response_time_ms
                )
            else:
                return CheckResult(
                    check_id=check.id,
                    timestamp=datetime.utcnow(),
                    status=CheckStatus.DOWN,
                    response_time_ms=response_time_ms,
                    error_message=stderr.decode() or 'Ping failed'
                )
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return CheckResult(
                check_id=check.id,
                timestamp=datetime.utcnow(),
                status=CheckStatus.DOWN,
                response_time_ms=response_time_ms,
                error_message=str(e)
            )
    
    async def _store_result(self, result: CheckResult):
        """Store check result"""
        if result.check_id not in self.results:
            self.results[result.check_id] = []
        
        self.results[result.check_id].append(result)
        
        # Trim old results
        if len(self.results[result.check_id]) > self.max_results:
            self.results[result.check_id] = self.results[result.check_id][-self.max_results:]
    
    async def _notify_callbacks(self, result: CheckResult):
        """Notify registered callbacks"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(result))
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Error in uptime callback: {e}")
    
    def on_status_change(self, callback: Callable):
        """Register a callback for status changes"""
        self._callbacks.append(callback)
    
    def get_uptime_stats(self, check_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get uptime statistics for a check"""
        if check_id not in self.results:
            return {'uptime_percentage': 0, 'checks': 0}
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        results = [r for r in self.results[check_id] if r.timestamp > cutoff]
        
        if not results:
            return {'uptime_percentage': 0, 'checks': 0}
        
        up_count = sum(1 for r in results if r.status == CheckStatus.UP)
        total_count = len(results)
        
        avg_response_time = sum(r.response_time_ms for r in results) / total_count
        
        return {
            'uptime_percentage': (up_count / total_count) * 100,
            'checks': total_count,
            'up_count': up_count,
            'down_count': total_count - up_count,
            'avg_response_time_ms': avg_response_time,
            'max_response_time_ms': max(r.response_time_ms for r in results),
            'min_response_time_ms': min(r.response_time_ms for r in results)
        }
    
    def get_all_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get uptime statistics for all checks"""
        stats = {}
        for check_id in self.checks:
            stats[check_id] = self.get_uptime_stats(check_id, hours)
        
        return stats


# Global uptime monitor
uptime_monitor = UptimeMonitor()


class StatusPageGenerator:
    """Generate status page data"""
    
    def __init__(self, uptime_monitor: UptimeMonitor):
        self.uptime_monitor = uptime_monitor
    
    def generate_status_page(self) -> Dict[str, Any]:
        """Generate status page data"""
        now = datetime.utcnow()
        
        status_page = {
            'page': {
                'name': 'Cerebrum AI Platform Status',
                'url': 'https://status.cerebrum.ai',
                'updated_at': now.isoformat()
            },
            'status': {
                'indicator': 'none',  # none, minor, major, critical
                'description': 'All Systems Operational'
            },
            'components': []
        }
        
        for check_id, check in self.uptime_monitor.checks.items():
            stats = self.uptime_monitor.get_uptime_stats(check_id, hours=24)
            
            # Determine component status
            if stats['uptime_percentage'] >= 99.9:
                status = 'operational'
            elif stats['uptime_percentage'] >= 99:
                status = 'degraded_performance'
            elif stats['uptime_percentage'] >= 95:
                status = 'partial_outage'
            else:
                status = 'major_outage'
                status_page['status']['indicator'] = 'critical'
                status_page['status']['description'] = 'Major Service Outage'
            
            component = {
                'id': check_id,
                'name': check.name,
                'status': status,
                'uptime_24h': stats['uptime_percentage'],
                'avg_response_time_ms': stats.get('avg_response_time_ms', 0)
            }
            
            status_page['components'].append(component)
        
        return status_page
    
    def generate_incidents(self, days: int = 30) -> List[Dict[str, Any]]:
        """Generate incident history"""
        incidents = []
        
        for check_id, results in self.uptime_monitor.results.items():
            check = self.uptime_monitor.checks.get(check_id)
            if not check:
                continue
            
            # Find incidents (consecutive DOWN results)
            incident_start = None
            
            for result in results:
                if result.status == CheckStatus.DOWN:
                    if incident_start is None:
                        incident_start = result
                else:
                    if incident_start is not None:
                        incidents.append({
                            'check_id': check_id,
                            'check_name': check.name,
                            'started_at': incident_start.timestamp.isoformat(),
                            'resolved_at': result.timestamp.isoformat(),
                            'duration_minutes': (
                                result.timestamp - incident_start.timestamp
                            ).total_seconds() / 60,
                            'error': incident_start.error_message
                        })
                        incident_start = None
        
        return sorted(incidents, key=lambda x: x['started_at'], reverse=True)


# Initialize default checks
def initialize_default_checks():
    """Initialize default uptime checks"""
    checks = [
        UptimeCheck(
            id='api-health',
            name='API Health',
            type=CheckType.HTTPS,
            target=f"{settings.API_BASE_URL}/health",
            interval_seconds=30,
            expected_status_codes=[200]
        ),
        UptimeCheck(
            id='web-app',
            name='Web Application',
            type=CheckType.HTTPS,
            target=settings.APP_BASE_URL,
            interval_seconds=60,
            expected_status_codes=[200]
        ),
        UptimeCheck(
            id='database',
            name='Database Connection',
            type=CheckType.TCP,
            target=f"{settings.DB_HOST}:{settings.DB_PORT}",
            interval_seconds=30
        ),
        UptimeCheck(
            id='redis',
            name='Redis Cache',
            type=CheckType.TCP,
            target=f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            interval_seconds=30
        )
    ]
    
    for check in checks:
        uptime_monitor.add_check(check)
