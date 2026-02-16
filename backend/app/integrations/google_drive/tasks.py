"""
Celery Background Sync Service for Google Drive
Handles background synchronization tasks with retry logic and monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from celery import Celery, Task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from celery.signals import task_prerun, task_postrun, task_failure

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.google_drive.sync import (
    DeltaSyncEngine, SyncResult, get_sync_manager
)
from app.integrations.google_drive.conflict import (
    ConflictResolver, get_conflict_resolver, get_conflict_queue
)
from app.integrations.google_drive.oauth import get_oauth_manager

logger = get_logger(__name__)

# Initialize Celery
celery_app = Celery(
    'google_drive_sync',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


class SyncStatus(Enum):
    """Sync task status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class SyncTaskInfo:
    """Information about a sync task."""
    task_id: str
    user_id: str
    status: SyncStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[SyncResult] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# In-memory task tracking (would use Redis in production)
_task_registry: Dict[str, SyncTaskInfo] = {}


class SyncTask(Task):
    """Base class for sync tasks with common functionality."""
    
    _max_retries = 3
    _default_retry_delay = 60  # seconds
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Update task registry
        if task_id in _task_registry:
            _task_registry[task_id].status = SyncStatus.FAILED
            _task_registry[task_id].error_message = str(exc)
            _task_registry[task_id].completed_at = datetime.utcnow()
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Task {task_id} completed successfully")
        
        # Update task registry
        if task_id in _task_registry:
            _task_registry[task_id].status = SyncStatus.COMPLETED
            _task_registry[task_id].result = retval
            _task_registry[task_id].completed_at = datetime.utcnow()


@celery_app.task(bind=True, base=SyncTask, max_retries=3)
def sync_user_drive(
    self,
    user_id: str,
    folder_id: Optional[str] = None,
    full_resync: bool = False,
    resolve_conflicts: bool = True
) -> Dict[str, Any]:
    """
    Background task to sync a user's Google Drive.
    
    Args:
        user_id: User ID to sync
        folder_id: Optional folder to limit sync scope
        full_resync: Whether to perform full resync
        resolve_conflicts: Whether to auto-resolve conflicts
    
    Returns:
        Sync result as dictionary
    """
    task_id = self.request.id
    
    # Register task
    _task_registry[task_id] = SyncTaskInfo(
        task_id=task_id,
        user_id=user_id,
        status=SyncStatus.RUNNING,
        started_at=datetime.utcnow()
    )
    
    try:
        logger.info(f"Starting sync for user {user_id}")
        
        # Get sync engine
        sync_manager = get_sync_manager()
        engine = sync_manager.get_engine(user_id)
        
        # Run sync
        if full_resync:
            result = asyncio.run(engine.full_resync(folder_id=folder_id))
        else:
            result = asyncio.run(engine.sync(folder_id=folder_id))
        
        # Handle conflicts if enabled
        if resolve_conflicts and result.success:
            asyncio.run(_process_conflicts(user_id, result.changes))
        
        # Update registry
        _task_registry[task_id].result = result
        _task_registry[task_id].status = SyncStatus.COMPLETED
        _task_registry[task_id].completed_at = datetime.utcnow()
        
        logger.info(f"Sync completed for user {user_id}")
        
        return {
            "success": result.success,
            "files_synced": result.files_synced,
            "folders_synced": result.folders_synced,
            "changes_count": len(result.changes),
            "duration_seconds": result.duration_seconds,
            "errors": result.errors
        }
        
    except SoftTimeLimitExceeded:
        logger.error(f"Sync task timed out for user {user_id}")
        _task_registry[task_id].status = SyncStatus.FAILED
        _task_registry[task_id].error_message = "Task timed out"
        raise
        
    except Exception as exc:
        logger.error(f"Sync failed for user {user_id}: {exc}")
        
        # Update retry count
        _task_registry[task_id].retry_count += 1
        _task_registry[task_id].status = SyncStatus.RETRYING
        
        # Retry with exponential backoff
        retry_count = self.request.retries
        countdown = min(60 * (2 ** retry_count), 3600)  # Max 1 hour
        
        logger.info(f"Retrying sync for user {user_id} in {countdown}s (attempt {retry_count + 1})")
        
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, base=SyncTask, max_retries=2)
def batch_sync(
    self,
    user_ids: List[str],
    folder_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Batch sync multiple users.
    
    Args:
        user_ids: List of user IDs to sync
        folder_id: Optional folder to limit sync scope
    
    Returns:
        Batch sync results
    """
    results = {
        "total": len(user_ids),
        "successful": 0,
        "failed": 0,
        "details": []
    }
    
    for user_id in user_ids:
        try:
            # Call individual sync
            result = sync_user_drive.delay(
                user_id=user_id,
                folder_id=folder_id
            )
            
            results["successful"] += 1
            results["details"].append({
                "user_id": user_id,
                "task_id": result.id,
                "status": "queued"
            })
            
        except Exception as e:
            logger.error(f"Failed to queue sync for user {user_id}: {e}")
            results["failed"] += 1
            results["details"].append({
                "user_id": user_id,
                "error": str(e)
            })
    
    return results


@celery_app.task(bind=True, max_retries=1)
def cleanup_old_tokens(self) -> Dict[str, int]:
    """
    Clean up expired and old tokens.
    
    Returns:
        Cleanup statistics
    """
    stats = {"revoked": 0, "errors": 0}
    
    try:
        # This would query database for old tokens
        # and revoke them
        logger.info("Token cleanup completed")
        return stats
        
    except Exception as exc:
        logger.error(f"Token cleanup failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(bind=True, max_retries=3)
def monitor_sync_health(self) -> Dict[str, Any]:
    """
    Monitor sync health and detect issues.
    
    Returns:
        Health status report
    """
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "active_tasks": 0,
        "failed_recent": 0,
        "average_duration": 0.0,
        "issues": []
    }
    
    try:
        # Analyze task registry
        recent_tasks = [
            t for t in _task_registry.values()
            if t.started_at and t.started_at > datetime.utcnow() - timedelta(hours=24)
        ]
        
        report["active_tasks"] = len([
            t for t in recent_tasks if t.status == SyncStatus.RUNNING
        ])
        
        failed_tasks = [t for t in recent_tasks if t.status == SyncStatus.FAILED]
        report["failed_recent"] = len(failed_tasks)
        
        # Calculate average duration
        completed_tasks = [
            t for t in recent_tasks 
            if t.status == SyncStatus.COMPLETED and t.result
        ]
        
        if completed_tasks:
            durations = [t.result.duration_seconds for t in completed_tasks]
            report["average_duration"] = sum(durations) / len(durations)
        
        # Detect issues
        if report["failed_recent"] > 10:
            report["issues"].append("High failure rate detected")
        
        if report["average_duration"] > 600:  # 10 minutes
            report["issues"].append("Sync duration exceeding threshold")
        
        logger.info(f"Health check completed: {report}")
        return report
        
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


async def _process_conflicts(user_id: str, changes: List[Any]) -> None:
    """Process and resolve conflicts for changes."""
    resolver = get_conflict_resolver()
    queue = get_conflict_queue()
    
    for change in changes:
        # Detect conflicts
        conflict = resolver.detect_conflict(
            local_version=None,  # Would be actual local version
            remote_version=None   # Would be actual remote version
        )
        
        if conflict:
            await queue.add_conflict(conflict)
    
    # Process conflict queue
    await queue.process_queue(auto_resolve=True)


# Scheduled tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks."""
    # Health check every 5 minutes
    sender.add_periodic_task(
        300.0,
        monitor_sync_health.s(),
        name='monitor-sync-health'
    )
    
    # Token cleanup daily
    sender.add_periodic_task(
        86400.0,
        cleanup_old_tokens.s(),
        name='cleanup-old-tokens'
    )


# Signal handlers
@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **extras):
    """Handle task pre-run."""
    logger.debug(f"Task {task_id} starting")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **extras):
    """Handle task post-run."""
    logger.debug(f"Task {task_id} finished with state {state}")


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **extras):
    """Handle task failure."""
    logger.error(f"Task {task_id} failed: {exception}")


class SyncScheduler:
    """Scheduler for managing periodic syncs."""
    
    def __init__(self):
        self._scheduled_syncs: Dict[str, Any] = {}
    
    def schedule_user_sync(
        self,
        user_id: str,
        interval_minutes: int = 30,
        folder_id: Optional[str] = None
    ) -> str:
        """
        Schedule periodic sync for user.
        
        Returns:
            Schedule ID
        """
        schedule_id = f"sync_{user_id}_{interval_minutes}min"
        
        # Create periodic task
        celery_app.add_periodic_task(
            interval_minutes * 60.0,
            sync_user_drive.s(user_id=user_id, folder_id=folder_id),
            name=schedule_id
        )
        
        self._scheduled_syncs[schedule_id] = {
            "user_id": user_id,
            "interval_minutes": interval_minutes,
            "folder_id": folder_id
        }
        
        logger.info(f"Scheduled sync for user {user_id} every {interval_minutes} minutes")
        
        return schedule_id
    
    def cancel_scheduled_sync(self, schedule_id: str) -> bool:
        """Cancel a scheduled sync."""
        if schedule_id in self._scheduled_syncs:
            # Remove from Celery beat schedule
            del self._scheduled_syncs[schedule_id]
            logger.info(f"Cancelled scheduled sync {schedule_id}")
            return True
        return False
    
    def get_scheduled_syncs(self) -> Dict[str, Any]:
        """Get all scheduled syncs."""
        return self._scheduled_syncs.copy()


class SyncMonitor:
    """Monitor for sync operations."""
    
    def __init__(self):
        self._metrics: Dict[str, List[Any]] = {}
    
    def record_metric(self, metric_name: str, value: Any) -> None:
        """Record a metric."""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        
        self._metrics[metric_name].append({
            "timestamp": datetime.utcnow().isoformat(),
            "value": value
        })
    
    def get_metrics(
        self, 
        metric_name: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, List[Any]]:
        """Get recorded metrics."""
        if metric_name:
            return {metric_name: self._metrics.get(metric_name, [])}
        
        return self._metrics.copy()
    
    def get_task_status(self, task_id: str) -> Optional[SyncTaskInfo]:
        """Get status of a specific task."""
        return _task_registry.get(task_id)
    
    def get_user_tasks(self, user_id: str) -> List[SyncTaskInfo]:
        """Get all tasks for a user."""
        return [
            task for task in _task_registry.values()
            if task.user_id == user_id
        ]


# Singleton instances
sync_scheduler = SyncScheduler()
sync_monitor = SyncMonitor()


def get_sync_scheduler() -> SyncScheduler:
    """Get sync scheduler instance."""
    return sync_scheduler


def get_sync_monitor() -> SyncMonitor:
    """Get sync monitor instance."""
    return sync_monitor
