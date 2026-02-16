"""
Safety Compliance Module
Handles safety meeting tracking, OSHA logs, and compliance documentation.
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer, Date, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class SafetyMeetingType(str, Enum):
    TOOLBOX_TALK = "toolbox_talk"
    DAILY_HUDDLE = "daily_huddle"
    WEEKLY_SAFETY = "weekly_safety"
    INCIDENT_REVIEW = "incident_review"
    NEW_HIRE_ORIENTATION = "new_hire_orientation"
    SUBCONTRACTOR_ORIENTATION = "subcontractor_orientation"


class IncidentSeverity(str, Enum):
    NEAR_MISS = "near_miss"
    FIRST_AID = "first_aid"
    MEDICAL_TREATMENT = "medical_treatment"
    LOST_TIME = "lost_time"
    FATALITY = "fatality"


class SafetyMeeting(Base):
    """Safety meeting record."""
    __tablename__ = 'safety_meetings'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    meeting_type = Column(String(100), nullable=False)
    meeting_date = Column(Date, nullable=False)
    
    topic = Column(String(500), nullable=False)
    description = Column(Text)
    
    conducted_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    location = Column(String(500))
    duration_minutes = Column(Integer)
    
    attendees = Column(JSONB, default=list)  # List of {user_id, name, signature, attended_at}
    attendee_count = Column(Integer, default=0)
    
    attachments = Column(JSONB, default=list)  # Sign-in sheets, photos
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SafetyIncident(Base):
    """Safety incident record (OSHA log)."""
    __tablename__ = 'safety_incidents'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    incident_number = Column(String(100), nullable=False)
    incident_date = Column(Date, nullable=False)
    incident_time = Column(String(50))
    
    severity = Column(String(50), nullable=False)
    
    injured_person_name = Column(String(255))
    injured_person_title = Column(String(255))
    injured_person_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    location = Column(String(500))
    description = Column(Text, nullable=False)
    
    immediate_cause = Column(Text)
    root_cause = Column(Text)
    contributing_factors = Column(JSONB, default=list)
    
    injury_type = Column(String(255))
    body_part_affected = Column(String(255))
    treatment_provided = Column(Text)
    
    days_away_from_work = Column(Integer)
    days_on_restriction = Column(Integer)
    
    reported_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    reported_at = Column(DateTime, default=datetime.utcnow)
    
    supervisor_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    investigation_completed = Column(Boolean, default=False)
    investigation_completed_at = Column(DateTime)
    
    corrective_actions = Column(JSONB, default=list)
    
    osha_recordable = Column(Boolean, default=False)
    osha_case_number = Column(String(100))
    
    photos = Column(JSONB, default=list)
    witness_statements = Column(JSONB, default=list)
    
    status = Column(String(50), default="open")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SafetyInspection(Base):
    """Safety inspection record."""
    __tablename__ = 'safety_inspections'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    inspection_type = Column(String(100), nullable=False)  # daily, weekly, monthly, special
    inspection_date = Column(Date, nullable=False)
    
    inspected_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    area_inspected = Column(String(500))
    
    findings = Column(JSONB, default=list)  # List of findings
    
    total_items = Column(Integer, default=0)
    compliant_items = Column(Integer, default=0)
    non_compliant_items = Column(Integer, default=0)
    
    score = Column(Float)
    
    status = Column(String(50), default="open")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SafetyFinding(Base):
    """Individual safety finding."""
    __tablename__ = 'safety_findings'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    inspection_id = Column(PG_UUID(as_uuid=True), ForeignKey('safety_inspections.id'))
    
    category = Column(String(100))  # ppe, fall_protection, electrical, etc.
    description = Column(Text, nullable=False)
    severity = Column(String(50))  # low, medium, high, critical
    
    assigned_to = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    due_date = Column(Date)
    
    status = Column(String(50), default="open")
    
    corrected_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    corrected_at = Column(DateTime)
    correction_notes = Column(Text)
    
    photos_before = Column(JSONB, default=list)
    photos_after = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models

class AttendeeInfo(BaseModel):
    user_id: Optional[str] = None
    name: str
    company: Optional[str] = None
    signature: Optional[str] = None
    attended_at: Optional[datetime] = None


class SafetyMeetingCreateRequest(BaseModel):
    project_id: str
    meeting_type: SafetyMeetingType
    meeting_date: str
    topic: str
    description: Optional[str] = None
    company_id: Optional[str] = None
    location: Optional[str] = None
    duration_minutes: int = 15
    attendees: List[AttendeeInfo] = []


class SafetyIncidentCreateRequest(BaseModel):
    project_id: str
    incident_date: str
    incident_time: Optional[str] = None
    severity: IncidentSeverity
    injured_person_name: Optional[str] = None
    injured_person_title: Optional[str] = None
    injured_person_company_id: Optional[str] = None
    location: Optional[str] = None
    description: str
    immediate_cause: Optional[str] = None
    root_cause: Optional[str] = None
    contributing_factors: List[str] = []
    injury_type: Optional[str] = None
    body_part_affected: Optional[str] = None
    treatment_provided: Optional[str] = None


class SafetyInspectionCreateRequest(BaseModel):
    project_id: str
    inspection_type: str
    inspection_date: str
    company_id: Optional[str] = None
    area_inspected: str


class SafetyFindingCreateRequest(BaseModel):
    inspection_id: str
    category: str
    description: str
    severity: str
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


class CorrectFindingRequest(BaseModel):
    correction_notes: str
    photos_after: List[str] = []


class SafetyMeetingResponse(BaseModel):
    id: str
    meeting_type: str
    meeting_date: str
    topic: str
    description: Optional[str]
    conducted_by: Optional[str]
    conducted_by_name: Optional[str]
    company_id: Optional[str]
    company_name: Optional[str]
    location: Optional[str]
    duration_minutes: int
    attendee_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SafetyIncidentResponse(BaseModel):
    id: str
    incident_number: str
    incident_date: str
    incident_time: Optional[str]
    severity: str
    injured_person_name: Optional[str]
    injured_person_title: Optional[str]
    injured_person_company_name: Optional[str]
    location: Optional[str]
    description: str
    injury_type: Optional[str]
    body_part_affected: Optional[str]
    days_away_from_work: Optional[int]
    days_on_restriction: Optional[int]
    osha_recordable: bool
    osha_case_number: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class SafetyComplianceService:
    """Service for safety compliance management."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def _generate_incident_number(self, tenant_id: str, project_id: str) -> str:
        """Generate unique incident number."""
        count = self.db.query(SafetyIncident).filter(
            SafetyIncident.tenant_id == tenant_id,
            SafetyIncident.project_id == project_id
        ).count()
        return f"INC-{count + 1:05d}"
    
    def create_safety_meeting(
        self,
        tenant_id: str,
        user_id: str,
        request: SafetyMeetingCreateRequest
    ) -> SafetyMeeting:
        """Create a safety meeting record."""
        meeting = SafetyMeeting(
            tenant_id=tenant_id,
            project_id=request.project_id,
            meeting_type=request.meeting_type,
            meeting_date=datetime.strptime(request.meeting_date, "%Y-%m-%d").date(),
            topic=request.topic,
            description=request.description,
            conducted_by=user_id,
            company_id=request.company_id,
            location=request.location,
            duration_minutes=request.duration_minutes,
            attendees=[a.dict() for a in request.attendees],
            attendee_count=len(request.attendees)
        )
        
        self.db.add(meeting)
        self.db.commit()
        return meeting
    
    def create_safety_incident(
        self,
        tenant_id: str,
        user_id: str,
        request: SafetyIncidentCreateRequest
    ) -> SafetyIncident:
        """Create a safety incident record."""
        incident = SafetyIncident(
            tenant_id=tenant_id,
            project_id=request.project_id,
            incident_number=self._generate_incident_number(tenant_id, request.project_id),
            incident_date=datetime.strptime(request.incident_date, "%Y-%m-%d").date(),
            incident_time=request.incident_time,
            severity=request.severity,
            injured_person_name=request.injured_person_name,
            injured_person_title=request.injured_person_title,
            injured_person_company_id=request.injured_person_company_id,
            location=request.location,
            description=request.description,
            immediate_cause=request.immediate_cause,
            root_cause=request.root_cause,
            contributing_factors=request.contributing_factors,
            injury_type=request.injury_type,
            body_part_affected=request.body_part_affected,
            treatment_provided=request.treatment_provided,
            reported_by=user_id,
            osha_recordable=request.severity in [IncidentSeverity.MEDICAL_TREATMENT, IncidentSeverity.LOST_TIME, IncidentSeverity.FATALITY]
        )
        
        self.db.add(incident)
        self.db.commit()
        return incident
    
    def create_safety_inspection(
        self,
        tenant_id: str,
        user_id: str,
        request: SafetyInspectionCreateRequest
    ) -> SafetyInspection:
        """Create a safety inspection record."""
        inspection = SafetyInspection(
            tenant_id=tenant_id,
            project_id=request.project_id,
            inspection_type=request.inspection_type,
            inspection_date=datetime.strptime(request.inspection_date, "%Y-%m-%d").date(),
            inspected_by=user_id,
            company_id=request.company_id,
            area_inspected=request.area_inspected
        )
        
        self.db.add(inspection)
        self.db.commit()
        return inspection
    
    def add_finding(
        self,
        tenant_id: str,
        user_id: str,
        request: SafetyFindingCreateRequest
    ) -> SafetyFinding:
        """Add a finding to an inspection."""
        finding = SafetyFinding(
            tenant_id=tenant_id,
            inspection_id=request.inspection_id,
            category=request.category,
            description=request.description,
            severity=request.severity,
            assigned_to=request.assigned_to,
            due_date=datetime.strptime(request.due_date, "%Y-%m-%d").date() if request.due_date else None
        )
        
        self.db.add(finding)
        
        # Update inspection counts
        inspection = self.db.query(SafetyInspection).filter(
            SafetyInspection.tenant_id == tenant_id,
            SafetyInspection.id == request.inspection_id
        ).first()
        
        if inspection:
            inspection.total_items += 1
            inspection.non_compliant_items += 1
        
        self.db.commit()
        return finding
    
    def correct_finding(
        self,
        tenant_id: str,
        finding_id: str,
        user_id: str,
        request: CorrectFindingRequest
    ) -> SafetyFinding:
        """Mark a finding as corrected."""
        finding = self.db.query(SafetyFinding).filter(
            SafetyFinding.tenant_id == tenant_id,
            SafetyFinding.id == finding_id
        ).first()
        
        if not finding:
            raise ValueError("Finding not found")
        
        finding.status = "corrected"
        finding.corrected_by = user_id
        finding.corrected_at = datetime.utcnow()
        finding.correction_notes = request.correction_notes
        finding.photos_after = request.photos_after
        
        # Update inspection counts
        inspection = self.db.query(SafetyInspection).filter(
            SafetyInspection.id == finding.inspection_id
        ).first()
        
        if inspection:
            inspection.non_compliant_items -= 1
            inspection.compliant_items += 1
        
        self.db.commit()
        return finding
    
    def get_safety_meetings(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        meeting_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[SafetyMeeting]:
        """Get safety meetings with filters."""
        query = self.db.query(SafetyMeeting).filter(SafetyMeeting.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(SafetyMeeting.project_id == project_id)
        if company_id:
            query = query.filter(SafetyMeeting.company_id == company_id)
        if meeting_type:
            query = query.filter(SafetyMeeting.meeting_type == meeting_type)
        if start_date:
            query = query.filter(SafetyMeeting.meeting_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
        if end_date:
            query = query.filter(SafetyMeeting.meeting_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
        
        return query.order_by(SafetyMeeting.meeting_date.desc()).all()
    
    def get_safety_incidents(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        severity: Optional[str] = None,
        osha_recordable: Optional[bool] = None
    ) -> List[SafetyIncident]:
        """Get safety incidents with filters."""
        query = self.db.query(SafetyIncident).filter(SafetyIncident.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(SafetyIncident.project_id == project_id)
        if company_id:
            query = query.filter(SafetyIncident.injured_person_company_id == company_id)
        if severity:
            query = query.filter(SafetyIncident.severity == severity)
        if osha_recordable is not None:
            query = query.filter(SafetyIncident.osha_recordable == osha_recordable)
        
        return query.order_by(SafetyIncident.incident_date.desc()).all()
    
    def get_osha_summary(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get OSHA summary statistics."""
        query = self.db.query(SafetyIncident).filter(
            SafetyIncident.tenant_id == tenant_id,
            SafetyIncident.osha_recordable == True
        )
        
        if project_id:
            query = query.filter(SafetyIncident.project_id == project_id)
        if year:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            query = query.filter(
                SafetyIncident.incident_date >= start_date,
                SafetyIncident.incident_date <= end_date
            )
        
        incidents = query.all()
        
        total_recordable = len(incidents)
        days_away = sum(i.days_away_from_work or 0 for i in incidents)
        job_transfers = sum(i.days_on_restriction or 0 for i in incidents)
        
        # Calculate TRIR (Total Recordable Incident Rate)
        # Assuming 100 full-time employees for demo
        total_hours = 200000  # 100 employees * 2000 hours
        trir = (total_recordable * 200000) / total_hours if total_hours > 0 else 0
        
        return {
            "total_recordable_cases": total_recordable,
            "days_away_cases": sum(1 for i in incidents if i.days_away_from_work and i.days_away_from_work > 0),
            "job_transfer_cases": sum(1 for i in incidents if i.days_on_restriction and i.days_on_restriction > 0),
            "other_recordable_cases": total_recordable - sum(1 for i in incidents if (i.days_away_from_work and i.days_away_from_work > 0) or (i.days_on_restriction and i.days_on_restriction > 0)),
            "total_days_away": days_away,
            "total_job_transfers": job_transfers,
            "trir": round(trir, 2),
            "dart": round((sum(1 for i in incidents if (i.days_away_from_work and i.days_away_from_work > 0) or (i.days_on_restriction and i.days_on_restriction > 0)) * 200000) / total_hours, 2) if total_hours > 0 else 0
        }
    
    def get_safety_scorecard(
        self,
        tenant_id: str,
        project_id: str,
        company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get safety scorecard for project or company."""
        # Get meetings
        meetings_query = self.db.query(SafetyMeeting).filter(
            SafetyMeeting.tenant_id == tenant_id,
            SafetyMeeting.project_id == project_id
        )
        
        # Get incidents
        incidents_query = self.db.query(SafetyIncident).filter(
            SafetyIncident.tenant_id == tenant_id,
            SafetyIncident.project_id == project_id
        )
        
        # Get inspections
        inspections_query = self.db.query(SafetyInspection).filter(
            SafetyInspection.tenant_id == tenant_id,
            SafetyInspection.project_id == project_id
        )
        
        if company_id:
            meetings_query = meetings_query.filter(SafetyMeeting.company_id == company_id)
            incidents_query = incidents_query.filter(SafetyIncident.injured_person_company_id == company_id)
            inspections_query = inspections_query.filter(SafetyInspection.company_id == company_id)
        
        meetings = meetings_query.all()
        incidents = incidents_query.all()
        inspections = inspections_query.all()
        
        # Calculate metrics
        toolbox_talks = len([m for m in meetings if m.meeting_type == SafetyMeetingType.TOOLBOX_TALK])
        total_attendees = sum(m.attendee_count for m in meetings)
        
        recordable_incidents = len([i for i in incidents if i.osha_recordable])
        near_misses = len([i for i in incidents if i.severity == IncidentSeverity.NEAR_MISS])
        
        total_inspection_items = sum(i.total_items for i in inspections)
        non_compliant_items = sum(i.non_compliant_items for i in inspections)
        compliance_rate = ((total_inspection_items - non_compliant_items) / total_inspection_items * 100) if total_inspection_items > 0 else 100
        
        return {
            "meetings_conducted": len(meetings),
            "toolbox_talks": toolbox_talks,
            "total_attendees": total_attendees,
            "incidents": len(incidents),
            "recordable_incidents": recordable_incidents,
            "near_misses": near_misses,
            "inspections": len(inspections),
            "compliance_rate": round(compliance_rate, 1),
            "safety_score": self._calculate_safety_score(compliance_rate, recordable_incidents, len(meetings))
        }
    
    def _calculate_safety_score(
        self,
        compliance_rate: float,
        recordable_incidents: int,
        meetings_conducted: int
    ) -> int:
        """Calculate overall safety score (0-100)."""
        score = 100
        
        # Deduct for compliance issues
        score -= (100 - compliance_rate) * 0.5
        
        # Deduct for incidents
        score -= recordable_incidents * 10
        
        # Bonus for meetings
        score += min(meetings_conducted * 2, 10)
        
        return max(0, min(100, int(score)))
