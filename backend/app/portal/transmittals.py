"""
Transmittals Module
Handles document transmittal process between parties.
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


class TransmittalStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    RETURNED = "returned"


class TransmittalType(str, Enum):
    SUBMITTAL = "submittal"
    DRAWING = "drawing"
    SPECIFICATION = "specification"
    CORRESPONDENCE = "correspondence"
    CONTRACT = "contract"
    CHANGE_ORDER = "change_order"
    RFQ = "rfq"
    OTHER = "other"


class TransmittalAction(str, Enum):
    APPROVE = "approve"
    APPROVE_AS_NOTED = "approve_as_noted"
    REJECT = "reject"
    REVISE_RESUBMIT = "revise_resubmit"
    FOR_INFORMATION = "for_information"
    FOR_BID = "for_bid"
    FOR_CONSTRUCTION = "for_construction"


class Transmittal(Base):
    """Transmittal record."""
    __tablename__ = 'transmittals'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    transmittal_number = Column(String(100), nullable=False)
    transmittal_type = Column(String(100), nullable=False)
    
    subject = Column(String(500), nullable=False)
    message = Column(Text)
    
    from_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    from_user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    to_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    to_user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    
    required_action = Column(String(100))
    response_due_date = Column(DateTime)
    
    status = Column(String(50), default=TransmittalStatus.DRAFT)
    
    documents = Column(JSONB, default=list)  # List of transmitted documents
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    responses = relationship("TransmittalResponse", back_populates="transmittal")


class TransmittalResponse(Base):
    """Response to a transmittal."""
    __tablename__ = 'transmittal_responses'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    transmittal_id = Column(PG_UUID(as_uuid=True), ForeignKey('transmittals.id'), nullable=False)
    
    response_type = Column(String(100), nullable=False)  # action taken
    comments = Column(Text)
    
    responded_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    responded_at = Column(DateTime, default=datetime.utcnow)
    
    attachments = Column(JSONB, default=list)
    
    # Relationships
    transmittal = relationship("Transmittal", back_populates="responses")


class TransmittalDistributionList(Base):
    """Distribution list for transmittals."""
    __tablename__ = 'transmittal_distribution_lists'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    recipients = Column(JSONB, default=list)  # List of {company_id, user_id, role}
    
    is_active = Column(Boolean, default=True)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models

class TransmittalDocument(BaseModel):
    document_id: Optional[str] = None
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    revision: str = "0"
    description: Optional[str] = None


class TransmittalRecipient(BaseModel):
    company_id: Optional[str] = None
    user_id: Optional[str] = None
    role: str  # to, cc, bcc


class TransmittalCreateRequest(BaseModel):
    project_id: str
    transmittal_type: TransmittalType
    subject: str
    message: Optional[str] = None
    to_company_id: Optional[str] = None
    to_user_id: Optional[str] = None
    required_action: Optional[TransmittalAction] = None
    response_due_date: Optional[datetime] = None
    documents: List[TransmittalDocument] = []


class TransmittalSendRequest(BaseModel):
    distribution_list_id: Optional[str] = None
    additional_recipients: List[TransmittalRecipient] = []


class TransmittalResponseRequest(BaseModel):
    response_type: TransmittalAction
    comments: Optional[str] = None
    attachments: List[TransmittalDocument] = []


class DistributionListCreateRequest(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    recipients: List[TransmittalRecipient]


class TransmittalResponse(BaseModel):
    id: str
    transmittal_number: str
    transmittal_type: str
    subject: str
    message: Optional[str]
    from_company_id: Optional[str]
    from_company_name: Optional[str]
    from_user_name: Optional[str]
    to_company_id: Optional[str]
    to_company_name: Optional[str]
    to_user_name: Optional[str]
    sent_at: Optional[datetime]
    required_action: Optional[str]
    response_due_date: Optional[datetime]
    status: str
    document_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransmittalDetailResponse(BaseModel):
    transmittal: TransmittalResponse
    documents: List[TransmittalDocument]
    responses: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class DistributionListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    recipient_count: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransmittalService:
    """Service for managing transmittals."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def _generate_transmittal_number(self, tenant_id: str, project_id: str) -> str:
        """Generate unique transmittal number."""
        count = self.db.query(Transmittal).filter(
            Transmittal.tenant_id == tenant_id,
            Transmittal.project_id == project_id
        ).count()
        return f"TRN-{count + 1:05d}"
    
    def create_transmittal(
        self,
        tenant_id: str,
        user_id: str,
        company_id: Optional[str],
        request: TransmittalCreateRequest
    ) -> Transmittal:
        """Create a new transmittal."""
        transmittal = Transmittal(
            tenant_id=tenant_id,
            project_id=request.project_id,
            transmittal_number=self._generate_transmittal_number(tenant_id, request.project_id),
            transmittal_type=request.transmittal_type,
            subject=request.subject,
            message=request.message,
            from_company_id=company_id,
            from_user_id=user_id,
            to_company_id=request.to_company_id,
            to_user_id=request.to_user_id,
            required_action=request.required_action,
            response_due_date=request.response_due_date,
            documents=[doc.dict() for doc in request.documents]
        )
        
        self.db.add(transmittal)
        self.db.commit()
        return transmittal
    
    def send_transmittal(
        self,
        tenant_id: str,
        transmittal_id: str,
        user_id: str,
        request: TransmittalSendRequest
    ) -> Transmittal:
        """Send a transmittal."""
        transmittal = self.db.query(Transmittal).filter(
            Transmittal.tenant_id == tenant_id,
            Transmittal.id == transmittal_id
        ).first()
        
        if not transmittal:
            raise ValueError("Transmittal not found")
        
        if transmittal.status != TransmittalStatus.DRAFT:
            raise ValueError("Transmittal has already been sent")
        
        transmittal.status = TransmittalStatus.SENT
        transmittal.sent_at = datetime.utcnow()
        
        # TODO: Send email notifications
        # TODO: Handle distribution list
        
        self.db.commit()
        return transmittal
    
    def respond_to_transmittal(
        self,
        tenant_id: str,
        transmittal_id: str,
        user_id: str,
        request: TransmittalResponseRequest
    ) -> TransmittalResponse:
        """Respond to a transmittal."""
        transmittal = self.db.query(Transmittal).filter(
            Transmittal.tenant_id == tenant_id,
            Transmittal.id == transmittal_id
        ).first()
        
        if not transmittal:
            raise ValueError("Transmittal not found")
        
        response = TransmittalResponseModel(
            tenant_id=tenant_id,
            transmittal_id=transmittal_id,
            response_type=request.response_type,
            comments=request.comments,
            responded_by=user_id,
            attachments=[att.dict() for att in request.attachments]
        )
        
        self.db.add(response)
        
        # Update transmittal status
        transmittal.status = TransmittalStatus.ACKNOWLEDGED
        transmittal.acknowledged_at = datetime.utcnow()
        
        self.db.commit()
        return response
    
    def create_distribution_list(
        self,
        tenant_id: str,
        user_id: str,
        request: DistributionListCreateRequest
    ) -> TransmittalDistributionList:
        """Create a distribution list."""
        dist_list = TransmittalDistributionList(
            tenant_id=tenant_id,
            project_id=request.project_id,
            name=request.name,
            description=request.description,
            recipients=[r.dict() for r in request.recipients],
            created_by=user_id
        )
        
        self.db.add(dist_list)
        self.db.commit()
        return dist_list
    
    def get_transmittals(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status: Optional[str] = None,
        transmittal_type: Optional[str] = None,
        sent_by_me: bool = False,
        received_by_me: bool = False,
        user_id: Optional[str] = None
    ) -> List[Transmittal]:
        """Get transmittals with filters."""
        query = self.db.query(Transmittal).filter(Transmittal.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(Transmittal.project_id == project_id)
        if company_id:
            query = query.filter(
                (Transmittal.from_company_id == company_id) | 
                (Transmittal.to_company_id == company_id)
            )
        if status:
            query = query.filter(Transmittal.status == status)
        if transmittal_type:
            query = query.filter(Transmittal.transmittal_type == transmittal_type)
        if sent_by_me and user_id:
            query = query.filter(Transmittal.from_user_id == user_id)
        if received_by_me and user_id:
            query = query.filter(Transmittal.to_user_id == user_id)
        
        return query.order_by(Transmittal.created_at.desc()).all()
    
    def get_transmittal_detail(
        self,
        tenant_id: str,
        transmittal_id: str
    ) -> Dict[str, Any]:
        """Get transmittal with responses."""
        transmittal = self.db.query(Transmittal).filter(
            Transmittal.tenant_id == tenant_id,
            Transmittal.id == transmittal_id
        ).first()
        
        if not transmittal:
            raise ValueError("Transmittal not found")
        
        responses = self.db.query(TransmittalResponse).filter(
            TransmittalResponse.transmittal_id == transmittal_id
        ).order_by(TransmittalResponse.responded_at).all()
        
        return {
            "transmittal": transmittal,
            "documents": transmittal.documents,
            "responses": responses
        }
    
    def get_pending_responses(
        self,
        tenant_id: str,
        user_id: Optional[str] = None
    ) -> List[Transmittal]:
        """Get transmittals awaiting response."""
        query = self.db.query(Transmittal).filter(
            Transmittal.tenant_id == tenant_id,
            Transmittal.status.in_([TransmittalStatus.SENT, TransmittalStatus.DELIVERED]),
            Transmittal.response_due_date < datetime.utcnow()
        )
        
        if user_id:
            query = query.filter(Transmittal.to_user_id == user_id)
        
        return query.order_by(Transmittal.response_due_date).all()
    
    def get_transmittal_metrics(
        self,
        tenant_id: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get transmittal metrics."""
        query = self.db.query(Transmittal).filter(Transmittal.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(Transmittal.project_id == project_id)
        
        total = query.count()
        sent = query.filter(Transmittal.status == TransmittalStatus.SENT).count()
        acknowledged = query.filter(Transmittal.status == TransmittalStatus.ACKNOWLEDGED).count()
        pending = query.filter(Transmittal.status.in_([TransmittalStatus.SENT, TransmittalStatus.DELIVERED])).count()
        
        overdue = query.filter(
            Transmittal.status.in_([TransmittalStatus.SENT, TransmittalStatus.DELIVERED]),
            Transmittal.response_due_date < datetime.utcnow()
        ).count()
        
        return {
            "total_transmittals": total,
            "sent": sent,
            "acknowledged": acknowledged,
            "pending_response": pending,
            "overdue": overdue,
            "acknowledgment_rate": round(acknowledged / total * 100, 1) if total > 0 else 0
        }


# Fix for circular reference
TransmittalResponseModel = TransmittalResponse
