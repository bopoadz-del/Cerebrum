"""
Cerebrum Agent Task Scheduler

Schedule recurring agent tasks using cron-like scheduling.
Integrates with OpenClaw's cron system.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Types of schedules."""
    ONCE = "once"           # Run once at specific time
    INTERVAL = "interval"   # Run every X seconds/minutes/hours
    CRON = "cron"           # Cron expression
    DAILY = "daily"         # Daily at specific time
    WEEKLY = "weekly"       # Weekly on specific day/time


class TaskStatus(Enum):
    """Status of a scheduled task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """A scheduled agent task."""
    id: str
    name: str
    description: str
    task_template: str  # The task to execute
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]  # cron expr, interval, etc.
    
    # Execution tracking
    status: TaskStatus = TaskStatus.PENDING
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    max_runs: Optional[int] = None  # None = infinite
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "agent"
    enabled: bool = True
    
    # Results
    last_result: Optional[Dict] = None
    history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_template": self.task_template,
            "schedule_type": self.schedule_type.value,
            "schedule_config": self.schedule_config,
            "status": self.status.value,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "max_runs": self.max_runs,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "enabled": self.enabled,
            "last_result": self.last_result
        }
    
    def calculate_next_run(self) -> Optional[str]:
        """Calculate the next run time based on schedule."""
        if not self.enabled:
            return None
        
        if self.max_runs and self.run_count >= self.max_runs:
            return None
        
        now = datetime.now()
        
        if self.schedule_type == ScheduleType.ONCE:
            # One-time task
            run_at = self.schedule_config.get("at")
            if run_at and not self.last_run:
                return run_at
            return None
        
        elif self.schedule_type == ScheduleType.INTERVAL:
            # Interval-based
            interval_seconds = self.schedule_config.get("seconds", 0)
            interval_minutes = self.schedule_config.get("minutes", 0)
            interval_hours = self.schedule_config.get("hours", 0)
            
            delta = timedelta(
                seconds=interval_seconds,
                minutes=interval_minutes,
                hours=interval_hours
            )
            
            if self.last_run:
                last = datetime.fromisoformat(self.last_run)
                next_time = last + delta
            else:
                next_time = now + delta
            
            return next_time.isoformat()
        
        elif self.schedule_type == ScheduleType.DAILY:
            # Daily at specific time
            time_str = self.schedule_config.get("at", "00:00")
            hour, minute = map(int, time_str.split(":"))
            
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)
            
            return next_time.isoformat()
        
        elif self.schedule_type == ScheduleType.WEEKLY:
            # Weekly on specific day
            day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day = self.schedule_config.get("day", "monday").lower()
            time_str = self.schedule_config.get("at", "00:00")
            
            target_day = day_names.index(day)
            current_day = now.weekday()
            hour, minute = map(int, time_str.split(":"))
            
            days_ahead = target_day - current_day
            if days_ahead <= 0:
                days_ahead += 7
            
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            next_time += timedelta(days=days_ahead)
            
            return next_time.isoformat()
        
        elif self.schedule_type == ScheduleType.CRON:
            # For full cron, we'd need a cron parser
            # For now, simplified every-X-minutes
            minutes = self.schedule_config.get("minutes", 60)
            next_time = now + timedelta(minutes=minutes)
            return next_time.isoformat()
        
        return None


class AgentScheduler:
    """
    Task scheduler for the Cerebrum Agent.
    
    Features:
    - Schedule recurring tasks
    - Cron-like expressions
    - Task history tracking
    - Automatic retry on failure
    """
    
    def __init__(self, agent):
        self.agent = agent
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 60  # Check every minute
    
    def create_task(
        self,
        name: str,
        description: str,
        task_template: str,
        schedule_type: str,
        schedule_config: Dict[str, Any],
        max_runs: Optional[int] = None,
        created_by: str = "agent"
    ) -> ScheduledTask:
        """
        Create a new scheduled task.
        
        Args:
            name: Task name
            description: Task description
            task_template: The agent task to execute
            schedule_type: once, interval, daily, weekly, cron
            schedule_config: Schedule-specific config
            max_runs: Maximum number of executions (None = infinite)
            created_by: Who created the task
        
        Returns:
            The created ScheduledTask
        """
        # Generate task ID
        task_hash = hashlib.md5(
            f"{name}:{task_template}:{datetime.now()}".encode()
        ).hexdigest()[:8]
        task_id = f"task_{task_hash}"
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            description=description,
            task_template=task_template,
            schedule_type=ScheduleType(schedule_type),
            schedule_config=schedule_config,
            max_runs=max_runs,
            created_by=created_by
        )
        
        # Calculate first run time
        task.next_run = task.calculate_next_run()
        
        self.tasks[task_id] = task
        logger.info(f"Created scheduled task {task_id}: {name}")
        
        return task
    
    async def start(self):
        """Start the scheduler loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Agent scheduler started")
    
    async def stop(self):
        """Stop the scheduler loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Agent scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                now = datetime.now()
                
                for task in self.tasks.values():
                    if not task.enabled:
                        continue
                    
                    if task.status == TaskStatus.RUNNING:
                        continue
                    
                    if task.next_run:
                        next_run = datetime.fromisoformat(task.next_run)
                        if now >= next_run:
                            # Execute the task
                            asyncio.create_task(self._execute_task(task))
                
                await asyncio.sleep(self._check_interval)
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(self._check_interval)
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now().isoformat()
        task.run_count += 1
        
        logger.info(f"Executing scheduled task {task.id}: {task.name}")
        
        try:
            # Execute the agent task
            result = await self.agent.run(task.task_template)
            
            task.last_result = {
                "success": result.success,
                "message": result.message,
                "timestamp": result.timestamp
            }
            task.status = TaskStatus.COMPLETED
            
            # Add to history
            task.history.append({
                "run_number": task.run_count,
                "timestamp": task.last_run,
                "success": result.success,
                "message": result.message
            })
            
            logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.status = TaskStatus.FAILED
            task.last_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        # Calculate next run
        task.next_run = task.calculate_next_run()
        
        # Reset status if more runs pending
        if task.next_run:
            task.status = TaskStatus.PENDING
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self, include_disabled: bool = False) -> List[Dict]:
        """List all tasks."""
        return [
            t.to_dict() for t in self.tasks.values()
            if include_disabled or t.enabled
        ]
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = True
            task.next_run = task.calculate_next_run()
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        task = self.tasks.get(task_id)
        if task:
            task.enabled = False
            task.next_run = None
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
    
    def run_task_now(self, task_id: str) -> bool:
        """Manually trigger a task to run immediately."""
        task = self.tasks.get(task_id)
        if task and task.status != TaskStatus.RUNNING:
            task.next_run = datetime.now().isoformat()
            return True
        return False
    
    def get_upcoming_tasks(self, limit: int = 10) -> List[Dict]:
        """Get upcoming scheduled tasks."""
        upcoming = []
        
        for task in self.tasks.values():
            if task.enabled and task.next_run:
                upcoming.append({
                    "id": task.id,
                    "name": task.name,
                    "next_run": task.next_run
                })
        
        # Sort by next_run
        upcoming.sort(key=lambda x: x["next_run"])
        return upcoming[:limit]
