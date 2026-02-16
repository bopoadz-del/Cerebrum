"""
Schedule Integration Module
Handles look-ahead schedule views and subcontractor schedule integration.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer, Date
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class ScheduleTaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    ON_HOLD = "on_hold"


class LookaheadPeriod(str, Enum):
    THREE_DAY = "3_day"
    ONE_WEEK = "1_week"
    TWO_WEEK = "2_week"
    THREE_WEEK = "3_week"
    FOUR_WEEK = "4_week"


class ScheduleTask(Base):
    """Schedule task from master schedule."""
    __tablename__ = 'schedule_tasks'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    task_code = Column(String(100), nullable=False)
    task_name = Column(String(500), nullable=False)
    description = Column(Text)
    
    wbs_code = Column(String(100))
    parent_task_id = Column(PG_UUID(as_uuid=True), ForeignKey('schedule_tasks.id'))
    
    start_date = Column(Date)
    finish_date = Column(Date)
    original_duration = Column(Integer)
    remaining_duration = Column(Integer)
    percent_complete = Column(Integer, default=0)
    
    assigned_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    status = Column(String(50), default=ScheduleTaskStatus.NOT_STARTED)
    
    predecessors = Column(JSONB, default=list)  # List of task IDs
    successors = Column(JSONB, default=list)  # List of task IDs
    
    external_id = Column(String(255))  # ID from external schedule system
    schedule_source = Column(String(100))  # p6, ms_project, asta, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lookahead_items = relationship("LookaheadItem", back_populates="schedule_task")


class LookaheadItem(Base):
    """Look-ahead schedule item for subcontractors."""
    __tablename__ = 'lookahead_items'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    schedule_task_id = Column(PG_UUID(as_uuid=True), ForeignKey('schedule_tasks.id'))
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'), nullable=False)
    
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    
    planned_start = Column(Date)
    planned_finish = Column(Date)
    
    crew_size = Column(Integer)
    equipment_needed = Column(JSONB, default=list)
    materials_needed = Column(JSONB, default=list)
    
    constraints = Column(Text)  # What's needed to start
    readiness_status = Column(String(50), default="not_ready")
    
    notes = Column(Text)
    
    submitted_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    approved_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    approved_at = Column(DateTime)
    
    # Relationships
    schedule_task = relationship("ScheduleTask", back_populates="lookahead_items")


class ScheduleImport(Base):
    """Schedule import record."""
    __tablename__ = 'schedule_imports'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    source_type = Column(String(100), nullable=False)  # p6, ms_project, primavera, etc.
    file_name = Column(String(500))
    file_url = Column(String(1000))
    
    imported_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    imported_at = Column(DateTime, default=datetime.utcnow)
    
    tasks_imported = Column(Integer)
    tasks_updated = Column(Integer)
    tasks_failed = Column(Integer)
    
    status = Column(String(50), default="processing")
    error_log = Column(Text)


# Pydantic Models

class ScheduleTaskCreateRequest(BaseModel):
    task_code: str
    task_name: str
    description: Optional[str] = None
    wbs_code: Optional[str] = None
    parent_task_id: Optional[str] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None
    original_duration: Optional[int] = None
    assigned_company_id: Optional[str] = None
    predecessors: List[str] = []
    successors: List[str] = []
    external_id: Optional[str] = None


class ScheduleTaskUpdateRequest(BaseModel):
    task_name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    finish_date: Optional[str] = None
    remaining_duration: Optional[int] = None
    percent_complete: Optional[int] = None
    assigned_company_id: Optional[str] = None
    status: Optional[ScheduleTaskStatus] = None


class LookaheadItemCreateRequest(BaseModel):
    schedule_task_id: Optional[str] = None
    week_start: str
    week_end: str
    planned_start: Optional[str] = None
    planned_finish: Optional[str] = None
    crew_size: Optional[int] = None
    equipment_needed: List[str] = []
    materials_needed: List[str] = []
    constraints: Optional[str] = None
    notes: Optional[str] = None


class LookaheadItemUpdateRequest(BaseModel):
    planned_start: Optional[str] = None
    planned_finish: Optional[str] = None
    crew_size: Optional[int] = None
    equipment_needed: Optional[List[str]] = None
    materials_needed: Optional[List[str]] = None
    constraints: Optional[str] = None
    readiness_status: Optional[str] = None
    notes: Optional[str] = None


class ScheduleImportRequest(BaseModel):
    source_type: str
    file_url: str
    file_name: str


class ScheduleTaskResponse(BaseModel):
    id: str
    task_code: str
    task_name: str
    description: Optional[str]
    wbs_code: Optional[str]
    start_date: Optional[str]
    finish_date: Optional[str]
    original_duration: Optional[int]
    remaining_duration: Optional[int]
    percent_complete: int
    assigned_company_id: Optional[str]
    assigned_company_name: Optional[str]
    status: str
    predecessors: List[str]
    successors: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LookaheadItemResponse(BaseModel):
    id: str
    schedule_task_id: Optional[str]
    schedule_task_name: Optional[str]
    week_start: str
    week_end: str
    planned_start: Optional[str]
    planned_finish: Optional[str]
    crew_size: Optional[int]
    equipment_needed: List[str]
    materials_needed: List[str]
    constraints: Optional[str]
    readiness_status: str
    notes: Optional[str]
    submitted_at: datetime
    approved_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ScheduleIntegrationService:
    """Service for schedule integration."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def import_schedule(
        self,
        tenant_id: str,
        project_id: str,
        user_id: str,
        request: ScheduleImportRequest
    ) -> ScheduleImport:
        """Import schedule from external system."""
        import_record = ScheduleImport(
            tenant_id=tenant_id,
            project_id=project_id,
            source_type=request.source_type,
            file_name=request.file_name,
            file_url=request.file_url,
            imported_by=user_id,
            status="processing"
        )
        
        self.db.add(import_record)
        self.db.commit()
        
        # Schedule async processing
        # TODO: Trigger Celery task for processing
        
        return import_record
    
    def create_schedule_task(
        self,
        tenant_id: str,
        project_id: str,
        request: ScheduleTaskCreateRequest
    ) -> ScheduleTask:
        """Create a schedule task."""
        task = ScheduleTask(
            tenant_id=tenant_id,
            project_id=project_id,
            task_code=request.task_code,
            task_name=request.task_name,
            description=request.description,
            wbs_code=request.wbs_code,
            parent_task_id=request.parent_task_id,
            start_date=datetime.strptime(request.start_date, "%Y-%m-%d").date() if request.start_date else None,
            finish_date=datetime.strptime(request.finish_date, "%Y-%m-%d").date() if request.finish_date else None,
            original_duration=request.original_duration,
            assigned_company_id=request.assigned_company_id,
            predecessors=request.predecessors,
            successors=request.successors,
            external_id=request.external_id,
            schedule_source="manual"
        )
        
        self.db.add(task)
        self.db.commit()
        return task
    
    def update_task_progress(
        self,
        tenant_id: str,
        task_id: str,
        percent_complete: int,
        remaining_duration: Optional[int] = None
    ) -> ScheduleTask:
        """Update task progress."""
        task = self.db.query(ScheduleTask).filter(
            ScheduleTask.tenant_id == tenant_id,
            ScheduleTask.id == task_id
        ).first()
        
        if not task:
            raise ValueError("Task not found")
        
        task.percent_complete = min(100, max(0, percent_complete))
        
        if remaining_duration is not None:
            task.remaining_duration = remaining_duration
        
        # Update status based on progress
        if task.percent_complete == 100:
            task.status = ScheduleTaskStatus.COMPLETED
        elif task.percent_complete > 0:
            task.status = ScheduleTaskStatus.IN_PROGRESS
        
        # Check for delays
        if task.finish_date and task.finish_date < datetime.utcnow().date() and task.percent_complete < 100:
            task.status = ScheduleTaskStatus.DELAYED
        
        self.db.commit()
        return task
    
    def create_lookahead_item(
        self,
        tenant_id: str,
        project_id: str,
        company_id: str,
        user_id: str,
        request: LookaheadItemCreateRequest
    ) -> LookaheadItem:
        """Create a look-ahead item."""
        item = LookaheadItem(
            tenant_id=tenant_id,
            project_id=project_id,
            company_id=company_id,
            schedule_task_id=request.schedule_task_id,
            week_start=datetime.strptime(request.week_start, "%Y-%m-%d").date(),
            week_end=datetime.strptime(request.week_end, "%Y-%m-%d").date(),
            planned_start=datetime.strptime(request.planned_start, "%Y-%m-%d").date() if request.planned_start else None,
            planned_finish=datetime.strptime(request.planned_finish, "%Y-%m-%d").date() if request.planned_finish else None,
            crew_size=request.crew_size,
            equipment_needed=request.equipment_needed,
            materials_needed=request.materials_needed,
            constraints=request.constraints,
            notes=request.notes,
            submitted_by=user_id
        )
        
        self.db.add(item)
        self.db.commit()
        return item
    
    def get_company_schedule(
        self,
        tenant_id: str,
        project_id: str,
        company_id: str
    ) -> List[ScheduleTask]:
        """Get schedule tasks assigned to a company."""
        return self.db.query(ScheduleTask).filter(
            ScheduleTask.tenant_id == tenant_id,
            ScheduleTask.project_id == project_id,
            ScheduleTask.assigned_company_id == company_id
        ).order_by(ScheduleTask.start_date).all()
    
    def get_lookahead_schedule(
        self,
        tenant_id: str,
        project_id: str,
        company_id: Optional[str] = None,
        weeks: int = 3
    ) -> Dict[str, Any]:
        """Get look-ahead schedule for specified weeks."""
        today = datetime.utcnow().date()
        lookahead_end = today + timedelta(weeks=weeks)
        
        query = self.db.query(ScheduleTask).filter(
            ScheduleTask.tenant_id == tenant_id,
            ScheduleTask.project_id == project_id,
            ScheduleTask.start_date >= today,
            ScheduleTask.start_date <= lookahead_end
        )
        
        if company_id:
            query = query.filter(ScheduleTask.assigned_company_id == company_id)
        
        tasks = query.order_by(ScheduleTask.start_date).all()
        
        # Group by week
        weeks_data = {}
        for i in range(weeks):
            week_start = today + timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            weeks_data[f"week_{i+1}"] = {
                "start": week_start.isoformat(),
                "end": week_end.isoformat(),
                "tasks": []
            }
        
        for task in tasks:
            if task.start_date:
                week_num = (task.start_date - today).days // 7
                if 0 <= week_num < weeks:
                    weeks_data[f"week_{week_num+1}"]["tasks"].append(task)
        
        return {
            "lookahead_period": f"{weeks} weeks",
            "start_date": today.isoformat(),
            "end_date": lookahead_end.isoformat(),
            "weeks": weeks_data,
            "total_tasks": len(tasks)
        }
    
    def get_company_lookahead_items(
        self,
        tenant_id: str,
        project_id: str,
        company_id: str,
        week_start: Optional[str] = None
    ) -> List[LookaheadItem]:
        """Get look-ahead items for a company."""
        query = self.db.query(LookaheadItem).filter(
            LookaheadItem.tenant_id == tenant_id,
            LookaheadItem.project_id == project_id,
            LookaheadItem.company_id == company_id
        )
        
        if week_start:
            start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
            query = query.filter(LookaheadItem.week_start == start_date)
        
        return query.order_by(LookaheadItem.week_start).all()
    
    def approve_lookahead_item(
        self,
        tenant_id: str,
        item_id: str,
        approved_by: str
    ) -> LookaheadItem:
        """Approve a look-ahead item."""
        item = self.db.query(LookaheadItem).filter(
            LookaheadItem.tenant_id == tenant_id,
            LookaheadItem.id == item_id
        ).first()
        
        if not item:
            raise ValueError("Lookahead item not found")
        
        item.approved_by = approved_by
        item.approved_at = datetime.utcnow()
        item.readiness_status = "approved"
        
        self.db.commit()
        return item
    
    def get_critical_path(
        self,
        tenant_id: str,
        project_id: str
    ) -> List[ScheduleTask]:
        """Get critical path tasks."""
        # Simplified critical path - tasks with no float/delayed tasks
        return self.db.query(ScheduleTask).filter(
            ScheduleTask.tenant_id == tenant_id,
            ScheduleTask.project_id == project_id,
            ScheduleTask.status.in_([ScheduleTaskStatus.NOT_STARTED, ScheduleTaskStatus.IN_PROGRESS, ScheduleTaskStatus.DELAYED])
        ).order_by(ScheduleTask.start_date).all()
