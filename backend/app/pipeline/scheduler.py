"""
Retraining Scheduler

Schedules and manages automated model retraining jobs.
Integrates with Celery for async execution.

Trigger Types:
- SCHEDULED: Time-based triggers (cron schedule)
- DRIFT: Triggered by drift detection
- PERFORMANCE: Triggered by performance degradation
- DATA_VOLUME: Triggered when sufficient new data collected
- MANUAL: Manually triggered

Features:
- Cron-based scheduling
- Drift-based triggers
- Performance-based triggers
- Integration with Celery for async execution
- PostgreSQL for job state persistence
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
import asyncio
import re
from contextlib import asynccontextmanager
from croniter import croniter

from sqlalchemy import (
    Column, String, Float, DateTime, Integer, JSON, 
    Enum as SQLEnum, Text, Boolean, ForeignKey, select, and_, desc
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, AsyncSessionLocal
from app.core.config import settings
from celery import Celery

Base = declarative_base()


class TriggerType(str, Enum):
    """Types of retraining triggers."""
    SCHEDULED = "scheduled"
    DRIFT = "drift"
    PERFORMANCE = "performance"
    DATA_VOLUME = "data_volume"
    MANUAL = "manual"


class JobStatus(str, Enum):
    """Status of a scheduled job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class ScheduleConfigDB(Base):
    """Database model for schedule configurations."""
    __tablename__ = "retraining_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(String(64), unique=True, index=True, nullable=False)
    model_name = Column(String(255), nullable=False, index=True)
    trigger_type = Column(SQLEnum(TriggerType), nullable=False)
    
    # Schedule configuration
    cron_expression = Column(String(64))  # For scheduled triggers
    cooldown_hours = Column(Float, default=24.0)
    enabled = Column(Boolean, default=True)
    
    # Trigger conditions (JSON)
    conditions = Column(JSON)
    
    # Training configuration
    training_config = Column(JSON)
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_triggered = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "schedule_id": self.schedule_id,
            "model_name": self.model_name,
            "trigger_type": self.trigger_type.value if self.trigger_type else None,
            "cron_expression": self.cron_expression,
            "cooldown_hours": self.cooldown_hours,
            "enabled": self.enabled,
            "conditions": self.conditions or {},
            "training_config": self.training_config or {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count,
        }


class RetrainingJobDB(Base):
    """Database model for retraining jobs."""
    __tablename__ = "retraining_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String(64), unique=True, index=True, nullable=False)
    schedule_id = Column(String(64), ForeignKey("retraining_schedules.schedule_id"))
    model_name = Column(String(255), nullable=False, index=True)
    model_version = Column(String(64))
    
    # Job status
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    trigger_type = Column(SQLEnum(TriggerType))
    
    # Timing
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    metrics = Column(JSON)
    logs = Column(JSON)
    error_message = Column(Text)
    
    # Celery task tracking
    celery_task_id = Column(String(64))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "job_id": self.job_id,
            "schedule_id": self.schedule_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "status": self.status.value if self.status else None,
            "trigger_type": self.trigger_type.value if self.trigger_type else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics": self.metrics or {},
            "logs": self.logs or [],
            "error_message": self.error_message,
            "celery_task_id": self.celery_task_id,
        }


@dataclass
class ScheduleConfig:
    """Configuration for a retraining schedule."""
    schedule_id: str
    model_name: str
    trigger_type: TriggerType
    cron_expression: Optional[str] = None
    cooldown_hours: float = 24.0
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    training_config: Dict[str, Any] = field(default_factory=dict)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "model_name": self.model_name,
            "trigger_type": self.trigger_type.value,
            "cron_expression": self.cron_expression,
            "cooldown_hours": self.cooldown_hours,
            "enabled": self.enabled,
            "conditions": self.conditions,
            "training_config": self.training_config,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count,
        }


@dataclass
class RetrainingJob:
    """Retraining job definition."""
    job_id: str
    model_name: str
    schedule_id: Optional[str]
    status: JobStatus
    trigger_type: TriggerType
    model_version: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class RetrainingScheduler:
    """
    Scheduler for automated model retraining.
    
    Supports multiple trigger types:
    - SCHEDULED: Cron-based scheduling (e.g., daily, weekly)
    - DRIFT: Trigger when drift is detected
    - PERFORMANCE: Trigger when performance degrades
    - DATA_VOLUME: Trigger when new data threshold is reached
    - MANUAL: Manually triggered retraining
    
    Features:
    - PostgreSQL for schedule and job state
    - Celery for async job execution
    - Cooldown periods to prevent retraining storms
    - Job history tracking
    """
    
    def __init__(
        self,
        celery_app: Optional[Celery] = None,
        use_async: bool = True
    ):
        self._celery = celery_app
        self._use_async = use_async
        self._scheduled_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
    
    @asynccontextmanager
    async def _get_db_session(self):
        """Get database session."""
        if self._use_async:
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        else:
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    async def create_schedule(
        self,
        model_name: str,
        trigger_type: TriggerType,
        cron_expression: Optional[str] = None,
        cooldown_hours: float = 24.0,
        conditions: Optional[Dict[str, Any]] = None,
        training_config: Optional[Dict[str, Any]] = None,
        created_by: str = ""
    ) -> ScheduleConfig:
        """
        Create a retraining schedule.
        
        Args:
            model_name: Model to retrain
            trigger_type: Type of trigger
            cron_expression: Cron expression for scheduled triggers (e.g., "0 2 * * 0" for weekly)
            cooldown_hours: Minimum hours between retrains
            conditions: Trigger conditions (e.g., drift_threshold)
            training_config: Training hyperparameters
            created_by: User who created the schedule
        """
        schedule_id = f"sched_{uuid.uuid4().hex[:12]}"
        
        # Validate cron expression if scheduled
        if trigger_type == TriggerType.SCHEDULED and cron_expression:
            if not croniter.is_valid(cron_expression):
                raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        config = ScheduleConfig(
            schedule_id=schedule_id,
            model_name=model_name,
            trigger_type=trigger_type,
            cron_expression=cron_expression,
            cooldown_hours=cooldown_hours,
            enabled=True,
            conditions=conditions or {},
            training_config=training_config or {},
            created_by=created_by,
        )
        
        # Persist to database
        async with self._get_db_session() as session:
            schedule_db = ScheduleConfigDB(
                schedule_id=schedule_id,
                model_name=model_name,
                trigger_type=trigger_type,
                cron_expression=cron_expression,
                cooldown_hours=cooldown_hours,
                enabled=True,
                conditions=conditions or {},
                training_config=training_config or {},
                created_by=created_by,
            )
            session.add(schedule_db)
        
        # Start monitoring if scheduled
        if trigger_type == TriggerType.SCHEDULED:
            self._start_schedule_monitoring(schedule_id, cron_expression)
        
        return config
    
    def _start_schedule_monitoring(self, schedule_id: str, cron_expression: str):
        """Start monitoring a scheduled trigger."""
        task = asyncio.create_task(
            self._monitor_schedule(schedule_id, cron_expression)
        )
        self._scheduled_tasks[schedule_id] = task
    
    async def _monitor_schedule(self, schedule_id: str, cron_expression: str):
        """Monitor a scheduled trigger and trigger retraining."""
        cron = croniter(cron_expression, datetime.utcnow())
        
        while self._running:
            # Get next run time
            next_run = cron.get_next(datetime)
            
            # Wait until next run
            wait_seconds = (next_run - datetime.utcnow()).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            
            # Check if schedule still enabled
            async with self._get_db_session() as session:
                result = await session.execute(
                    select(ScheduleConfigDB).where(ScheduleConfigDB.schedule_id == schedule_id)
                )
                schedule = result.scalar_one_or_none()
                
                if not schedule or not schedule.enabled:
                    break
                
                # Check cooldown
                if schedule.last_triggered:
                    hours_since = (datetime.utcnow() - schedule.last_triggered).total_seconds() / 3600
                    if hours_since < schedule.cooldown_hours:
                        continue
                
                # Trigger retraining
                await self.trigger_retraining(schedule_id, TriggerType.SCHEDULED)
    
    async def trigger_retraining(
        self,
        schedule_id: str,
        trigger_type: TriggerType,
        triggered_by: str = "system"
    ) -> str:
        """
        Trigger a retraining job for a schedule.
        
        Returns job_id for tracking.
        """
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        
        async with self._get_db_session() as session:
            # Get schedule
            result = await session.execute(
                select(ScheduleConfigDB).where(ScheduleConfigDB.schedule_id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                raise ValueError(f"Schedule {schedule_id} not found")
            
            # Create job
            job = RetrainingJobDB(
                job_id=job_id,
                schedule_id=schedule_id,
                model_name=schedule.model_name,
                status=JobStatus.SCHEDULED,
                trigger_type=trigger_type,
                scheduled_at=datetime.utcnow(),
            )
            session.add(job)
            
            # Update schedule
            schedule.last_triggered = datetime.utcnow()
            schedule.trigger_count += 1
            schedule.updated_at = datetime.utcnow()
        
        # Queue Celery task if available
        if self._celery:
            task = self._celery.send_task(
                "app.pipeline.tasks.execute_retraining",
                args=[job_id, schedule.model_name, schedule.training_config]
            )
            
            # Update job with Celery task ID
            async with self._get_db_session() as session:
                result = await session.execute(
                    select(RetrainingJobDB).where(RetrainingJobDB.job_id == job_id)
                )
                job_db = result.scalar_one()
                job_db.celery_task_id = task.id
        
        return job_id
    
    async def trigger_drift_retraining(
        self,
        model_name: str,
        drift_report_id: str,
        severity: str,
        training_config: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Trigger retraining based on drift detection.
        
        Only triggers if:
        - Drift severity is HIGH or CRITICAL
        - No recent retraining (respects cooldown)
        """
        if severity not in ["high", "critical"]:
            return None
        
        # Find or create schedule for this model
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ScheduleConfigDB)
                .where(ScheduleConfigDB.model_name == model_name)
                .where(ScheduleConfigDB.trigger_type == TriggerType.DRIFT)
                .where(ScheduleConfigDB.enabled == True)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                # Auto-create drift schedule
                schedule_id = await self.create_schedule(
                    model_name=model_name,
                    trigger_type=TriggerType.DRIFT,
                    cooldown_hours=24,
                    conditions={"min_severity": "high"},
                    training_config=training_config or {},
                    created_by="system"
                )
                schedule_id = schedule_id.schedule_id
            else:
                schedule_id = schedule.schedule_id
                # Check cooldown
                if schedule.last_triggered:
                    hours_since = (datetime.utcnow() - schedule.last_triggered).total_seconds() / 3600
                    if hours_since < schedule.cooldown_hours:
                        return None
        
        return await self.trigger_retraining(schedule_id, TriggerType.DRIFT, "drift_detector")
    
    async def trigger_performance_retraining(
        self,
        model_name: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        training_config: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Trigger retraining based on performance degradation.
        
        Triggers when performance drops below threshold.
        """
        # Check if degradation is significant
        if metric_value >= threshold:
            return None
        
        # Find or create schedule
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ScheduleConfigDB)
                .where(ScheduleConfigDB.model_name == model_name)
                .where(ScheduleConfigDB.trigger_type == TriggerType.PERFORMANCE)
                .where(ScheduleConfigDB.enabled == True)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                schedule_config = await self.create_schedule(
                    model_name=model_name,
                    trigger_type=TriggerType.PERFORMANCE,
                    cooldown_hours=12,
                    conditions={"metric_name": metric_name, "threshold": threshold},
                    training_config=training_config or {},
                    created_by="system"
                )
                schedule_id = schedule_config.schedule_id
            else:
                schedule_id = schedule.schedule_id
                # Check cooldown
                if schedule.last_triggered:
                    hours_since = (datetime.utcnow() - schedule.last_triggered).total_seconds() / 3600
                    if hours_since < schedule.cooldown_hours:
                        return None
        
        return await self.trigger_retraining(schedule_id, TriggerType.PERFORMANCE, "performance_monitor")
    
    async def start_job(self, job_id: str) -> bool:
        """Mark a job as started."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(RetrainingJobDB).where(RetrainingJobDB.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job or job.status != JobStatus.SCHEDULED:
                return False
            
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.logs = [f"Job started at {job.started_at}"]
            
            return True
    
    async def complete_job(
        self,
        job_id: str,
        model_version: str,
        metrics: Dict[str, float],
        logs: List[str]
    ) -> bool:
        """Mark a job as completed."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(RetrainingJobDB).where(RetrainingJobDB.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job or job.status != JobStatus.RUNNING:
                return False
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.model_version = model_version
            job.metrics = metrics
            job.logs = logs + [f"Job completed at {job.completed_at}"]
            
            return True
    
    async def fail_job(self, job_id: str, error_message: str) -> bool:
        """Mark a job as failed."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(RetrainingJobDB).where(RetrainingJobDB.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return False
            
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = error_message
            
            return True
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled or running job."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(RetrainingJobDB).where(RetrainingJobDB.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job or job.status not in [JobStatus.SCHEDULED, JobStatus.RUNNING]:
                return False
            
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            
            # Revoke Celery task if running
            if job.celery_task_id and self._celery:
                self._celery.control.revoke(job.celery_task_id, terminate=True)
            
            return True
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(RetrainingJobDB).where(RetrainingJobDB.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            return job.to_dict() if job else None
    
    async def list_jobs(
        self,
        model_name: Optional[str] = None,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List retraining jobs."""
        async with self._get_db_session() as session:
            query = select(RetrainingJobDB)
            
            if model_name:
                query = query.where(RetrainingJobDB.model_name == model_name)
            if status:
                query = query.where(RetrainingJobDB.status == status)
            
            query = query.order_by(desc(RetrainingJobDB.scheduled_at))
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            jobs = result.scalars().all()
            
            return [j.to_dict() for j in jobs]
    
    async def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """Get schedule configuration."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ScheduleConfigDB).where(ScheduleConfigDB.schedule_id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                return None
            
            return ScheduleConfig(
                schedule_id=schedule.schedule_id,
                model_name=schedule.model_name,
                trigger_type=schedule.trigger_type,
                cron_expression=schedule.cron_expression,
                cooldown_hours=schedule.cooldown_hours,
                enabled=schedule.enabled,
                conditions=schedule.conditions or {},
                training_config=schedule.training_config or {},
                created_by=schedule.created_by or "",
                created_at=schedule.created_at,
                last_triggered=schedule.last_triggered,
                trigger_count=schedule.trigger_count,
            )
    
    async def list_schedules(
        self,
        model_name: Optional[str] = None,
        trigger_type: Optional[TriggerType] = None,
        enabled_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List retraining schedules."""
        async with self._get_db_session() as session:
            query = select(ScheduleConfigDB)
            
            if model_name:
                query = query.where(ScheduleConfigDB.model_name == model_name)
            if trigger_type:
                query = query.where(ScheduleConfigDB.trigger_type == trigger_type)
            if enabled_only:
                query = query.where(ScheduleConfigDB.enabled == True)
            
            query = query.order_by(desc(ScheduleConfigDB.created_at))
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            schedules = result.scalars().all()
            
            return [s.to_dict() for s in schedules]
    
    async def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a schedule."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ScheduleConfigDB).where(ScheduleConfigDB.schedule_id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                return False
            
            schedule.enabled = True
            schedule.updated_at = datetime.utcnow()
            
            # Start monitoring if scheduled
            if schedule.trigger_type == TriggerType.SCHEDULED and schedule.cron_expression:
                self._start_schedule_monitoring(schedule_id, schedule.cron_expression)
            
            return True
    
    async def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ScheduleConfigDB).where(ScheduleConfigDB.schedule_id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                return False
            
            schedule.enabled = False
            schedule.updated_at = datetime.utcnow()
            
            # Stop monitoring if scheduled
            if schedule_id in self._scheduled_tasks:
                task = self._scheduled_tasks[schedule_id]
                task.cancel()
                del self._scheduled_tasks[schedule_id]
            
            return True
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule.""""
        # Disable first
        await self.disable_schedule(schedule_id)
        
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ScheduleConfigDB).where(ScheduleConfigDB.schedule_id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                return False
            
            await session.delete(schedule)
            return True
    
    async def start(self):
        """Start the scheduler."""
        self._running = True
        
        # Load and start all enabled scheduled schedules
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ScheduleConfigDB)
                .where(ScheduleConfigDB.trigger_type == TriggerType.SCHEDULED)
                .where(ScheduleConfigDB.enabled == True)
            )
            schedules = result.scalars().all()
            
            for schedule in schedules:
                if schedule.cron_expression:
                    self._start_schedule_monitoring(schedule.schedule_id, schedule.cron_expression)
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        
        # Cancel all scheduled tasks
        for task in self._scheduled_tasks.values():
            task.cancel()
        
        self._scheduled_tasks.clear()
    
    async def get_next_run_times(self, schedule_id: str, count: int = 5) -> List[str]:
        """Get next scheduled run times for a schedule."""
        schedule = await self.get_schedule(schedule_id)
        
        if not schedule or not schedule.cron_expression:
            return []
        
        cron = croniter(schedule.cron_expression, datetime.utcnow())
        times = []
        
        for _ in range(count):
            next_run = cron.get_next(datetime)
            times.append(next_run.isoformat())
        
        return times


# Celery task for retraining execution
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def execute_retraining(
    self,
    job_id: str,
    model_name: str,
    training_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Celery task to execute model retraining.
    
    This is called by the scheduler when a retraining job is triggered.
    """
    import asyncio
    
    async def _retrain():
        from app.pipeline.retraining import RetrainingOrchestrator
        
        orchestrator = RetrainingOrchestrator()
        
        try:
            # Start job
            await orchestrator.start_job(job_id)
            
            # Execute retraining
            job = await orchestrator.run_retraining(
                job_id=job_id,
                model_name=model_name,
                training_config=training_config
            )
            
            return {
                "success": True,
                "job_id": job_id,
                "model_version": job.model_version,
                "metrics": job.metrics,
            }
        
        except Exception as e:
            # Retry on failure
            retry_count = self.request.retries
            countdown = 60 * (2 ** retry_count)
            
            self.retry(exc=e, countdown=countdown)
    
    # Run async function in sync Celery context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_retrain())
    finally:
        loop.close()


# Migration SQL
SCHEDULER_MIGRATION = """
-- Migration for scheduler tables

-- Retraining schedules table
CREATE TABLE IF NOT EXISTS retraining_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id VARCHAR(64) UNIQUE NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    trigger_type VARCHAR(16) NOT NULL,
    cron_expression VARCHAR(64),
    cooldown_hours FLOAT DEFAULT 24.0,
    enabled BOOLEAN DEFAULT TRUE,
    conditions JSONB,
    training_config JSONB,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_triggered TIMESTAMP WITH TIME ZONE,
    trigger_count INTEGER DEFAULT 0
);

-- Retraining jobs table
CREATE TABLE IF NOT EXISTS retraining_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(64) UNIQUE NOT NULL,
    schedule_id VARCHAR(64) REFERENCES retraining_schedules(schedule_id),
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(64),
    status VARCHAR(16) DEFAULT 'pending',
    trigger_type VARCHAR(16),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metrics JSONB,
    logs JSONB,
    error_message TEXT,
    celery_task_id VARCHAR(64)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_schedules_model ON retraining_schedules(model_name);
CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON retraining_schedules(enabled);
CREATE INDEX IF NOT EXISTS idx_schedules_trigger_type ON retraining_schedules(trigger_type);
CREATE INDEX IF NOT EXISTS idx_jobs_model ON retraining_jobs(model_name);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON retraining_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON retraining_jobs(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_jobs_schedule ON retraining_jobs(schedule_id);
"""
