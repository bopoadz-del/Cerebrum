"""
Daily Reports Module - Subcontractor daily reports
Item 327: Daily reports
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, date, time
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Numeric, Date, Time
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum

from app.db.base_class import Base


class WeatherCondition(str, Enum):
    """Weather conditions"""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    WINDY = "windy"
    FOGGY = "foggy"


class ReportStatus(str, Enum):
    """Report status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


# Database Models

class DailyReport(Base):
    """Daily report"""
    __tablename__ = 'daily_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('subcontractor_companies.id', ondelete='CASCADE'), nullable=False)
    
    # Report info
    report_number = Column(String(100), nullable=False)
    report_date = Column(Date, nullable=False)
    
    # Weather
    weather_condition = Column(String(50), nullable=True)
    temperature_low = Column(Integer, nullable=True)
    temperature_high = Column(Integer, nullable=True)
    precipitation = Column(Numeric(5, 2), nullable=True)  # inches
    wind_speed = Column(Integer, nullable=True)  # mph
    
    # Work performed
    work_description = Column(Text, nullable=True)
    work_areas = Column(JSONB, default=list)
    
    # Manpower
    workers_on_site = Column(Integer, default=0)
    hours_worked = Column(Numeric(5, 2), default=0)
    trades_present = Column(JSONB, default=list)
    
    # Equipment
    equipment_used = Column(JSONB, default=list)
    
    # Materials
    materials_delivered = Column(JSONB, default=list)
    
    # Visitors
    visitors = Column(JSONB, default=list)
    
    # Issues/Delays
    delays = Column(JSONB, default=list)
    safety_incidents = Column(JSONB, default=list)
    issues = Column(Text, nullable=True)
    
    # Photos
    photos = Column(JSONB, default=list)
    
    # Status
    status = Column(String(50), default=ReportStatus.DRAFT.value)
    
    # Submission
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Review
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkerAttendance(Base):
    """Worker attendance record"""
    __tablename__ = 'worker_attendance'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daily_report_id = Column(UUID(as_uuid=True), ForeignKey('daily_reports.id', ondelete='CASCADE'), nullable=False)
    
    # Worker info
    worker_name = Column(String(255), nullable=False)
    trade = Column(String(100), nullable=True)
    
    # Hours
    time_in = Column(Time, nullable=True)
    time_out = Column(Time, nullable=True)
    hours_worked = Column(Numeric(4, 2), nullable=True)
    
    # Details
    work_performed = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class WorkerAttendanceEntry(BaseModel):
    """Worker attendance entry"""
    worker_name: str
    trade: Optional[str] = None
    time_in: Optional[str] = None  # HH:MM format
    time_out: Optional[str] = None
    hours_worked: Optional[float] = None
    work_performed: Optional[str] = None


class EquipmentEntry(BaseModel):
    """Equipment entry"""
    equipment_type: str
    equipment_id: Optional[str] = None
    hours_used: Optional[float] = None
    operator: Optional[str] = None


class MaterialDeliveryEntry(BaseModel):
    """Material delivery entry"""
    material_description: str
    quantity: Optional[str] = None
    supplier: Optional[str] = None
    delivery_time: Optional[str] = None


class DelayEntry(BaseModel):
    """Delay entry"""
    delay_type: str  # weather, material, labor, equipment, other
    description: str
    duration_hours: Optional[float] = None
    impact: Optional[str] = None


class CreateDailyReportRequest(BaseModel):
    """Create daily report request"""
    project_id: str
    company_id: str
    report_date: date
    weather_condition: Optional[WeatherCondition] = None
    temperature_low: Optional[int] = None
    temperature_high: Optional[int] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[int] = None
    work_description: Optional[str] = None
    work_areas: List[str] = Field(default_factory=list)
    workers_on_site: int = 0
    hours_worked: float = 0
    trades_present: List[str] = Field(default_factory=list)
    equipment_used: List[EquipmentEntry] = Field(default_factory=list)
    materials_delivered: List[MaterialDeliveryEntry] = Field(default_factory=list)
    visitors: List[Dict[str, Any]] = Field(default_factory=list)
    delays: List[DelayEntry] = Field(default_factory=list)
    safety_incidents: List[Dict[str, Any]] = Field(default_factory=list)
    issues: Optional[str] = None
    photos: List[Dict[str, Any]] = Field(default_factory=list)


class ReviewDailyReportRequest(BaseModel):
    """Review daily report request"""
    status: ReportStatus
    notes: Optional[str] = None


# Service Classes

class DailyReportService:
    """Service for daily report management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_report_number(self, project_id: str) -> str:
        """Generate report number"""
        today = datetime.utcnow().strftime('%Y%m%d')
        count = self.db.query(DailyReport).filter(
            DailyReport.project_id == project_id
        ).count()
        return f"DR-{project_id[:8].upper()}-{today}-{count + 1:03d}"
    
    def create_report(
        self,
        request: CreateDailyReportRequest,
        submitted_by: Optional[str] = None
    ) -> DailyReport:
        """Create daily report"""
        
        report = DailyReport(
            project_id=request.project_id,
            company_id=request.company_id,
            report_number=self._generate_report_number(request.project_id),
            report_date=request.report_date,
            weather_condition=request.weather_condition.value if request.weather_condition else None,
            temperature_low=request.temperature_low,
            temperature_high=request.temperature_high,
            precipitation=request.precipitation,
            wind_speed=request.wind_speed,
            work_description=request.work_description,
            work_areas=request.work_areas,
            workers_on_site=request.workers_on_site,
            hours_worked=request.hours_worked,
            trades_present=request.trades_present,
            equipment_used=[e.model_dump() for e in request.equipment_used],
            materials_delivered=[m.model_dump() for m in request.materials_delivered],
            visitors=request.visitors,
            delays=[d.model_dump() for d in request.delays],
            safety_incidents=request.safety_incidents,
            issues=request.issues,
            photos=request.photos,
            status=ReportStatus.SUBMITTED.value,
            submitted_at=datetime.utcnow(),
            submitted_by=submitted_by
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def get_report(self, report_id: str) -> Optional[DailyReport]:
        """Get daily report by ID"""
        return self.db.query(DailyReport).filter(
            DailyReport.id == report_id
        ).first()
    
    def list_reports(
        self,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None
    ) -> List[DailyReport]:
        """List daily reports"""
        
        query = self.db.query(DailyReport)
        
        if project_id:
            query = query.filter(DailyReport.project_id == project_id)
        
        if company_id:
            query = query.filter(DailyReport.company_id == company_id)
        
        if start_date:
            query = query.filter(DailyReport.report_date >= start_date)
        
        if end_date:
            query = query.filter(DailyReport.report_date <= end_date)
        
        if status:
            query = query.filter(DailyReport.status == status)
        
        return query.order_by(DailyReport.report_date.desc()).all()
    
    def review_report(
        self,
        report_id: str,
        request: ReviewDailyReportRequest,
        reviewed_by: str
    ) -> DailyReport:
        """Review daily report"""
        
        report = self.get_report(report_id)
        if not report:
            raise HTTPException(404, "Daily report not found")
        
        report.status = request.status.value
        report.review_notes = request.notes
        report.reviewed_by = reviewed_by
        report.reviewed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def get_project_summary(
        self,
        project_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get project daily report summary"""
        
        query = self.db.query(DailyReport).filter(
            DailyReport.project_id == project_id
        )
        
        if start_date:
            query = query.filter(DailyReport.report_date >= start_date)
        
        if end_date:
            query = query.filter(DailyReport.report_date <= end_date)
        
        reports = query.all()
        
        total_workers = sum(r.workers_on_site for r in reports)
        total_hours = sum(float(r.hours_worked) for r in reports)
        
        # Count by weather
        weather_counts = {}
        for r in reports:
            wc = r.weather_condition or 'unknown'
            weather_counts[wc] = weather_counts.get(wc, 0) + 1
        
        # Count delays
        total_delays = sum(len(r.delays or []) for r in reports)
        
        return {
            "project_id": project_id,
            "total_reports": len(reports),
            "total_workers": total_workers,
            "total_hours": total_hours,
            "average_workers_per_day": total_workers / len(reports) if reports else 0,
            "weather_breakdown": weather_counts,
            "total_delays": total_delays,
            "reports": [
                {
                    "id": str(r.id),
                    "report_number": r.report_number,
                    "report_date": r.report_date.isoformat() if r.report_date else None,
                    "company_id": str(r.company_id),
                    "workers_on_site": r.workers_on_site,
                    "hours_worked": float(r.hours_worked),
                    "status": r.status
                }
                for r in reports
            ]
        }


# Export
__all__ = [
    'WeatherCondition',
    'ReportStatus',
    'DailyReport',
    'WorkerAttendance',
    'WorkerAttendanceEntry',
    'EquipmentEntry',
    'MaterialDeliveryEntry',
    'DelayEntry',
    'CreateDailyReportRequest',
    'ReviewDailyReportRequest',
    'DailyReportService'
]
