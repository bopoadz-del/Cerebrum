"""
Project Closeout Module
Handles O&M manuals, as-builts, warranties, and final documentation.
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer, Date
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class CloseoutItemType(str, Enum):
    O_AND_M_MANUAL = "o_and_m_manual"
    AS_BUILT_DRAWINGS = "as_built_drawings"
    WARRANTIES = "warranties"
    CERTIFICATES = "certificates"
    TEST_REPORTS = "test_reports"
    TRAINING_DOCS = "training_docs"
    SPARE_PARTS_LIST = "spare_parts_list"
    FINAL_LIEN_WAIVERS = "final_lien_waivers"
    ATTIC_STOCK = "attic_stock"
    OTHER = "other"


class CloseoutStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    REVISION_REQUIRED = "revision_required"
    APPROVED = "approved"
    REJECTED = "rejected"


class CloseoutItem(Base):
    """Individual closeout item."""
    __tablename__ = 'closeout_items'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    item_type = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    specification_section = Column(String(50))
    trade = Column(String(100))
    
    submitted_by_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    required_count = Column(Integer, default=1)
    submitted_count = Column(Integer, default=0)
    
    status = Column(String(50), default=CloseoutStatus.NOT_STARTED)
    
    due_date = Column(Date)
    submitted_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    
    reviewed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    review_notes = Column(Text)
    
    documents = Column(JSONB, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WarrantyRecord(Base):
    """Warranty record for equipment/materials."""
    __tablename__ = 'warranty_records'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    equipment_name = Column(String(500), nullable=False)
    manufacturer = Column(String(255))
    model_number = Column(String(255))
    serial_number = Column(String(255))
    
    supplier_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    warranty_type = Column(String(100))  # manufacturer, extended, workmanship
    warranty_period_months = Column(Integer)
    
    start_date = Column(Date)
    expiration_date = Column(Date)
    
    warranty_document_url = Column(String(1000))
    warranty_terms = Column(Text)
    
    contact_name = Column(String(255))
    contact_phone = Column(String(50))
    contact_email = Column(String(255))
    
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AsBuiltDrawing(Base):
    """As-built drawing record."""
    __tablename__ = 'as_built_drawings'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    drawing_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    discipline = Column(String(100))
    
    submitted_by_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    file_url = Column(String(1000))
    file_name = Column(String(500))
    file_size = Column(Integer)
    
    revision = Column(String(20), default="0")
    
    status = Column(String(50), default=CloseoutStatus.NOT_STARTED)
    
    submitted_at = Column(DateTime)
    approved_at = Column(DateTime)
    approved_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FinalLienWaiver(Base):
    """Final lien waiver record."""
    __tablename__ = 'final_lien_waivers'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'), nullable=False)
    
    waiver_type = Column(String(50))  # partial, final
    waiver_amount = Column(Integer)  # cents
    
    through_date = Column(Date)
    
    signed_by = Column(String(255))
    signed_date = Column(Date)
    
    notarized = Column(Boolean, default=False)
    notary_name = Column(String(255))
    notary_date = Column(Date)
    
    document_url = Column(String(1000))
    
    status = Column(String(50), default="pending")
    verified_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    verified_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models

class CloseoutDocument(BaseModel):
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    description: Optional[str] = None
    revision: str = "0"


class CloseoutItemCreateRequest(BaseModel):
    project_id: str
    item_type: CloseoutItemType
    title: str
    description: Optional[str] = None
    specification_section: Optional[str] = None
    trade: Optional[str] = None
    required_count: int = 1
    due_date: Optional[str] = None


class SubmitCloseoutItemRequest(BaseModel):
    documents: List[CloseoutDocument]
    notes: Optional[str] = None


class ReviewCloseoutItemRequest(BaseModel):
    action: str  # approve, reject
    notes: Optional[str] = None


class WarrantyCreateRequest(BaseModel):
    project_id: str
    equipment_name: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    supplier_company_id: Optional[str] = None
    warranty_type: str
    warranty_period_months: int
    start_date: Optional[str] = None
    expiration_date: Optional[str] = None
    warranty_document_url: Optional[str] = None
    warranty_terms: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class AsBuiltCreateRequest(BaseModel):
    project_id: str
    drawing_number: str
    title: str
    description: Optional[str] = None
    discipline: Optional[str] = None
    file_url: str
    file_name: str
    file_size: int
    file_type: str


class LienWaiverCreateRequest(BaseModel):
    project_id: str
    company_id: str
    waiver_type: str
    waiver_amount: int
    through_date: str
    signed_by: str
    signed_date: str
    notarized: bool = False
    notary_name: Optional[str] = None
    notary_date: Optional[str] = None
    document_url: str


class CloseoutItemResponse(BaseModel):
    id: str
    item_type: str
    title: str
    description: Optional[str]
    specification_section: Optional[str]
    trade: Optional[str]
    submitted_by_company_id: Optional[str]
    submitted_by_company_name: Optional[str]
    required_count: int
    submitted_count: int
    status: str
    due_date: Optional[date]
    submitted_at: Optional[datetime]
    days_overdue: int
    
    class Config:
        from_attributes = True


class WarrantyResponse(BaseModel):
    id: str
    equipment_name: str
    manufacturer: Optional[str]
    model_number: Optional[str]
    serial_number: Optional[str]
    warranty_type: str
    warranty_period_months: int
    start_date: Optional[date]
    expiration_date: Optional[date]
    days_until_expiration: int
    contact_name: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CloseoutService:
    """Service for project closeout management."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_closeout_item(
        self,
        tenant_id: str,
        user_id: str,
        request: CloseoutItemCreateRequest
    ) -> CloseoutItem:
        """Create a closeout item requirement."""
        item = CloseoutItem(
            tenant_id=tenant_id,
            project_id=request.project_id,
            item_type=request.item_type,
            title=request.title,
            description=request.description,
            specification_section=request.specification_section,
            trade=request.trade,
            required_count=request.required_count,
            due_date=datetime.strptime(request.due_date, "%Y-%m-%d").date() if request.due_date else None
        )
        
        self.db.add(item)
        self.db.commit()
        return item
    
    def submit_closeout_item(
        self,
        tenant_id: str,
        item_id: str,
        company_id: str,
        user_id: str,
        request: SubmitCloseoutItemRequest
    ) -> CloseoutItem:
        """Submit documents for a closeout item."""
        item = self.db.query(CloseoutItem).filter(
            CloseoutItem.tenant_id == tenant_id,
            CloseoutItem.id == item_id
        ).first()
        
        if not item:
            raise ValueError("Closeout item not found")
        
        item.submitted_by_company_id = company_id
        item.submitted_count = len(request.documents)
        item.status = CloseoutStatus.SUBMITTED
        item.submitted_at = datetime.utcnow()
        item.documents = [doc.dict() for doc in request.documents]
        
        if request.notes:
            item.description = f"{item.description or ''}\n\nSubmission Notes: {request.notes}"
        
        self.db.commit()
        return item
    
    def review_closeout_item(
        self,
        tenant_id: str,
        item_id: str,
        user_id: str,
        request: ReviewCloseoutItemRequest
    ) -> CloseoutItem:
        """Review a submitted closeout item."""
        item = self.db.query(CloseoutItem).filter(
            CloseoutItem.tenant_id == tenant_id,
            CloseoutItem.id == item_id
        ).first()
        
        if not item:
            raise ValueError("Closeout item not found")
        
        item.reviewed_by = user_id
        item.reviewed_at = datetime.utcnow()
        item.review_notes = request.notes
        
        if request.action == "approve":
            item.status = CloseoutStatus.APPROVED
        else:
            item.status = CloseoutStatus.REVISION_REQUIRED
        
        self.db.commit()
        return item
    
    def create_warranty(
        self,
        tenant_id: str,
        user_id: str,
        request: WarrantyCreateRequest
    ) -> WarrantyRecord:
        """Create a warranty record."""
        warranty = WarrantyRecord(
            tenant_id=tenant_id,
            project_id=request.project_id,
            equipment_name=request.equipment_name,
            manufacturer=request.manufacturer,
            model_number=request.model_number,
            serial_number=request.serial_number,
            supplier_company_id=request.supplier_company_id,
            warranty_type=request.warranty_type,
            warranty_period_months=request.warranty_period_months,
            start_date=datetime.strptime(request.start_date, "%Y-%m-%d").date() if request.start_date else None,
            expiration_date=datetime.strptime(request.expiration_date, "%Y-%m-%d").date() if request.expiration_date else None,
            warranty_document_url=request.warranty_document_url,
            warranty_terms=request.warranty_terms,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
            contact_email=request.contact_email
        )
        
        self.db.add(warranty)
        self.db.commit()
        return warranty
    
    def create_as_built(
        self,
        tenant_id: str,
        company_id: str,
        user_id: str,
        request: AsBuiltCreateRequest
    ) -> AsBuiltDrawing:
        """Create an as-built drawing record."""
        as_built = AsBuiltDrawing(
            tenant_id=tenant_id,
            project_id=request.project_id,
            drawing_number=request.drawing_number,
            title=request.title,
            description=request.description,
            discipline=request.discipline,
            submitted_by_company_id=company_id,
            file_url=request.file_url,
            file_name=request.file_name,
            file_size=request.file_size,
            status=CloseoutStatus.SUBMITTED,
            submitted_at=datetime.utcnow()
        )
        
        self.db.add(as_built)
        self.db.commit()
        return as_built
    
    def create_lien_waiver(
        self,
        tenant_id: str,
        user_id: str,
        request: LienWaiverCreateRequest
    ) -> FinalLienWaiver:
        """Create a lien waiver record."""
        waiver = FinalLienWaiver(
            tenant_id=tenant_id,
            project_id=request.project_id,
            company_id=request.company_id,
            waiver_type=request.waiver_type,
            waiver_amount=request.waiver_amount,
            through_date=datetime.strptime(request.through_date, "%Y-%m-%d").date(),
            signed_by=request.signed_by,
            signed_date=datetime.strptime(request.signed_date, "%Y-%m-%d").date(),
            notarized=request.notarized,
            notary_name=request.notary_name,
            notary_date=datetime.strptime(request.notary_date, "%Y-%m-%d").date() if request.notary_date else None,
            document_url=request.document_url
        )
        
        self.db.add(waiver)
        self.db.commit()
        return waiver
    
    def get_closeout_items(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        item_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[CloseoutItem]:
        """Get closeout items with filters."""
        query = self.db.query(CloseoutItem).filter(CloseoutItem.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(CloseoutItem.project_id == project_id)
        if company_id:
            query = query.filter(CloseoutItem.submitted_by_company_id == company_id)
        if item_type:
            query = query.filter(CloseoutItem.item_type == item_type)
        if status:
            query = query.filter(CloseoutItem.status == status)
        
        return query.order_by(CloseoutItem.due_date).all()
    
    def get_warranties(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        expiring_soon: bool = False
    ) -> List[WarrantyRecord]:
        """Get warranty records."""
        query = self.db.query(WarrantyRecord).filter(WarrantyRecord.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(WarrantyRecord.project_id == project_id)
        
        if expiring_soon:
            # Warranties expiring in next 90 days
            from datetime import timedelta
            soon = date.today() + timedelta(days=90)
            query = query.filter(
                WarrantyRecord.expiration_date <= soon,
                WarrantyRecord.expiration_date >= date.today()
            )
        
        return query.order_by(WarrantyRecord.expiration_date).all()
    
    def get_closeout_summary(
        self,
        tenant_id: str,
        project_id: str
    ) -> Dict[str, Any]:
        """Get closeout summary for a project."""
        items = self.db.query(CloseoutItem).filter(
            CloseoutItem.tenant_id == tenant_id,
            CloseoutItem.project_id == project_id
        ).all()
        
        warranties = self.db.query(WarrantyRecord).filter(
            WarrantyRecord.tenant_id == tenant_id,
            WarrantyRecord.project_id == project_id
        ).count()
        
        as_builts = self.db.query(AsBuiltDrawing).filter(
            AsBuiltDrawing.tenant_id == tenant_id,
            AsBuiltDrawing.project_id == project_id
        ).count()
        
        lien_waivers = self.db.query(FinalLienWaiver).filter(
            FinalLienWaiver.tenant_id == tenant_id,
            FinalLienWaiver.project_id == project_id
        ).count()
        
        total_items = len(items)
        approved = len([i for i in items if i.status == CloseoutStatus.APPROVED])
        submitted = len([i for i in items if i.status == CloseoutStatus.SUBMITTED])
        not_started = len([i for i in items if i.status == CloseoutStatus.NOT_STARTED])
        
        return {
            "closeout_items": {
                "total": total_items,
                "approved": approved,
                "submitted": submitted,
                "not_started": not_started,
                "completion_percentage": round(approved / total_items * 100, 1) if total_items > 0 else 0
            },
            "warranties": warranties,
            "as_built_drawings": as_builts,
            "lien_waivers": lien_waivers,
            "overall_completion": self._calculate_overall_completion(
                total_items, approved, warranties, as_builts, lien_waivers
            )
        }
    
    def _calculate_overall_completion(
        self,
        total_items: int,
        approved_items: int,
        warranties: int,
        as_builts: int,
        lien_waivers: int
    ) -> float:
        """Calculate overall closeout completion percentage."""
        if total_items == 0:
            return 0.0
        
        item_completion = (approved_items / total_items) * 70  # 70% weight
        
        # Assume minimum targets for other items
        warranty_completion = min(warranties / 5, 1) * 10  # 10% weight
        as_built_completion = min(as_builts / 10, 1) * 10  # 10% weight
        lien_completion = min(lien_waivers / 5, 1) * 10  # 10% weight
        
        return round(item_completion + warranty_completion + as_built_completion + lien_completion, 1)
