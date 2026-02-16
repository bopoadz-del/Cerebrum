"""
Submittals Module
Handles submittal upload, review, and approval workflow.
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


class SubmittalStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    REVISION_REQUIRED = "revision_required"
    APPROVED = "approved"
    APPROVED_AS_NOTED = "approved_as_noted"
    REJECTED = "rejected"
    VOID = "void"


class SubmittalType(str, Enum):
    PRODUCT_DATA = "product_data"
    SHOP_DRAWINGS = "shop_drawings"
    SAMPLES = "samples"
    MOCKUPS = "mockups"
    TEST_REPORTS = "test_reports"
    CERTIFICATES = "certificates"
    MSDS = "msds"
    O_AND_M = "o_and_m"
    WARRANTIES = "warranties"
    CLOSEOUT = "closeout"


class SubmittalPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Submittal(Base):
    """Submittal record."""
    __tablename__ = 'submittals'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    submittal_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    submittal_type = Column(String(50), nullable=False)
    
    specification_section = Column(String(50))
    specification_paragraph = Column(String(50))
    
    submitted_by_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    submitted_by_user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    submitted_at = Column(DateTime)
    
    priority = Column(String(50), default=SubmittalPriority.NORMAL)
    status = Column(String(50), default=SubmittalStatus.DRAFT)
    
    required_approval_date = Column(DateTime)
    actual_approval_date = Column(DateTime)
    
    review_assignee_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    attachments = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    revisions = relationship("SubmittalRevision", back_populates="submittal")
    reviews = relationship("SubmittalReview", back_populates="submittal")


class SubmittalRevision(Base):
    """Submittal revision tracking."""
    __tablename__ = 'submittal_revisions'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    submittal_id = Column(PG_UUID(as_uuid=True), ForeignKey('submittals.id'), nullable=False)
    
    revision_number = Column(Integer, nullable=False)
    description = Column(Text)
    
    file_url = Column(String(1000))
    file_name = Column(String(500))
    file_size = Column(Integer)
    
    submitted_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submittal = relationship("Submittal", back_populates="revisions")


class SubmittalReview(Base):
    """Submittal review record."""
    __tablename__ = 'submittal_reviews'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    submittal_id = Column(PG_UUID(as_uuid=True), ForeignKey('submittals.id'), nullable=False)
    revision_id = Column(PG_UUID(as_uuid=True), ForeignKey('submittal_revisions.id'))
    
    reviewer_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    
    action = Column(String(50))  # approved, approved_as_noted, revision_required, rejected
    comments = Column(Text)
    
    distribution_list = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submittal = relationship("Submittal", back_populates="reviews")


# Pydantic Models

class SubmittalAttachment(BaseModel):
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    description: Optional[str] = None


class SubmittalCreateRequest(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    submittal_type: SubmittalType
    specification_section: Optional[str] = None
    specification_paragraph: Optional[str] = None
    priority: SubmittalPriority = SubmittalPriority.NORMAL
    required_approval_date: Optional[datetime] = None
    attachments: List[SubmittalAttachment] = []


class SubmittalUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[SubmittalPriority] = None
    required_approval_date: Optional[datetime] = None


class SubmitSubmittalRequest(BaseModel):
    notes: Optional[str] = None


class ReviewSubmittalRequest(BaseModel):
    action: str  # approved, approved_as_noted, revision_required, rejected
    comments: Optional[str] = None
    distribution_list: Optional[List[str]] = None


class SubmittalRevisionCreateRequest(BaseModel):
    description: str
    file_url: str
    file_name: str
    file_size: int


class SubmittalResponse(BaseModel):
    id: str
    submittal_number: str
    title: str
    description: Optional[str]
    submittal_type: str
    specification_section: Optional[str]
    specification_paragraph: Optional[str]
    submitted_by_company_id: Optional[str]
    submitted_by_company_name: Optional[str]
    priority: str
    status: str
    required_approval_date: Optional[datetime]
    actual_approval_date: Optional[datetime]
    review_assignee_id: Optional[str]
    review_assignee_name: Optional[str]
    revision_count: int
    attachments: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SubmittalRevisionResponse(BaseModel):
    id: str
    revision_number: int
    description: Optional[str]
    file_url: str
    file_name: str
    file_size: int
    submitted_by: Optional[str]
    submitted_at: datetime
    
    class Config:
        from_attributes = True


class SubmittalReviewResponse(BaseModel):
    id: str
    reviewer_id: str
    reviewer_name: str
    reviewed_at: datetime
    action: str
    comments: Optional[str]
    
    class Config:
        from_attributes = True


class SubmittalService:
    """Service for managing submittals."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def _generate_submittal_number(self, tenant_id: str, project_id: str) -> str:
        """Generate unique submittal number."""
        count = self.db.query(Submittal).filter(
            Submittal.tenant_id == tenant_id,
            Submittal.project_id == project_id
        ).count()
        return f"SUB-{count + 1:05d}"
    
    def create_submittal(
        self,
        tenant_id: str,
        user_id: str,
        company_id: Optional[str],
        request: SubmittalCreateRequest
    ) -> Submittal:
        """Create a new submittal."""
        submittal = Submittal(
            tenant_id=tenant_id,
            project_id=request.project_id,
            submittal_number=self._generate_submittal_number(tenant_id, request.project_id),
            title=request.title,
            description=request.description,
            submittal_type=request.submittal_type,
            specification_section=request.specification_section,
            specification_paragraph=request.specification_paragraph,
            submitted_by_company_id=company_id,
            submitted_by_user_id=user_id,
            priority=request.priority,
            required_approval_date=request.required_approval_date,
            attachments=[a.dict() for a in request.attachments]
        )
        
        self.db.add(submittal)
        self.db.commit()
        return submittal
    
    def submit_submittal(
        self,
        tenant_id: str,
        submittal_id: str,
        user_id: str,
        request: SubmitSubmittalRequest
    ) -> Submittal:
        """Submit submittal for review."""
        submittal = self.db.query(Submittal).filter(
            Submittal.tenant_id == tenant_id,
            Submittal.id == submittal_id
        ).first()
        
        if not submittal:
            raise ValueError("Submittal not found")
        
        if submittal.status != SubmittalStatus.DRAFT:
            raise ValueError("Submittal can only be submitted from draft status")
        
        submittal.status = SubmittalStatus.SUBMITTED
        submittal.submitted_at = datetime.utcnow()
        
        # Create initial revision
        revision = SubmittalRevision(
            tenant_id=tenant_id,
            submittal_id=submittal.id,
            revision_number=1,
            description=request.notes,
            submitted_by=user_id
        )
        
        if submittal.attachments:
            revision.file_url = submittal.attachments[0].get('file_url')
            revision.file_name = submittal.attachments[0].get('file_name')
            revision.file_size = submittal.attachments[0].get('file_size')
        
        self.db.add(revision)
        self.db.commit()
        return submittal
    
    def review_submittal(
        self,
        tenant_id: str,
        submittal_id: str,
        reviewer_id: str,
        request: ReviewSubmittalRequest
    ) -> SubmittalReview:
        """Review a submittal."""
        submittal = self.db.query(Submittal).filter(
            Submittal.tenant_id == tenant_id,
            Submittal.id == submittal_id
        ).first()
        
        if not submittal:
            raise ValueError("Submittal not found")
        
        # Create review record
        review = SubmittalReview(
            tenant_id=tenant_id,
            submittal_id=submittal.id,
            reviewer_id=reviewer_id,
            reviewed_at=datetime.utcnow(),
            action=request.action,
            comments=request.comments,
            distribution_list=request.distribution_list or []
        )
        
        # Update submittal status
        status_map = {
            "approved": SubmittalStatus.APPROVED,
            "approved_as_noted": SubmittalStatus.APPROVED_AS_NOTED,
            "revision_required": SubmittalStatus.REVISION_REQUIRED,
            "rejected": SubmittalStatus.REJECTED
        }
        
        submittal.status = status_map.get(request.action, SubmittalStatus.UNDER_REVIEW)
        
        if request.action in ["approved", "approved_as_noted"]:
            submittal.actual_approval_date = datetime.utcnow()
        
        self.db.add(review)
        self.db.commit()
        return review
    
    def create_revision(
        self,
        tenant_id: str,
        submittal_id: str,
        user_id: str,
        request: SubmittalRevisionCreateRequest
    ) -> SubmittalRevision:
        """Create a new revision of a submittal."""
        submittal = self.db.query(Submittal).filter(
            Submittal.tenant_id == tenant_id,
            Submittal.id == submittal_id
        ).first()
        
        if not submittal:
            raise ValueError("Submittal not found")
        
        # Get current revision count
        revision_count = self.db.query(SubmittalRevision).filter(
            SubmittalRevision.submittal_id == submittal_id
        ).count()
        
        revision = SubmittalRevision(
            tenant_id=tenant_id,
            submittal_id=submittal_id,
            revision_number=revision_count + 1,
            description=request.description,
            file_url=request.file_url,
            file_name=request.file_name,
            file_size=request.file_size,
            submitted_by=user_id
        )
        
        submittal.status = SubmittalStatus.SUBMITTED
        
        self.db.add(revision)
        self.db.commit()
        return revision
    
    def get_submittals(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status: Optional[str] = None,
        submittal_type: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Submittal]:
        """Get submittals with filters."""
        query = self.db.query(Submittal).filter(Submittal.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(Submittal.project_id == project_id)
        if company_id:
            query = query.filter(Submittal.submitted_by_company_id == company_id)
        if status:
            query = query.filter(Submittal.status == status)
        if submittal_type:
            query = query.filter(Submittal.submittal_type == submittal_type)
        if priority:
            query = query.filter(Submittal.priority == priority)
        
        return query.order_by(Submittal.created_at.desc()).all()
    
    def get_submittal_detail(
        self,
        tenant_id: str,
        submittal_id: str
    ) -> Dict[str, Any]:
        """Get detailed submittal information."""
        submittal = self.db.query(Submittal).filter(
            Submittal.tenant_id == tenant_id,
            Submittal.id == submittal_id
        ).first()
        
        if not submittal:
            raise ValueError("Submittal not found")
        
        revisions = self.db.query(SubmittalRevision).filter(
            SubmittalRevision.submittal_id == submittal_id
        ).order_by(SubmittalRevision.revision_number).all()
        
        reviews = self.db.query(SubmittalReview).filter(
            SubmittalReview.submittal_id == submittal_id
        ).order_by(SubmittalReview.reviewed_at.desc()).all()
        
        return {
            "submittal": submittal,
            "revisions": revisions,
            "reviews": reviews
        }
    
    def get_pending_reviews(
        self,
        tenant_id: str,
        reviewer_id: Optional[str] = None
    ) -> List[Submittal]:
        """Get submittals pending review."""
        query = self.db.query(Submittal).filter(
            Submittal.tenant_id == tenant_id,
            Submittal.status.in_([SubmittalStatus.SUBMITTED, SubmittalStatus.UNDER_REVIEW])
        )
        
        if reviewer_id:
            query = query.filter(Submittal.review_assignee_id == reviewer_id)
        
        return query.order_by(Submittal.required_approval_date).all()
    
    def get_overdue_submittals(
        self,
        tenant_id: str,
        project_id: Optional[str] = None
    ) -> List[Submittal]:
        """Get submittals past their required approval date."""
        query = self.db.query(Submittal).filter(
            Submittal.tenant_id == tenant_id,
            Submittal.required_approval_date < datetime.utcnow(),
            Submittal.status.notin_([SubmittalStatus.APPROVED, SubmittalStatus.APPROVED_AS_NOTED, SubmittalStatus.REJECTED])
        )
        
        if project_id:
            query = query.filter(Submittal.project_id == project_id)
        
        return query.order_by(Submittal.required_approval_date).all()
