"""
RFI (Request for Information) Module
Handles RFI submission, routing, and response workflow.
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


class RFIStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    OPEN = "open"
    IN_REVIEW = "in_review"
    ANSWERED = "answered"
    CLOSED = "closed"
    VOID = "void"


class RFIType(str, Enum):
    CLARIFICATION = "clarification"
    CONFLICT = "conflict"
    OMISSION = "omission"
    DESIGN_CHANGE = "design_change"
    COORDINATION = "coordination"
    MATERIAL_SUBSTITUTION = "material_substitution"
    SITE_CONDITION = "site_condition"
    OTHER = "other"


class RFI(Base):
    """Request for Information record."""
    __tablename__ = 'rfis'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    rfi_number = Column(String(100), nullable=False)
    subject = Column(String(500), nullable=False)
    question = Column(Text, nullable=False)
    rfi_type = Column(String(50), default=RFIType.CLARIFICATION)
    
    specification_section = Column(String(50))
    drawing_number = Column(String(100))
    detail_reference = Column(String(100))
    
    submitted_by_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    submitted_by_user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    submitted_at = Column(DateTime)
    
    assigned_to_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    status = Column(String(50), default=RFIStatus.DRAFT)
    priority = Column(String(50), default="normal")
    
    suggested_answer = Column(Text)
    official_answer = Column(Text)
    answered_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    answered_at = Column(DateTime)
    
    due_date = Column(DateTime)
    answered_date = Column(DateTime)
    
    cost_impact = Column(String(50))  # yes, no, unknown
    schedule_impact = Column(String(50))  # yes, no, unknown
    
    attachments = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = relationship("RFIHistory", back_populates="rfi")


class RFIHistory(Base):
    """RFI status change history."""
    __tablename__ = 'rfi_history'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    rfi_id = Column(PG_UUID(as_uuid=True), ForeignKey('rfis.id'), nullable=False)
    
    action = Column(String(100), nullable=False)
    from_status = Column(String(50))
    to_status = Column(String(50))
    
    performed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    performed_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    
    # Relationships
    rfi = relationship("RFI", back_populates="history")


# Pydantic Models

class RFIAttachment(BaseModel):
    file_url: str
    file_name: str
    file_size: int
    file_type: str


class RFICreateRequest(BaseModel):
    project_id: str
    subject: str
    question: str
    rfi_type: RFIType = RFIType.CLARIFICATION
    specification_section: Optional[str] = None
    drawing_number: Optional[str] = None
    detail_reference: Optional[str] = None
    priority: str = "normal"
    suggested_answer: Optional[str] = None
    due_date: Optional[datetime] = None
    attachments: List[RFIAttachment] = []


class RFIUpdateRequest(BaseModel):
    subject: Optional[str] = None
    question: Optional[str] = None
    rfi_type: Optional[RFIType] = None
    priority: Optional[str] = None
    suggested_answer: Optional[str] = None
    due_date: Optional[datetime] = None


class SubmitRFIRequest(BaseModel):
    assign_to_user_id: Optional[str] = None


class AnswerRFIRequest(BaseModel):
    official_answer: str
    cost_impact: str = "no"  # yes, no, unknown
    schedule_impact: str = "no"  # yes, no, unknown


class RFIRoutingRule(BaseModel):
    """Rule for auto-routing RFIs based on criteria."""
    id: str
    name: str
    rfi_type: Optional[str] = None
    specification_section: Optional[str] = None
    assign_to_user_id: str
    priority: str = "normal"
    is_active: bool = True


class RFIResponse(BaseModel):
    id: str
    rfi_number: str
    subject: str
    question: str
    rfi_type: str
    specification_section: Optional[str]
    drawing_number: Optional[str]
    detail_reference: Optional[str]
    submitted_by_company_id: Optional[str]
    submitted_by_company_name: Optional[str]
    submitted_by_user_name: Optional[str]
    submitted_at: Optional[datetime]
    assigned_to_id: Optional[str]
    assigned_to_name: Optional[str]
    status: str
    priority: str
    suggested_answer: Optional[str]
    official_answer: Optional[str]
    answered_by: Optional[str]
    answered_by_name: Optional[str]
    answered_at: Optional[datetime]
    due_date: Optional[datetime]
    cost_impact: Optional[str]
    schedule_impact: Optional[str]
    attachments: List[Dict[str, Any]]
    days_open: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RFIHistoryResponse(BaseModel):
    id: str
    action: str
    from_status: Optional[str]
    to_status: Optional[str]
    performed_by: str
    performed_by_name: str
    performed_at: datetime
    notes: Optional[str]
    
    class Config:
        from_attributes = True


class RFIService:
    """Service for managing RFIs."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def _generate_rfi_number(self, tenant_id: str, project_id: str) -> str:
        """Generate unique RFI number."""
        count = self.db.query(RFI).filter(
            RFI.tenant_id == tenant_id,
            RFI.project_id == project_id
        ).count()
        return f"RFI-{count + 1:04d}"
    
    def _add_history(
        self,
        tenant_id: str,
        rfi_id: str,
        action: str,
        from_status: Optional[str],
        to_status: Optional[str],
        user_id: str,
        notes: Optional[str] = None
    ):
        """Add RFI history entry."""
        history = RFIHistory(
            tenant_id=tenant_id,
            rfi_id=rfi_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            performed_by=user_id,
            notes=notes
        )
        self.db.add(history)
    
    def create_rfi(
        self,
        tenant_id: str,
        user_id: str,
        company_id: Optional[str],
        request: RFICreateRequest
    ) -> RFI:
        """Create a new RFI."""
        rfi = RFI(
            tenant_id=tenant_id,
            project_id=request.project_id,
            rfi_number=self._generate_rfi_number(tenant_id, request.project_id),
            subject=request.subject,
            question=request.question,
            rfi_type=request.rfi_type,
            specification_section=request.specification_section,
            drawing_number=request.drawing_number,
            detail_reference=request.detail_reference,
            submitted_by_company_id=company_id,
            submitted_by_user_id=user_id,
            priority=request.priority,
            suggested_answer=request.suggested_answer,
            due_date=request.due_date,
            attachments=[a.dict() for a in request.attachments]
        )
        
        self.db.add(rfi)
        self.db.flush()
        
        self._add_history(
            tenant_id, rfi.id, "RFI Created",
            None, RFIStatus.DRAFT, user_id
        )
        
        self.db.commit()
        return rfi
    
    def submit_rfi(
        self,
        tenant_id: str,
        rfi_id: str,
        user_id: str,
        request: SubmitRFIRequest
    ) -> RFI:
        """Submit RFI for review."""
        rfi = self.db.query(RFI).filter(
            RFI.tenant_id == tenant_id,
            RFI.id == rfi_id
        ).first()
        
        if not rfi:
            raise ValueError("RFI not found")
        
        if rfi.status != RFIStatus.DRAFT:
            raise ValueError("RFI can only be submitted from draft status")
        
        old_status = rfi.status
        rfi.status = RFIStatus.OPEN
        rfi.submitted_at = datetime.utcnow()
        
        if request.assign_to_user_id:
            rfi.assigned_to_id = request.assign_to_user_id
        
        self._add_history(
            tenant_id, rfi.id, "RFI Submitted",
            old_status, rfi.status, user_id
        )
        
        self.db.commit()
        return rfi
    
    def answer_rfi(
        self,
        tenant_id: str,
        rfi_id: str,
        user_id: str,
        request: AnswerRFIRequest
    ) -> RFI:
        """Answer an RFI."""
        rfi = self.db.query(RFI).filter(
            RFI.tenant_id == tenant_id,
            RFI.id == rfi_id
        ).first()
        
        if not rfi:
            raise ValueError("RFI not found")
        
        if rfi.status not in [RFIStatus.OPEN, RFIStatus.IN_REVIEW]:
            raise ValueError("RFI must be open to answer")
        
        old_status = rfi.status
        rfi.official_answer = request.official_answer
        rfi.answered_by = user_id
        rfi.answered_at = datetime.utcnow()
        rfi.answered_date = datetime.utcnow()
        rfi.cost_impact = request.cost_impact
        rfi.schedule_impact = request.schedule_impact
        rfi.status = RFIStatus.ANSWERED
        
        self._add_history(
            tenant_id, rfi.id, "RFI Answered",
            old_status, rfi.status, user_id,
            f"Cost Impact: {request.cost_impact}, Schedule Impact: {request.schedule_impact}"
        )
        
        self.db.commit()
        return rfi
    
    def close_rfi(
        self,
        tenant_id: str,
        rfi_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> RFI:
        """Close an RFI."""
        rfi = self.db.query(RFI).filter(
            RFI.tenant_id == tenant_id,
            RFI.id == rfi_id
        ).first()
        
        if not rfi:
            raise ValueError("RFI not found")
        
        old_status = rfi.status
        rfi.status = RFIStatus.CLOSED
        
        self._add_history(
            tenant_id, rfi.id, "RFI Closed",
            old_status, rfi.status, user_id, notes
        )
        
        self.db.commit()
        return rfi
    
    def assign_rfi(
        self,
        tenant_id: str,
        rfi_id: str,
        assign_to_user_id: str,
        assigned_by_user_id: str
    ) -> RFI:
        """Assign RFI to a user."""
        rfi = self.db.query(RFI).filter(
            RFI.tenant_id == tenant_id,
            RFI.id == rfi_id
        ).first()
        
        if not rfi:
            raise ValueError("RFI not found")
        
        rfi.assigned_to_id = assign_to_user_id
        
        if rfi.status == RFIStatus.OPEN:
            old_status = rfi.status
            rfi.status = RFIStatus.IN_REVIEW
            
            self._add_history(
                tenant_id, rfi.id, "RFI Assigned",
                old_status, rfi.status, assigned_by_user_id,
                f"Assigned to user: {assign_to_user_id}"
            )
        
        self.db.commit()
        return rfi
    
    def get_rfi(
        self,
        tenant_id: str,
        rfi_id: str
    ) -> Dict[str, Any]:
        """Get RFI with history."""
        rfi = self.db.query(RFI).filter(
            RFI.tenant_id == tenant_id,
            RFI.id == rfi_id
        ).first()
        
        if not rfi:
            raise ValueError("RFI not found")
        
        history = self.db.query(RFIHistory).filter(
            RFIHistory.rfi_id == rfi_id
        ).order_by(RFIHistory.performed_at).all()
        
        return {
            "rfi": rfi,
            "history": history
        }
    
    def get_rfis(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        overdue_only: bool = False
    ) -> List[RFI]:
        """Get RFIs with filters."""
        query = self.db.query(RFI).filter(RFI.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(RFI.project_id == project_id)
        if company_id:
            query = query.filter(RFI.submitted_by_company_id == company_id)
        if status:
            query = query.filter(RFI.status == status)
        if assigned_to:
            query = query.filter(RFI.assigned_to_id == assigned_to)
        if overdue_only:
            query = query.filter(
                RFI.due_date < datetime.utcnow(),
                RFI.status.notin_([RFIStatus.ANSWERED, RFIStatus.CLOSED])
            )
        
        return query.order_by(RFI.created_at.desc()).all()
    
    def get_open_rfi_count(
        self,
        tenant_id: str,
        project_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get count of open RFIs."""
        query = self.db.query(RFI).filter(
            RFI.tenant_id == tenant_id,
            RFI.status.in_([RFIStatus.OPEN, RFIStatus.IN_REVIEW])
        )
        
        if project_id:
            query = query.filter(RFI.project_id == project_id)
        
        total_open = query.count()
        overdue = query.filter(RFI.due_date < datetime.utcnow()).count()
        
        return {
            "total_open": total_open,
            "overdue": overdue
        }
