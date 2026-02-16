"""
Time Tracking Module
Handles field worker time clock and labor tracking.
"""
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer, Date, Time, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class TimeEntryStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"


class TimeEntryType(str, Enum):
    REGULAR = "regular"
    OVERTIME = "overtime"
    DOUBLE_TIME = "double_time"
    VACATION = "vacation"
    SICK = "sick"
    HOLIDAY = "holiday"


class TimeEntry(Base):
    """Individual time entry for a worker."""
    __tablename__ = 'time_entries'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    worker_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    work_date = Column(Date, nullable=False)
    
    clock_in = Column(DateTime)
    clock_out = Column(DateTime)
    
    start_time = Column(Time)
    end_time = Column(Time)
    
    break_duration_minutes = Column(Integer, default=0)
    lunch_duration_minutes = Column(Integer, default=0)
    
    total_hours = Column(Float, default=0)
    regular_hours = Column(Float, default=0)
    overtime_hours = Column(Float, default=0)
    
    entry_type = Column(String(50), default=TimeEntryType.REGULAR)
    
    cost_code_id = Column(PG_UUID(as_uuid=True), ForeignKey('cost_codes.id'))
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey('schedule_tasks.id'))
    
    location_lat = Column(Float)
    location_lon = Column(Float)
    
    notes = Column(Text)
    
    status = Column(String(50), default=TimeEntryStatus.PENDING)
    
    approved_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    approved_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Timesheet(Base):
    """Weekly timesheet."""
    __tablename__ = 'timesheets'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    worker_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    
    total_hours = Column(Float, default=0)
    regular_hours = Column(Float, default=0)
    overtime_hours = Column(Float, default=0)
    
    status = Column(String(50), default="draft")
    
    submitted_at = Column(DateTime)
    submitted_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    approved_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    approved_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkerProfile(Base):
    """Field worker profile with wage rates."""
    __tablename__ = 'worker_profiles'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    employee_id = Column(String(100))
    trade = Column(String(100))
    classification = Column(String(100))  # apprentice, journeyman, foreman
    
    regular_rate = Column(Integer)  # cents per hour
    overtime_rate = Column(Integer)  # cents per hour
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models

class ClockInRequest(BaseModel):
    project_id: str
    cost_code_id: Optional[str] = None
    task_id: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    time_entry_id: str
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    notes: Optional[str] = None


class ManualTimeEntryRequest(BaseModel):
    project_id: str
    work_date: str
    start_time: str
    end_time: str
    break_duration_minutes: int = 0
    lunch_duration_minutes: int = 30
    cost_code_id: Optional[str] = None
    task_id: Optional[str] = None
    notes: Optional[str] = None


class ApproveTimeRequest(BaseModel):
    time_entry_ids: List[str]
    action: str  # approve, reject
    notes: Optional[str] = None


class WorkerProfileCreateRequest(BaseModel):
    user_id: str
    company_id: str
    employee_id: Optional[str] = None
    trade: Optional[str] = None
    classification: str = "journeyman"
    regular_rate: int  # cents per hour
    overtime_rate: int  # cents per hour


class TimeEntryResponse(BaseModel):
    id: str
    project_id: str
    project_name: Optional[str]
    worker_id: str
    worker_name: Optional[str]
    work_date: date
    clock_in: Optional[datetime]
    clock_out: Optional[datetime]
    start_time: Optional[time]
    end_time: Optional[time]
    break_duration_minutes: int
    lunch_duration_minutes: int
    total_hours: float
    regular_hours: float
    overtime_hours: float
    entry_type: str
    cost_code_id: Optional[str]
    cost_code_name: Optional[str]
    task_id: Optional[str]
    task_name: Optional[str]
    notes: Optional[str]
    status: str
    approved_by_name: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TimesheetResponse(BaseModel):
    id: str
    worker_id: str
    worker_name: Optional[str]
    week_start: date
    week_end: date
    total_hours: float
    regular_hours: float
    overtime_hours: float
    status: str
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class DailySummary(BaseModel):
    date: date
    total_workers: int
    total_hours: float
    regular_hours: float
    overtime_hours: float


class TimeTrackingService:
    """Service for time tracking."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def clock_in(
        self,
        tenant_id: str,
        worker_id: str,
        company_id: Optional[str],
        request: ClockInRequest
    ) -> TimeEntry:
        """Clock in a worker."""
        # Check for existing open entry
        existing = self.db.query(TimeEntry).filter(
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.worker_id == worker_id,
            TimeEntry.clock_out == None
        ).first()
        
        if existing:
            raise ValueError("Worker already clocked in")
        
        now = datetime.utcnow()
        
        entry = TimeEntry(
            tenant_id=tenant_id,
            project_id=request.project_id,
            worker_id=worker_id,
            company_id=company_id,
            work_date=now.date(),
            clock_in=now,
            start_time=now.time(),
            cost_code_id=request.cost_code_id,
            task_id=request.task_id,
            location_lat=request.location_lat,
            location_lon=request.location_lon,
            notes=request.notes
        )
        
        self.db.add(entry)
        self.db.commit()
        return entry
    
    def clock_out(
        self,
        tenant_id: str,
        worker_id: str,
        request: ClockOutRequest
    ) -> TimeEntry:
        """Clock out a worker."""
        entry = self.db.query(TimeEntry).filter(
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.id == request.time_entry_id,
            TimeEntry.worker_id == worker_id,
            TimeEntry.clock_out == None
        ).first()
        
        if not entry:
            raise ValueError("No active time entry found")
        
        now = datetime.utcnow()
        
        entry.clock_out = now
        entry.end_time = now.time()
        
        # Calculate hours
        total_seconds = (now - entry.clock_in).total_seconds()
        break_seconds = (entry.break_duration_minutes + entry.lunch_duration_minutes) * 60
        work_seconds = max(0, total_seconds - break_seconds)
        
        entry.total_hours = round(work_seconds / 3600, 2)
        
        # Calculate regular vs overtime
        if entry.total_hours > 8:
            entry.regular_hours = 8
            entry.overtime_hours = entry.total_hours - 8
            entry.entry_type = TimeEntryType.OVERTIME
        else:
            entry.regular_hours = entry.total_hours
            entry.overtime_hours = 0
        
        self.db.commit()
        return entry
    
    def create_manual_entry(
        self,
        tenant_id: str,
        worker_id: str,
        company_id: Optional[str],
        request: ManualTimeEntryRequest
    ) -> TimeEntry:
        """Create a manual time entry."""
        work_date = datetime.strptime(request.work_date, "%Y-%m-%d").date()
        start_time = datetime.strptime(request.start_time, "%H:%M").time()
        end_time = datetime.strptime(request.end_time, "%H:%M").time()
        
        # Calculate hours
        start_dt = datetime.combine(work_date, start_time)
        end_dt = datetime.combine(work_date, end_time)
        
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        total_seconds = (end_dt - start_dt).total_seconds()
        break_seconds = (request.break_duration_minutes + request.lunch_duration_minutes) * 60
        work_seconds = max(0, total_seconds - break_seconds)
        
        total_hours = round(work_seconds / 3600, 2)
        
        entry = TimeEntry(
            tenant_id=tenant_id,
            project_id=request.project_id,
            worker_id=worker_id,
            company_id=company_id,
            work_date=work_date,
            start_time=start_time,
            end_time=end_time,
            break_duration_minutes=request.break_duration_minutes,
            lunch_duration_minutes=request.lunch_duration_minutes,
            total_hours=total_hours,
            regular_hours=min(total_hours, 8),
            overtime_hours=max(0, total_hours - 8),
            cost_code_id=request.cost_code_id,
            task_id=request.task_id,
            notes=request.notes
        )
        
        self.db.add(entry)
        self.db.commit()
        return entry
    
    def approve_time_entries(
        self,
        tenant_id: str,
        approver_id: str,
        request: ApproveTimeRequest
    ) -> List[TimeEntry]:
        """Approve or reject time entries."""
        entries = []
        
        for entry_id in request.time_entry_ids:
            entry = self.db.query(TimeEntry).filter(
                TimeEntry.tenant_id == tenant_id,
                TimeEntry.id == entry_id
            ).first()
            
            if entry:
                entry.status = TimeEntryStatus.APPROVED if request.action == "approve" else TimeEntryStatus.REJECTED
                entry.approved_by = approver_id
                entry.approved_at = datetime.utcnow()
                entries.append(entry)
        
        self.db.commit()
        return entries
    
    def get_time_entries(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        company_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[TimeEntry]:
        """Get time entries with filters."""
        query = self.db.query(TimeEntry).filter(TimeEntry.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(TimeEntry.project_id == project_id)
        if worker_id:
            query = query.filter(TimeEntry.worker_id == worker_id)
        if company_id:
            query = query.filter(TimeEntry.company_id == company_id)
        if start_date:
            query = query.filter(TimeEntry.work_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
        if end_date:
            query = query.filter(TimeEntry.work_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
        if status:
            query = query.filter(TimeEntry.status == status)
        
        return query.order_by(TimeEntry.work_date.desc(), TimeEntry.start_time.desc()).all()
    
    def get_daily_summary(
        self,
        tenant_id: str,
        project_id: str,
        work_date: str
    ) -> DailySummary:
        """Get daily labor summary."""
        date_obj = datetime.strptime(work_date, "%Y-%m-%d").date()
        
        entries = self.db.query(TimeEntry).filter(
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.project_id == project_id,
            TimeEntry.work_date == date_obj
        ).all()
        
        workers = set(e.worker_id for e in entries)
        
        return DailySummary(
            date=date_obj,
            total_workers=len(workers),
            total_hours=sum(e.total_hours for e in entries),
            regular_hours=sum(e.regular_hours for e in entries),
            overtime_hours=sum(e.overtime_hours for e in entries)
        )
    
    def get_worker_summary(
        self,
        tenant_id: str,
        worker_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Get worker time summary for a period."""
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        entries = self.db.query(TimeEntry).filter(
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.worker_id == worker_id,
            TimeEntry.work_date >= start,
            TimeEntry.work_date <= end
        ).all()
        
        return {
            "worker_id": worker_id,
            "period": f"{start_date} to {end_date}",
            "total_entries": len(entries),
            "total_hours": sum(e.total_hours for e in entries),
            "regular_hours": sum(e.regular_hours for e in entries),
            "overtime_hours": sum(e.overtime_hours for e in entries),
            "days_worked": len(set(e.work_date for e in entries))
        }
    
    def create_worker_profile(
        self,
        tenant_id: str,
        request: WorkerProfileCreateRequest
    ) -> WorkerProfile:
        """Create a worker profile."""
        profile = WorkerProfile(
            tenant_id=tenant_id,
            user_id=request.user_id,
            company_id=request.company_id,
            employee_id=request.employee_id,
            trade=request.trade,
            classification=request.classification,
            regular_rate=request.regular_rate,
            overtime_rate=request.overtime_rate
        )
        
        self.db.add(profile)
        self.db.commit()
        return profile
    
    def get_active_workers(
        self,
        tenant_id: str,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Get currently clocked-in workers."""
        entries = self.db.query(TimeEntry).filter(
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.project_id == project_id,
            TimeEntry.clock_out == None
        ).all()
        
        return [
            {
                "worker_id": e.worker_id,
                "clocked_in_at": e.clock_in,
                "duration_hours": round((datetime.utcnow() - e.clock_in).total_seconds() / 3600, 2) if e.clock_in else 0
            }
            for e in entries
        ]
