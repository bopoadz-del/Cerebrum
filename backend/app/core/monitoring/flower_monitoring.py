"""
Flower Monitoring Integration - Celery Task Monitoring
Real-time monitoring of Celery workers and tasks using Flower.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp
import logging

logger = logging.getLogger(__name__)


FLOWER_API_URL = os.getenv('FLOWER_API_URL', 'http://localhost:5555/api')
FLOWER_BASIC_AUTH = os.getenv('FLOWER_BASIC_AUTH')  # user:pass format


@dataclass
class WorkerInfo:
    """Celery worker information."""
    hostname: str
    pid: int
    clock: int
    uptime: int
    processed: int
    active: int
    loadavg: List[float]
    sw_ident: str
    sw_ver: str
    sw_sys: str


@dataclass
class TaskInfo:
    """Celery task information."""
    task_id: str
    name: str
    state: str
    received: float
    started: Optional[float]
    succeeded: Optional[float]
    failed: Optional[float]
    runtime: Optional[float]
    worker: Optional[str]
    args: Optional[str]
    kwargs: Optional[str]
    result: Optional[str]
    exception: Optional[str]
    traceback: Optional[str]


@dataclass
class QueueInfo:
    """Celery queue information."""
    name: str
    messages: int
    consumers: int
    memory: int


@dataclass
class BrokerInfo:
    """Message broker information."""
    hostname: str
    port: int
    vhost: str
    transport: str
    uptime: int
    version: str


class FlowerClient:
    """Client for Flower monitoring API."""
    
    def __init__(self, base_url: str = FLOWER_API_URL, auth: Optional[str] = FLOWER_BASIC_AUTH):
        self.base_url = base_url.rstrip('/')
        self.auth = auth
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            headers = {'Accept': 'application/json'}
            
            if self.auth:
                import base64
                auth_str = base64.b64encode(self.auth.encode()).decode()
                headers['Authorization'] = f'Basic {auth_str}'
            
            self.session = aiohttp.ClientSession(headers=headers)
        
        return self.session
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make request to Flower API."""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"Flower API error: {response.status} - {await response.text()}")
                    return None
        except Exception as e:
            self.logger.error(f"Flower API request failed: {e}")
            return None
    
    async def get_workers(self) -> List[WorkerInfo]:
        """Get list of workers."""
        data = await self._request('GET', '/workers')
        
        if not data:
            return []
        
        workers = []
        for hostname, info in data.items():
            workers.append(WorkerInfo(
                hostname=hostname,
                pid=info.get('pid', 0),
                clock=info.get('clock', 0),
                uptime=info.get('uptime', 0),
                processed=info.get('processed', 0),
                active=info.get('active', 0),
                loadavg=info.get('loadavg', [0, 0, 0]),
                sw_ident=info.get('sw_ident', ''),
                sw_ver=info.get('sw_ver', ''),
                sw_sys=info.get('sw_sys', '')
            ))
        
        return workers
    
    async def get_worker_stats(self, worker_name: Optional[str] = None) -> Dict[str, Any]:
        """Get worker statistics."""
        endpoint = f'/worker/{worker_name}' if worker_name else '/workers'
        return await self._request('GET', endpoint) or {}
    
    async def get_tasks(
        self,
        state: Optional[str] = None,
        limit: int = 100,
        worker: Optional[str] = None,
        taskname: Optional[str] = None
    ) -> List[TaskInfo]:
        """Get list of tasks."""
        params = {'limit': limit}
        if state:
            params['state'] = state
        if worker:
            params['worker'] = worker
        if taskname:
            params['taskname'] = taskname
        
        data = await self._request('GET', '/tasks', params=params)
        
        if not data:
            return []
        
        tasks = []
        for task_id, info in data.items():
            tasks.append(TaskInfo(
                task_id=task_id,
                name=info.get('name', ''),
                state=info.get('state', ''),
                received=info.get('received', 0),
                started=info.get('started'),
                succeeded=info.get('succeeded'),
                failed=info.get('failed'),
                runtime=info.get('runtime'),
                worker=info.get('worker'),
                args=info.get('args'),
                kwargs=info.get('kwargs'),
                result=info.get('result'),
                exception=info.get('exception'),
                traceback=info.get('traceback')
            ))
        
        return tasks
    
    async def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Get detailed information about a task."""
        data = await self._request('GET', f'/task/info/{task_id}')
        
        if not data:
            return None
        
        return TaskInfo(
            task_id=task_id,
            name=data.get('name', ''),
            state=data.get('state', ''),
            received=data.get('received', 0),
            started=data.get('started'),
            succeeded=data.get('succeeded'),
            failed=data.get('failed'),
            runtime=data.get('runtime'),
            worker=data.get('worker'),
            args=data.get('args'),
            kwargs=data.get('kwargs'),
            result=data.get('result'),
            exception=data.get('exception'),
            traceback=data.get('traceback')
        )
    
    async def get_queues(self) -> List[QueueInfo]:
        """Get queue information."""
        data = await self._request('GET', '/queues/length')
        
        if not data:
            return []
        
        queues = []
        for name, info in data.items():
            queues.append(QueueInfo(
                name=name,
                messages=info.get('messages', 0),
                consumers=info.get('consumers', 0),
                memory=info.get('memory', 0)
            ))
        
        return queues
    
    async def get_broker_info(self) -> Optional[BrokerInfo]:
        """Get broker information."""
        data = await self._request('GET', '/broker')
        
        if not data:
            return None
        
        return BrokerInfo(
            hostname=data.get('hostname', ''),
            port=data.get('port', 0),
            vhost=data.get('vhost', ''),
            transport=data.get('transport', ''),
            uptime=data.get('uptime', 0),
            version=data.get('version', '')
        )
    
    async def revoke_task(self, task_id: str, terminate: bool = False) -> bool:
        """Revoke a task."""
        params = {'terminate': 'true' if terminate else 'false'}
        result = await self._request('POST', f'/task/revoke/{task_id}', params=params)
        return result is not None
    
    async def retry_task(self, task_id: str) -> bool:
        """Retry a failed task."""
        result = await self._request('POST', f'/task/retry/{task_id}')
        return result is not None
    
    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()


class FlowerMonitoringService:
    """Service for monitoring Celery via Flower."""
    
    def __init__(self, client: Optional[FlowerClient] = None):
        self.client = client or FlowerClient()
        self.logger = logging.getLogger(__name__)
        self.alert_callbacks: List[Callable] = []
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for alerts."""
        self.alert_callbacks.append(callback)
    
    async def _send_alert(self, alert_type: str, message: str, data: Dict[str, Any]):
        """Send alert via registered callbacks."""
        for callback in self.alert_callbacks:
            try:
                await callback(alert_type, message, data)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    async def check_worker_health(self) -> Dict[str, Any]:
        """Check health of all workers."""
        workers = await self.client.get_workers()
        
        healthy_workers = []
        unhealthy_workers = []
        
        for worker in workers:
            # Check if worker is responsive
            if worker.uptime > 0 and worker.loadavg[0] < 10:
                healthy_workers.append(worker)
            else:
                unhealthy_workers.append(worker)
                await self._send_alert(
                    'worker_unhealthy',
                    f"Worker {worker.hostname} appears unhealthy",
                    asdict(worker)
                )
        
        return {
            'healthy_count': len(healthy_workers),
            'unhealthy_count': len(unhealthy_workers),
            'healthy_workers': [w.hostname for w in healthy_workers],
            'unhealthy_workers': [w.hostname for w in unhealthy_workers],
            'timestamp': datetime.now().isoformat()
        }
    
    async def check_queue_health(self, max_queue_size: int = 1000) -> Dict[str, Any]:
        """Check health of task queues."""
        queues = await self.client.get_queues()
        
        healthy_queues = []
        congested_queues = []
        
        for queue in queues:
            if queue.messages < max_queue_size:
                healthy_queues.append(queue)
            else:
                congested_queues.append(queue)
                await self._send_alert(
                    'queue_congested',
                    f"Queue {queue.name} has {queue.messages} messages",
                    asdict(queue)
                )
        
        return {
            'healthy_count': len(healthy_queues),
            'congested_count': len(congested_queues),
            'total_messages': sum(q.messages for q in queues),
            'congested_queues': [q.name for q in congested_queues],
            'timestamp': datetime.now().isoformat()
        }
    
    async def check_failed_tasks(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Check for failed tasks in time window."""
        tasks = await self.client.get_tasks(state='FAILURE', limit=100)
        
        cutoff_time = (datetime.now() - timedelta(minutes=time_window_minutes)).timestamp()
        recent_failures = [t for t in tasks if t.failed and t.failed > cutoff_time]
        
        # Group by task name
        failures_by_task: Dict[str, int] = {}
        for task in recent_failures:
            failures_by_task[task.name] = failures_by_task.get(task.name, 0) + 1
        
        # Alert if too many failures
        if len(recent_failures) > 10:
            await self._send_alert(
                'high_failure_rate',
                f"{len(recent_failures)} tasks failed in last {time_window_minutes} minutes",
                {'failures': len(recent_failures), 'by_task': failures_by_task}
            )
        
        return {
            'total_failures': len(recent_failures),
            'failures_by_task': failures_by_task,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        workers = await self.client.get_workers()
        tasks = await self.client.get_tasks(limit=1000)
        
        # Calculate metrics
        total_processed = sum(w.processed for w in workers)
        total_active = sum(w.active for w in workers)
        
        successful_tasks = [t for t in tasks if t.state == 'SUCCESS']
        failed_tasks = [t for t in tasks if t.state == 'FAILURE']
        
        avg_runtime = 0
        if successful_tasks:
            runtimes = [t.runtime for t in successful_tasks if t.runtime]
            if runtimes:
                avg_runtime = sum(runtimes) / len(runtimes)
        
        return {
            'workers': {
                'count': len(workers),
                'total_processed': total_processed,
                'total_active': total_active,
            },
            'tasks': {
                'total': len(tasks),
                'successful': len(successful_tasks),
                'failed': len(failed_tasks),
                'success_rate': len(successful_tasks) / len(tasks) * 100 if tasks else 0,
                'avg_runtime': avg_runtime,
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run complete health check."""
        return {
            'workers': await self.check_worker_health(),
            'queues': await self.check_queue_health(),
            'failed_tasks': await self.check_failed_tasks(),
            'performance': await self.get_performance_metrics(),
            'overall_status': 'healthy',  # Would calculate based on checks
            'timestamp': datetime.now().isoformat()
        }


class FlowerDashboard:
    """Generate Flower monitoring dashboard data."""
    
    def __init__(self, service: FlowerMonitoringService):
        self.service = service
        self.logger = logging.getLogger(__name__)
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        workers = await self.service.client.get_workers()
        queues = await self.service.client.get_queues()
        recent_tasks = await self.service.client.get_tasks(limit=50)
        
        # Calculate task statistics
        task_states: Dict[str, int] = {}
        for task in recent_tasks:
            task_states[task.state] = task_states.get(task.state, 0) + 1
        
        return {
            'workers': {
                'count': len(workers),
                'details': [asdict(w) for w in workers]
            },
            'queues': {
                'count': len(queues),
                'details': [asdict(q) for q in queues],
                'total_messages': sum(q.messages for q in queues)
            },
            'tasks': {
                'recent_count': len(recent_tasks),
                'by_state': task_states,
                'recent': [asdict(t) for t in recent_tasks[:10]]
            },
            'timestamp': datetime.now().isoformat()
        }


# Singleton instances
flower_client = FlowerClient()
flower_monitoring = FlowerMonitoringService(flower_client)
flower_dashboard = FlowerDashboard(flower_monitoring)
