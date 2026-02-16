"""
Quality Control Module
Handles inspection checklists, punch lists, and quality documentation.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class InspectionStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PASSED = "passed"


class PunchListStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


class PunchListPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InspectionChecklist(Base):
    """Quality inspection checklist template."""
    __tablename__ = 'inspection_checklists'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # concrete, steel, electrical, etc.
    
    items = Column(JSONB, default=list)  # List of checklist items
    
    is_template = Column(Boolean, default=False)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Inspection(Base):
    """Quality inspection record."""
    __tablename__ = 'quality_inspections'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    inspection_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    checklist_id = Column(PG_UUID(as_uuid=True), ForeignKey('inspection_checklists.id'))
    category = Column(String(100))
    
    inspection_date = Column(DateTime)
    inspected_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    location = Column(String(500))
    specification_section = Column(String(50))
    drawing_reference = Column(String(100))
    
    results = Column(JSONB, default=list)  # Checklist item results
    
    total_items = Column(Integer, default=0)
    passed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    status = Column(String(50), default=InspectionStatus.SCHEDULED)
    
    notes = Column(Text)
    attachments = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PunchListItem(Base):
    """Punch list item."""
    __tablename__ = 'punch_list_items'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    item_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    location = Column(String(500))
    specification_section = Column(String(50))
    drawing_reference = Column(String(100))
    
    assigned_to_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    assigned_to_user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    priority = Column(String(50), default=PunchListPriority.MEDIUM)
    status = Column(String(50), default=PunchListStatus.OPEN)
    
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    completed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    verified_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    verified_at = Column(DateTime)
    
    photos_before = Column(JSONB, default=list)
    photos_after = Column(JSONB, default=list)
    
    cost_impact = Column(String(50))  # yes, no
    estimated_cost = Column(Integer)  # cents
    
    notes = Column(Text)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DefectReport(Base):
    """Quality defect report."""
    __tablename__ = 'defect_reports'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    report_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    defect_type = Column(String(100))  # workmanship, material, design, other
    severity = Column(String(50))  # minor, major, critical
    
    reported_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    reported_at = Column(DateTime, default=datetime.utcnow)
    
    location = Column(String(500))
    
    root_cause = Column(Text)
    corrective_action = Column(Text)
    
    assigned_to = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    due_date = Column(DateTime)
    
    status = Column(String(50), default="open")
    
    resolved_at = Column(DateTime)
    resolved_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    photos = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models

class ChecklistItem(BaseModel):
    id: str
    description: str
    required: bool = True
    category: Optional[str] = None


class ChecklistCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    items: List[ChecklistItem]
    is_template: bool = False


class InspectionResult(BaseModel):
    item_id: str
    description: str
    result: str  # pass, fail, na
    notes: Optional[str] = None
    photos: List[str] = []


class InspectionCreateRequest(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    checklist_id: Optional[str] = None
    category: Optional[str] = None
    company_id: Optional[str] = None
    location: Optional[str] = None
    specification_section: Optional[str] = None
    drawing_reference: Optional[str] = None
    inspection_date: Optional[str] = None


class CompleteInspectionRequest(BaseModel):
    results: List[InspectionResult]
    notes: Optional[str] = None


class PunchListCreateRequest(BaseModel):
    project_id: str
    title: str
    description: str
    location: Optional[str] = None
    specification_section: Optional[str] = None
    drawing_reference: Optional[str] = None
    assigned_to_company_id: Optional[str] = None
    priority: PunchListPriority = PunchListPriority.MEDIUM
    due_date: Optional[str] = None
    photos_before: List[str] = []


class PunchListUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PunchListPriority] = None
    due_date: Optional[str] = None
    assigned_to_company_id: Optional[str] = None


class CompletePunchItemRequest(BaseModel):
    notes: Optional[str] = None
    photos_after: List[str] = []


class DefectReportCreateRequest(BaseModel):
    project_id: str
    title: str
    description: str
    defect_type: str
    severity: str
    location: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    due_date: Optional[str] = None
    photos: List[str] = []


class InspectionResponse(BaseModel):
    id: str
    inspection_number: str
    title: str
    description: Optional[str]
    category: Optional[str]
    inspection_date: Optional[datetime]
    inspected_by: Optional[str]
    inspected_by_name: Optional[str]
    company_id: Optional[str]
    company_name: Optional[str]
    location: Optional[str]
    total_items: int
    passed_items: int
    failed_items: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class PunchListResponse(BaseModel):
    id: str
    item_number: str
    title: str
    description: str
    location: Optional[str]
    assigned_to_company_id: Optional[str]
    assigned_to_company_name: Optional[str]
    priority: str
    status: str
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    verified_at: Optional[datetime]
    days_open: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class DefectReportResponse(BaseModel):
    id: str
    report_number: str
    title: str
    description: str
    defect_type: str
    severity: str
    reported_by: Optional[str]
    reported_by_name: Optional[str]
    location: Optional[str]
    status: str
    due_date: Optional[datetime]
    resolved_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class QualityControlService:
    """Service for quality control management."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def _generate_inspection_number(self, tenant_id: str, project_id: str) -> str:
        """Generate unique inspection number."""
        count = self.db.query(Inspection).filter(
            Inspection.tenant_id == tenant_id,
            Inspection.project_id == project_id
        ).count()
        return f"INSP-{count + 1:05d}"
    
    def _generate_punch_item_number(self, tenant_id: str, project_id: str) -> str:
        """Generate unique punch item number."""
        count = self.db.query(PunchListItem).filter(
            PunchListItem.tenant_id == tenant_id,
            PunchListItem.project_id == project_id
        ).count()
        return f"PL-{count + 1:04d}"
    
    def _generate_defect_number(self, tenant_id: str, project_id: str) -> str:
        """Generate unique defect report number."""
        count = self.db.query(DefectReport).filter(
            DefectReport.tenant_id == tenant_id,
            DefectReport.project_id == project_id
        ).count()
        return f"DEF-{count + 1:04d}"
    
    def create_checklist(
        self,
        tenant_id: str,
        user_id: str,
        request: ChecklistCreateRequest
    ) -> InspectionChecklist:
        """Create an inspection checklist."""
        checklist = InspectionChecklist(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            category=request.category,
            items=[item.dict() for item in request.items],
            is_template=request.is_template,
            created_by=user_id
        )
        
        self.db.add(checklist)
        self.db.commit()
        return checklist
    
    def create_inspection(
        self,
        tenant_id: str,
        user_id: str,
        request: InspectionCreateRequest
    ) -> Inspection:
        """Create a quality inspection."""
        inspection = Inspection(
            tenant_id=tenant_id,
            project_id=request.project_id,
            inspection_number=self._generate_inspection_number(tenant_id, request.project_id),
            title=request.title,
            description=request.description,
            checklist_id=request.checklist_id,
            category=request.category,
            inspected_by=user_id,
            company_id=request.company_id,
            location=request.location,
            specification_section=request.specification_section,
            drawing_reference=request.drawing_reference,
            inspection_date=datetime.strptime(request.inspection_date, "%Y-%m-%d") if request.inspection_date else None
        )
        
        # Load checklist items if provided
        if request.checklist_id:
            checklist = self.db.query(InspectionChecklist).filter(
                InspectionChecklist.tenant_id == tenant_id,
                InspectionChecklist.id == request.checklist_id
            ).first()
            
            if checklist:
                inspection.total_items = len(checklist.items)
        
        self.db.add(inspection)
        self.db.commit()
        return inspection
    
    def complete_inspection(
        self,
        tenant_id: str,
        inspection_id: str,
        user_id: str,
        request: CompleteInspectionRequest
    ) -> Inspection:
        """Complete an inspection with results."""
        inspection = self.db.query(Inspection).filter(
            Inspection.tenant_id == tenant_id,
            Inspection.id == inspection_id
        ).first()
        
        if not inspection:
            raise ValueError("Inspection not found")
        
        passed = sum(1 for r in request.results if r.result == "pass")
        failed = sum(1 for r in request.results if r.result == "fail")
        
        inspection.results = [r.dict() for r in request.results]
        inspection.passed_items = passed
        inspection.failed_items = failed
        inspection.total_items = len(request.results)
        inspection.status = InspectionStatus.PASSED if failed == 0 else InspectionStatus.FAILED
        inspection.notes = request.notes
        inspection.inspection_date = datetime.utcnow()
        
        self.db.commit()
        return inspection
    
    def create_punch_item(
        self,
        tenant_id: str,
        user_id: str,
        request: PunchListCreateRequest
    ) -> PunchListItem:
        """Create a punch list item."""
        item = PunchListItem(
            tenant_id=tenant_id,
            project_id=request.project_id,
            item_number=self._generate_punch_item_number(tenant_id, request.project_id),
            title=request.title,
            description=request.description,
            location=request.location,
            specification_section=request.specification_section,
            drawing_reference=request.drawing_reference,
            assigned_to_company_id=request.assigned_to_company_id,
            priority=request.priority,
            due_date=datetime.strptime(request.due_date, "%Y-%m-%d") if request.due_date else None,
            created_by=user_id,
            photos_before=request.photos_before
        )
        
        self.db.add(item)
        self.db.commit()
        return item
    
    def complete_punch_item(
        self,
        tenant_id: str,
        item_id: str,
        user_id: str,
        request: CompletePunchItemRequest
    ) -> PunchListItem:
        """Mark punch item as complete."""
        item = self.db.query(PunchListItem).filter(
            PunchListItem.tenant_id == tenant_id,
            PunchListItem.id == item_id
        ).first()
        
        if not item:
            raise ValueError("Punch item not found")
        
        item.status = PunchListStatus.READY_FOR_REVIEW
        item.completed_at = datetime.utcnow()
        item.completed_by = user_id
        item.photos_after = request.photos_after
        item.notes = request.notes
        
        self.db.commit()
        return item
    
    def verify_punch_item(
        self,
        tenant_id: str,
        item_id: str,
        user_id: str,
        approved: bool,
        notes: Optional[str] = None
    ) -> PunchListItem:
        """Verify a completed punch item."""
        item = self.db.query(PunchListItem).filter(
            PunchListItem.tenant_id == tenant_id,
            PunchListItem.id == item_id
        ).first()
        
        if not item:
            raise ValueError("Punch item not found")
        
        item.verified_by = user_id
        item.verified_at = datetime.utcnow()
        item.status = PunchListStatus.CLOSED if approved else PunchListStatus.OPEN
        
        if notes:
            item.notes = f"{item.notes or ''}\n\nVerification Notes: {notes}"
        
        self.db.commit()
        return item
    
    def create_defect_report(
        self,
        tenant_id: str,
        user_id: str,
        request: DefectReportCreateRequest
    ) -> DefectReport:
        """Create a defect report."""
        report = DefectReport(
            tenant_id=tenant_id,
            project_id=request.project_id,
            report_number=self._generate_defect_number(tenant_id, request.project_id),
            title=request.title,
            description=request.description,
            defect_type=request.defect_type,
            severity=request.severity,
            reported_by=user_id,
            location=request.location,
            root_cause=request.root_cause,
            corrective_action=request.corrective_action,
            due_date=datetime.strptime(request.due_date, "%Y-%m-%d") if request.due_date else None,
            photos=request.photos
        )
        
        self.db.add(report)
        self.db.commit()
        return report
    
    def get_punch_list(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[PunchListItem]:
        """Get punch list items with filters."""
        query = self.db.query(PunchListItem).filter(PunchListItem.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(PunchListItem.project_id == project_id)
        if company_id:
            query = query.filter(PunchListItem.assigned_to_company_id == company_id)
        if status:
            query = query.filter(PunchListItem.status == status)
        if priority:
            query = query.filter(PunchListItem.priority == priority)
        
        return query.order_by(PunchListItem.created_at.desc()).all()
    
    def get_quality_metrics(
        self,
        tenant_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """Get quality metrics for a project."""
        inspections = self.db.query(Inspection).filter(
            Inspection.tenant_id == tenant_id,
            Inspection.project_id == project_id
        ).all()
        
        punch_items = self.db.query(PunchListItem).filter(
            PunchListItem.tenant_id == tenant_id,
            PunchListItem.project_id == project_id
        ).all()
        
        defects = self.db.query(DefectReport).filter(
            DefectReport.tenant_id == tenant_id,
            DefectReport.project_id == project_id
        ).all()
        
        total_inspections = len(inspections)
        passed_inspections = len([i for i in inspections if i.status == InspectionStatus.PASSED])
        
        open_punch = len([p for p in punch_items if p.status in [PunchListStatus.OPEN, PunchListStatus.IN_PROGRESS]])
        closed_punch = len([p for p in punch_items if p.status == PunchListStatus.CLOSED])
        
        open_defects = len([d for d in defects if d.status == "open"])
        critical_defects = len([d for d in defects if d.severity == "critical" and d.status == "open"])
        
        return {
            "inspections": {
                "total": total_inspections,
                "passed": passed_inspections,
                "failed": total_inspections - passed_inspections,
                "pass_rate": round(passed_inspections / total_inspections * 100, 1) if total_inspections > 0 else 0
            },
            "punch_list": {
                "total": len(punch_items),
                "open": open_punch,
                "closed": closed_punch,
                "completion_rate": round(closed_punch / len(punch_items) * 100, 1) if punch_items else 0
            },
            "defects": {
                "total": len(defects),
                "open": open_defects,
                "critical": critical_defects
            },
            "quality_score": self._calculate_quality_score(
                passed_inspections, total_inspections,
                closed_punch, len(punch_items),
                len(defects) - open_defects, len(defects)
            )
        }
    
    def _calculate_quality_score(
        self,
        passed_insp: int, total_insp: int,
        closed_punch: int, total_punch: int,
        resolved_defects: int, total_defects: int
    ) -> int:
        """Calculate overall quality score (0-100)."""
        score = 100
        
        # Inspection pass rate (40% weight)
        if total_insp > 0:
            insp_score = (passed_insp / total_insp) * 40
        else:
            insp_score = 40
        
        # Punch list completion (30% weight)
        if total_punch > 0:
            punch_score = (closed_punch / total_punch) * 30
        else:
            punch_score = 30
        
        # Defect resolution (30% weight)
        if total_defects > 0:
            defect_score = (resolved_defects / total_defects) * 30
        else:
            defect_score = 30
        
        return int(insp_score + punch_score + defect_score)
