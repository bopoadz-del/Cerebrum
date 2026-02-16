"""
Queue Monitoring
Celery queue depth and task monitoring
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import logging

from celery import Celery
from celery.result import AsyncResult
import redis

from app.core.config import settings
from app.core.celery import celery_app

logger = logging.getLogger(__name__)


@dataclass
class QueueStats:
    """Queue statistics"""
    queue_name: str
    pending_count: int
    active_count: int
    scheduled_count: int
    reserved_count: int
    retry_count: int
    dead_letter_count: int


@dataclass
class WorkerStats:
    """Celery worker statistics"""
    hostname: str
    status: str
    active_tasks: int
    processed_tasks: int
    failed_tasks: int
    succeeded_tasks: int
    retried_tasks: int
    rejected_tasks: int
    uptime_seconds: int
    prefetch_count: int


@dataclass
class TaskStats:
    """Task execution statistics"""
    task_name: str
    total_count: int
    success_count: int
    failure_count: int
    retry_count: int
    avg_runtime_ms: float
    min_runtime_ms: float
    max_runtime_ms: float


class CeleryMonitor:
    """Monitor Celery task queue"""
    
    def __init__(self):
        self.celery: Celery = celery_app
        self.redis_client: Optional[redis.Redis] = None
        self.stats_history: List[Dict[str, Any]] = []
        self.max_history = 1000
    
    def initialize(self):
        """Initialize Celery monitor"""
        self.redis_client = redis.from_url(settings.REDIS_URL)
        logger.info("Celery monitor initialized")
    
    def close(self):
        """Close connections"""
        if self.redis_client:
            self.redis_client.close()
    
    def get_queue_stats(self) -> Dict[str, QueueStats]:
        """Get statistics for all queues"""
        if not self.redis_client:
            return {}
        
        queues = {}
        
        # Get queue names from Celery
        inspect = self.celery.control.inspect()
        active_queues = inspect.active_queues() or {}
        
        queue_names = set()
        for worker_queues in active_queues.values():
            for q in worker_queues:
                queue_names.add(q['name'])
        
        # Add default queue
        queue_names.add('celery')
        
        for queue_name in queue_names:
            # Get queue length from Redis
            queue_key = f'celery:{queue_name}'
            pending = self.redis_client.llen(queue_key)
            
            # Get scheduled tasks
            scheduled_key = 'celery:schedule'
            scheduled = self.redis_client.zcard(scheduled_key) or 0
            
            queues[queue_name] = QueueStats(
                queue_name=queue_name,
                pending_count=pending or 0,
                active_count=0,
                scheduled_count=scheduled,
                reserved_count=0,
                retry_count=0,
                dead_letter_count=0
            )
        
        # Get active tasks from workers
        active_tasks = inspect.active() or {}
        for worker, tasks in active_tasks.items():
            for task in tasks:
                queue = task.get('delivery_info', {}).get('routing_key', 'celery')
                if queue in queues:
                    queues[queue].active_count += 1
        
        # Get reserved tasks
        reserved_tasks = inspect.reserved() or {}
        for worker, tasks in reserved_tasks.items():
            for task in tasks:
                queue = task.get('delivery_info', {}).get('routing_key', 'celery')
                if queue in queues:
                    queues[queue].reserved_count += 1
        
        return queues
    
    def get_worker_stats(self) -> List[WorkerStats]:
        """Get worker statistics"""
        inspect = self.celery.control.inspect()
        
        stats = inspect.stats() or {}
        active = inspect.active() or {}
        
        workers = []
        
        for hostname, worker_stats in stats.items():
            worker_active = active.get(hostname, [])
            
            total = worker_stats.get('total', {})
            
            workers.append(WorkerStats(
                hostname=hostname,
                status='online',
                active_tasks=len(worker_active),
                processed_tasks=total.get('tasks', 0),
                failed_tasks=0,  # Would need to track separately
                succeeded_tasks=0,
                retried_tasks=0,
                rejected_tasks=0,
                uptime_seconds=worker_stats.get('uptime', 0),
                prefetch_count=worker_stats.get('prefetch_count', 0)
            ))
        
        return workers
    
    def get_task_stats(self, hours: int = 24) -> List[TaskStats]:
        """Get task execution statistics"""
        # This would query a task result backend
        # For now, return placeholder
        return []
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get currently active tasks"""
        inspect = self.celery.control.inspect()
        active = inspect.active() or {}
        
        tasks = []
        for worker, worker_tasks in active.items():
            for task in worker_tasks:
                tasks.append({
                    'task_id': task.get('id'),
                    'task_name': task.get('name'),
                    'worker': worker,
                    'args': task.get('args'),
                    'kwargs': task.get('kwargs'),
                    'started_at': task.get('time_start')
                })
        
        return tasks
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get scheduled tasks"""
        inspect = self.celery.control.inspect()
        scheduled = inspect.scheduled() or {}
        
        tasks = []
        for worker, worker_tasks in scheduled.items():
            for task in worker_tasks:
                tasks.append({
                    'task_id': task.get('request', {}).get('id'),
                    'task_name': task.get('request', {}).get('name'),
                    'worker': worker,
                    'eta': task.get('eta'),
                    'priority': task.get('priority')
                })
        
        return tasks
    
    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get task result"""
        result = AsyncResult(task_id, app=self.celery)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'traceback': result.traceback if result.failed() else None,
            'date_done': result.date_done.isoformat() if result.date_done else None
        }
    
    def purge_queue(self, queue_name: str = 'celery') -> int:
        """Purge all tasks from a queue"""
        count = self.celery.control.purge()
        logger.info(f"Purged {count} tasks from queue")
        return count
    
    def revoke_task(self, task_id: str, terminate: bool = False):
        """Revoke a task"""
        self.celery.control.revoke(task_id, terminate=terminate)
        logger.info(f"Revoked task: {task_id}")
    
    def get_queue_health(self) -> Dict[str, Any]:
        """Check queue health"""
        queues = self.get_queue_stats()
        workers = self.get_worker_stats()
        
        total_pending = sum(q.pending_count for q in queues.values())
        total_active = sum(q.active_count for q in queues.values())
        worker_count = len(workers)
        
        issues = []
        
        if total_pending > 10000:
            issues.append(f'High queue depth: {total_pending} pending tasks')
        
        if worker_count == 0:
            issues.append('No workers available')
        
        if total_active > worker_count * 10:
            issues.append('Workers may be overloaded')
        
        if issues:
            return {
                'status': 'degraded',
                'issues': issues,
                'queues': {name: {
                    'pending': q.pending_count,
                    'active': q.active_count
                } for name, q in queues.items()},
                'workers': worker_count
            }
        
        return {
            'status': 'healthy',
            'queues': {name: {
                'pending': q.pending_count,
                'active': q.active_count
            } for name, q in queues.items()},
            'workers': worker_count
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get queue summary"""
        queues = self.get_queue_stats()
        workers = self.get_worker_stats()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'queues': {
                name: {
                    'pending': q.pending_count,
                    'active': q.active_count,
                    'scheduled': q.scheduled_count
                }
                for name, q in queues.items()
            },
            'workers': [
                {
                    'hostname': w.hostname,
                    'status': w.status,
                    'active_tasks': w.active_tasks,
                    'processed': w.processed_tasks
                }
                for w in workers
            ],
            'total_pending': sum(q.pending_count for q in queues.values()),
            'total_active': sum(q.active_count for q in queues.values()),
            'worker_count': len(workers)
        }


# Global Celery monitor
celery_monitor = CeleryMonitor()
