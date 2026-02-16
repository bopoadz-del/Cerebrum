"""
Change Orders Module
Handles subcontractor change order request workflow.
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


class CORStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PRICING_REQUESTED = "pricing_requested"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CORType(str, Enum):
    OWNER_DIRECTED = "owner_directed"
    FIELD_CONDITION = "field_condition"
    DESIGN_CHANGE = "design_change"
    OMISSION = "omission"
    ACCELERATION = "acceleration"
    DELAY = "delay"
    OTHER = "other"


class CORPricingStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ChangeOrderRequest(Base):
    """Change order request from subcontractor."""
    __tablename__ = 'change_order_requests'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    cor_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    cor_type = Column(String(100), nullable=False)
    
    submitted_by_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    submitted_by_user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    submitted_at = Column(DateTime)
    
    # Reference information
    rfi_reference_id = Column(PG_UUID(as_uuid=True), ForeignKey('rfis.id'))
    drawing_reference = Column(String(100))
    specification_section = Column(String(50))
    
    # Reason and justification
    reason = Column(Text)
    justification = Column(Text)
    
    # Impact assessment
    cost_impact = Column(Boolean, default=False)
    schedule_impact = Column(Boolean, default=False)
    
    days_impact = Column(Integer, default=0)
    
    status = Column(String(50), default=CORStatus.DRAFT)
    
    reviewed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    
    approved_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    approved_at = Column(DateTime)
    approval_amount = Column(Integer)  # cents
    
    attachments = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pricing = relationship("CORPricing", back_populates="change_order")


class CORPricing(Base):
    """Change order pricing breakdown."""
    __tablename__ = 'cor_pricing'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    cor_id = Column(PG_UUID(as_uuid=True), ForeignKey('change_order_requests.id'), nullable=False)
    
    line_items = Column(JSONB, default=list)  # List of {description, quantity, unit, unit_price}
    
    material_cost = Column(Integer, default=0)  # cents
    labor_cost = Column(Integer, default=0)  # cents
    equipment_cost = Column(Integer, default=0)  # cents
    subcontract_cost = Column(Integer, default=0)  # cents
    overhead_profit = Column(Integer, default=0)  # cents
    bond_insurance = Column(Integer, default=0)  # cents
    
    subtotal = Column(Integer, default=0)  # cents
    tax = Column(Integer, default=0)  # cents
    total = Column(Integer, default=0)  # cents
    
    submitted_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    submitted_at = Column(DateTime)
    
    status = Column(String(50), default=CORPricingStatus.PENDING)
    
    reviewed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    
    # Relationships
    change_order = relationship("ChangeOrderRequest", back_populates="pricing")


class CORNegotiation(Base):
    """Change order negotiation history."""
    __tablename__ = 'cor_negotiations'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    cor_id = Column(PG_UUID(as_uuid=True), ForeignKey('change_order_requests.id'), nullable=False)
    
    proposed_amount = Column(Integer)  # cents
    proposed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    proposed_at = Column(DateTime, default=datetime.utcnow)
    
    counter_amount = Column(Integer)  # cents
    counter_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    counter_at = Column(DateTime)
    
    notes = Column(Text)
    
    status = Column(String(50))  # pending, accepted, rejected


# Pydantic Models

class CORLineItem(BaseModel):
    description: str
    quantity: float
    unit: str
    unit_price: int  # cents
    total: int  # cents


class CORAttachment(BaseModel):
    file_url: str
    file_name: str
    file_type: str
    description: Optional[str] = None


class CORCreateRequest(BaseModel):
    project_id: str
    title: str
    description: str
    cor_type: CORType
    rfi_reference_id: Optional[str] = None
    drawing_reference: Optional[str] = None
    specification_section: Optional[str] = None
    reason: Optional[str] = None
    justification: Optional[str] = None
    cost_impact: bool = False
    schedule_impact: bool = False
    days_impact: int = 0
    attachments: List[CORAttachment] = []


class CORUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    justification: Optional[str] = None


class CORPricingSubmitRequest(BaseModel):
    line_items: List[CORLineItem]
    material_cost: int
    labor_cost: int
    equipment_cost: int
    subcontract_cost: int
    overhead_profit: int
    bond_insurance: int
    tax: int


class CORReviewRequest(BaseModel):
    action: str  # approve, reject, request_pricing, request_revision
    notes: Optional[str] = None
    approval_amount: Optional[int] = None  # cents


class CORResponse(BaseModel):
    id: str
    cor_number: str
    title: str
    description: str
    cor_type: str
    submitted_by_company_id: Optional[str]
    submitted_by_company_name: Optional[str]
    submitted_by_user_name: Optional[str]
    submitted_at: Optional[datetime]
    rfi_reference_id: Optional[str]
    drawing_reference: Optional[str]
    specification_section: Optional[str]
    cost_impact: bool
    schedule_impact: bool
    days_impact: int
    status: str
    total_pricing: Optional[int]
    approved_amount: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CORPricingResponse(BaseModel):
    id: str
    cor_id: str
    line_items: List[CORLineItem]
    material_cost: int
    labor_cost: int
    equipment_cost: int
    subcontract_cost: int
    overhead_profit: int
    bond_insurance: int
    subtotal: int
    tax: int
    total: int
    status: str
    submitted_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ChangeOrderService:
    """Service for managing change orders."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def _generate_cor_number(self, tenant_id: str, project_id: str) -> str:
        """Generate unique COR number."""
        count = self.db.query(ChangeOrderRequest).filter(
            ChangeOrderRequest.tenant_id == tenant_id,
            ChangeOrderRequest.project_id == project_id
        ).count()
        return f"COR-{count + 1:04d}"
    
    def create_cor(
        self,
        tenant_id: str,
        user_id: str,
        company_id: Optional[str],
        request: CORCreateRequest
    ) -> ChangeOrderRequest:
        """Create a change order request."""
        cor = ChangeOrderRequest(
            tenant_id=tenant_id,
            project_id=request.project_id,
            cor_number=self._generate_cor_number(tenant_id, request.project_id),
            title=request.title,
            description=request.description,
            cor_type=request.cor_type,
            submitted_by_company_id=company_id,
            submitted_by_user_id=user_id,
            rfi_reference_id=request.rfi_reference_id,
            drawing_reference=request.drawing_reference,
            specification_section=request.specification_section,
            reason=request.reason,
            justification=request.justification,
            cost_impact=request.cost_impact,
            schedule_impact=request.schedule_impact,
            days_impact=request.days_impact,
            attachments=[att.dict() for att in request.attachments]
        )
        
        self.db.add(cor)
        self.db.commit()
        return cor
    
    def submit_cor(
        self,
        tenant_id: str,
        cor_id: str,
        user_id: str
    ) -> ChangeOrderRequest:
        """Submit change order request."""
        cor = self.db.query(ChangeOrderRequest).filter(
            ChangeOrderRequest.tenant_id == tenant_id,
            ChangeOrderRequest.id == cor_id
        ).first()
        
        if not cor:
            raise ValueError("Change order not found")
        
        if cor.status != CORStatus.DRAFT:
            raise ValueError("Change order can only be submitted from draft status")
        
        cor.status = CORStatus.SUBMITTED
        cor.submitted_at = datetime.utcnow()
        
        self.db.commit()
        return cor
    
    def submit_pricing(
        self,
        tenant_id: str,
        cor_id: str,
        user_id: str,
        request: CORPricingSubmitRequest
    ) -> CORPricing:
        """Submit pricing for a change order."""
        cor = self.db.query(ChangeOrderRequest).filter(
            ChangeOrderRequest.tenant_id == tenant_id,
            ChangeOrderRequest.id == cor_id
        ).first()
        
        if not cor:
            raise ValueError("Change order not found")
        
        # Calculate totals
        subtotal = request.material_cost + request.labor_cost + request.equipment_cost + request.subcontract_cost + request.overhead_profit + request.bond_insurance
        total = subtotal + request.tax
        
        pricing = CORPricing(
            tenant_id=tenant_id,
            cor_id=cor_id,
            line_items=[item.dict() for item in request.line_items],
            material_cost=request.material_cost,
            labor_cost=request.labor_cost,
            equipment_cost=request.equipment_cost,
            subcontract_cost=request.subcontract_cost,
            overhead_profit=request.overhead_profit,
            bond_insurance=request.bond_insurance,
            subtotal=subtotal,
            tax=request.tax,
            total=total,
            submitted_by=user_id,
            submitted_at=datetime.utcnow(),
            status=CORPricingStatus.SUBMITTED
        )
        
        self.db.add(pricing)
        
        cor.status = CORStatus.PENDING_APPROVAL
        
        self.db.commit()
        return pricing
    
    def review_cor(
        self,
        tenant_id: str,
        cor_id: str,
        user_id: str,
        request: CORReviewRequest
    ) -> ChangeOrderRequest:
        """Review a change order request."""
        cor = self.db.query(ChangeOrderRequest).filter(
            ChangeOrderRequest.tenant_id == tenant_id,
            ChangeOrderRequest.id == cor_id
        ).first()
        
        if not cor:
            raise ValueError("Change order not found")
        
        cor.reviewed_by = user_id
        cor.reviewed_at = datetime.utcnow()
        cor.review_notes = request.notes
        
        if request.action == "approve":
            cor.status = CORStatus.APPROVED
            cor.approved_by = user_id
            cor.approved_at = datetime.utcnow()
            cor.approval_amount = request.approval_amount
        elif request.action == "reject":
            cor.status = CORStatus.REJECTED
        elif request.action == "request_pricing":
            cor.status = CORStatus.PRICING_REQUESTED
        elif request.action == "request_revision":
            cor.status = CORStatus.UNDER_REVIEW
        
        self.db.commit()
        return cor
    
    def get_cors(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status: Optional[str] = None,
        cor_type: Optional[str] = None
    ) -> List[ChangeOrderRequest]:
        """Get change orders with filters."""
        query = self.db.query(ChangeOrderRequest).filter(ChangeOrderRequest.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(ChangeOrderRequest.project_id == project_id)
        if company_id:
            query = query.filter(ChangeOrderRequest.submitted_by_company_id == company_id)
        if status:
            query = query.filter(ChangeOrderRequest.status == status)
        if cor_type:
            query = query.filter(ChangeOrderRequest.cor_type == cor_type)
        
        return query.order_by(ChangeOrderRequest.created_at.desc()).all()
    
    def get_cor_detail(
        self,
        tenant_id: str,
        cor_id: str
    ) -> Dict[str, Any]:
        """Get change order with pricing."""
        cor = self.db.query(ChangeOrderRequest).filter(
            ChangeOrderRequest.tenant_id == tenant_id,
            ChangeOrderRequest.id == cor_id
        ).first()
        
        if not cor:
            raise ValueError("Change order not found")
        
        pricing = self.db.query(CORPricing).filter(
            CORPricing.cor_id == cor_id
        ).first()
        
        return {
            "change_order": cor,
            "pricing": pricing
        }
    
    def get_cor_metrics(
        self,
        tenant_id: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get change order metrics."""
        query = self.db.query(ChangeOrderRequest).filter(ChangeOrderRequest.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(ChangeOrderRequest.project_id == project_id)
        
        total = query.count()
        pending = query.filter(ChangeOrderRequest.status.in_([CORStatus.SUBMITTED, CORStatus.UNDER_REVIEW])).count()
        approved = query.filter(ChangeOrderRequest.status == CORStatus.APPROVED).count()
        rejected = query.filter(ChangeOrderRequest.status == CORStatus.REJECTED).count()
        
        # Calculate total value
        pricing_query = self.db.query(CORPricing).join(ChangeOrderRequest).filter(
            ChangeOrderRequest.tenant_id == tenant_id
        )
        
        if project_id:
            pricing_query = pricing_query.filter(ChangeOrderRequest.project_id == project_id)
        
        total_value = sum(p.total for p in pricing_query.all())
        approved_value = sum(
            p.total for p in pricing_query.filter(ChangeOrderRequest.status == CORStatus.APPROVED).all()
        )
        
        return {
            "total_cors": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "total_value": total_value,
            "approved_value": approved_value,
            "approval_rate": round(approved / total * 100, 1) if total > 0 else 0
        }
