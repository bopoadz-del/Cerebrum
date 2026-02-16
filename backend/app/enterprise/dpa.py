"""
Data Processing Agreement Module - DPA Management
Item 299: Data Processing Agreements
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from app.db.base_class import Base

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class DPAStatus(str, Enum):
    """DPA status"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    AMENDED = "amended"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class SubprocessorCategory(str, Enum):
    """Subprocessor categories"""
    INFRASTRUCTURE = "infrastructure"
    ANALYTICS = "analytics"
    COMMUNICATIONS = "communications"
    PAYMENT = "payment"
    SECURITY = "security"
    STORAGE = "storage"
    AI_ML = "ai_ml"
    OTHER = "other"


# Database Models

class DataProcessingAgreement(Base):
    """Data Processing Agreement"""
    __tablename__ = 'data_processing_agreements'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # DPA reference
    dpa_number = Column(String(100), unique=True, nullable=False)
    version = Column(String(20), default='1.0')
    
    # Parties
    controller_name = Column(String(500), nullable=False)
    controller_address = Column(Text, nullable=True)
    controller_contact_email = Column(String(255), nullable=True)
    controller_dpo_email = Column(String(255), nullable=True)
    
    processor_name = Column(String(500), default='Cerebrum AI, Inc.')
    processor_address = Column(Text, nullable=True)
    processor_contact_email = Column(String(255), nullable=True)
    processor_dpo_email = Column(String(255), nullable=True)
    
    # Status
    status = Column(String(50), default=DPAStatus.DRAFT.value)
    
    # Scope
    processing_activities = Column(JSONB, default=list)
    data_categories = Column(JSONB, default=list)
    data_subject_categories = Column(JSONB, default=list)
    
    # Security measures
    security_measures = Column(Text, nullable=True)
    encryption_standards = Column(String(255), nullable=True)
    
    # Subprocessors
    subprocessors_approved = Column(Boolean, default=False)
    subprocessors_list_url = Column(String(500), nullable=True)
    
    # International transfers
    international_transfers = Column(Boolean, default=False)
    transfer_mechanism = Column(String(100), nullable=True)  # SCCs, BCRs, adequacy decision
    transfer_safeguards = Column(Text, nullable=True)
    
    # Audit rights
    audit_rights = Column(Boolean, default=True)
    audit_frequency = Column(String(50), default='annual')
    
    # Breach notification
    breach_notification_hours = Column(Integer, default=72)
    
    # Termination
    data_return_period_days = Column(Integer, default=30)
    data_deletion_period_days = Column(Integer, default=90)
    
    # Documents
    document_url = Column(String(500), nullable=True)
    signed_document_url = Column(String(500), nullable=True)
    
    # Signatures
    signed_by_controller = Column(Boolean, default=False)
    signed_by_controller_at = Column(DateTime, nullable=True)
    signed_by_controller_name = Column(String(255), nullable=True)
    signed_by_controller_title = Column(String(255), nullable=True)
    
    signed_by_processor = Column(Boolean, default=False)
    signed_by_processor_at = Column(DateTime, nullable=True)
    signed_by_processor_name = Column(String(255), nullable=True)
    signed_by_processor_title = Column(String(255), nullable=True)
    
    # Effective dates
    effective_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    
    # Metadata
    custom_clauses = Column(JSONB, default=list)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class Subprocessor(Base):
    """Approved subprocessors"""
    __tablename__ = 'subprocessors'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Subprocessor details
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Category
    category = Column(String(50), nullable=False)
    
    # Location
    country = Column(String(100), nullable=False)
    region = Column(String(100), nullable=True)
    
    # Data processing
    data_processed = Column(Text, nullable=True)
    data_location = Column(String(100), nullable=True)
    
    # Security
    security_certifications = Column(JSONB, default=list)
    gdpr_compliant = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Contact
    privacy_policy_url = Column(String(500), nullable=True)
    dpa_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DPAAmendment(Base):
    """DPA amendments"""
    __tablename__ = 'dpa_amendments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dpa_id = Column(UUID(as_uuid=True), ForeignKey('data_processing_agreements.id', ondelete='CASCADE'), nullable=False)
    
    # Amendment details
    amendment_number = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    
    # Changes
    changes_summary = Column(Text, nullable=True)
    previous_version = Column(String(20), nullable=False)
    new_version = Column(String(20), nullable=False)
    
    # Status
    status = Column(String(50), default='pending')
    
    # Documents
    document_url = Column(String(500), nullable=True)
    
    # Signatures
    signed_by_controller = Column(Boolean, default=False)
    signed_by_controller_at = Column(DateTime, nullable=True)
    signed_by_processor = Column(Boolean, default=False)
    signed_by_processor_at = Column(DateTime, nullable=True)
    
    # Effective date
    effective_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class DPANotification(Base):
    """DPA notifications (new subprocessors, changes)"""
    __tablename__ = 'dpa_notifications'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dpa_id = Column(UUID(as_uuid=True), ForeignKey('data_processing_agreements.id', ondelete='CASCADE'), nullable=False)
    
    # Notification details
    notification_type = Column(String(50), nullable=False)  # new_subprocessor, security_incident, policy_change
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Related entity
    subprocessor_id = Column(UUID(as_uuid=True), ForeignKey('subprocessors.id'), nullable=True)
    
    # Status
    status = Column(String(50), default='pending')
    
    # Response
    response_required = Column(Boolean, default=False)
    response_deadline = Column(DateTime, nullable=True)
    response_received = Column(Boolean, default=False)
    response_received_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class CreateDPARequest(BaseModel):
    """Create DPA request"""
    controller_name: str
    controller_address: Optional[str] = None
    controller_contact_email: Optional[str] = None
    controller_dpo_email: Optional[str] = None
    processing_activities: List[str] = Field(default_factory=list)
    data_categories: List[str] = Field(default_factory=list)
    data_subject_categories: List[str] = Field(default_factory=list)
    international_transfers: bool = False
    transfer_mechanism: Optional[str] = None
    custom_clauses: List[Dict[str, Any]] = Field(default_factory=list)


class UpdateDPARequest(BaseModel):
    """Update DPA request"""
    security_measures: Optional[str] = None
    encryption_standards: Optional[str] = None
    breach_notification_hours: Optional[int] = None
    data_return_period_days: Optional[int] = None
    data_deletion_period_days: Optional[int] = None


class SignDPARequest(BaseModel):
    """Sign DPA request"""
    party: str  # 'controller' or 'processor'
    signed_by_name: str
    signed_by_title: Optional[str] = None


class CreateSubprocessorRequest(BaseModel):
    """Create subprocessor request"""
    name: str
    description: Optional[str] = None
    category: SubprocessorCategory
    country: str
    region: Optional[str] = None
    data_processed: Optional[str] = None
    security_certifications: List[str] = Field(default_factory=list)
    gdpr_compliant: bool = False
    privacy_policy_url: Optional[str] = None


class DPAResponse(BaseModel):
    """DPA response"""
    id: str
    dpa_number: str
    version: str
    controller_name: str
    status: str
    effective_date: Optional[datetime]
    created_at: datetime


class SubprocessorResponse(BaseModel):
    """Subprocessor response"""
    id: str
    name: str
    category: str
    country: str
    gdpr_compliant: bool
    is_active: bool


# Service Classes

class DPAService:
    """Service for DPA management"""
    
    STANDARD_PROCESSING_ACTIVITIES = [
        'Project management and collaboration',
        'Document storage and management',
        'Communication and messaging',
        'Analytics and reporting',
        'User authentication and access control',
        'Payment processing',
        'Customer support'
    ]
    
    STANDARD_DATA_CATEGORIES = [
        'Contact information (name, email, phone)',
        'Professional information (title, company)',
        'Project data and documents',
        'Communication records',
        'Usage data and analytics',
        'Payment information'
    ]
    
    STANDARD_DATA_SUBJECTS = [
        'Employees and contractors',
        'Customers and clients',
        'Vendors and suppliers',
        'Project stakeholders'
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_dpa_number(self) -> str:
        """Generate unique DPA number"""
        year = datetime.utcnow().strftime('%Y')
        random_suffix = str(uuid.uuid4().hex[:8]).upper()
        return f"DPA-{year}-{random_suffix}"
    
    def create_dpa(
        self,
        tenant_id: str,
        request: CreateDPARequest,
        created_by: Optional[str] = None
    ) -> DataProcessingAgreement:
        """Create new DPA"""
        
        dpa = DataProcessingAgreement(
            tenant_id=tenant_id,
            dpa_number=self._generate_dpa_number(),
            controller_name=request.controller_name,
            controller_address=request.controller_address,
            controller_contact_email=request.controller_contact_email,
            controller_dpo_email=request.controller_dpo_email,
            processing_activities=request.processing_activities or self.STANDARD_PROCESSING_ACTIVITIES,
            data_categories=request.data_categories or self.STANDARD_DATA_CATEGORIES,
            data_subject_categories=request.data_subject_categories or self.STANDARD_DATA_SUBJECTS,
            international_transfers=request.international_transfers,
            transfer_mechanism=request.transfer_mechanism,
            custom_clauses=request.custom_clauses,
            created_by=created_by
        )
        
        self.db.add(dpa)
        self.db.commit()
        self.db.refresh(dpa)
        
        return dpa
    
    def get_dpa(self, dpa_id: str) -> Optional[DataProcessingAgreement]:
        """Get DPA by ID"""
        return self.db.query(DataProcessingAgreement).filter(
            DataProcessingAgreement.id == dpa_id
        ).first()
    
    def get_dpa_by_number(self, dpa_number: str) -> Optional[DataProcessingAgreement]:
        """Get DPA by number"""
        return self.db.query(DataProcessingAgreement).filter(
            DataProcessingAgreement.dpa_number == dpa_number
        ).first()
    
    def list_dpas(
        self,
        tenant_id: str,
        status: Optional[str] = None
    ) -> List[DataProcessingAgreement]:
        """List DPAs for tenant"""
        
        query = self.db.query(DataProcessingAgreement).filter(
            DataProcessingAgreement.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(DataProcessingAgreement.status == status)
        
        return query.order_by(DataProcessingAgreement.created_at.desc()).all()
    
    def update_dpa(
        self,
        dpa_id: str,
        request: UpdateDPARequest
    ) -> DataProcessingAgreement:
        """Update DPA"""
        
        dpa = self.get_dpa(dpa_id)
        if not dpa:
            raise HTTPException(404, "DPA not found")
        
        if request.security_measures is not None:
            dpa.security_measures = request.security_measures
        
        if request.encryption_standards is not None:
            dpa.encryption_standards = request.encryption_standards
        
        if request.breach_notification_hours is not None:
            dpa.breach_notification_hours = request.breach_notification_hours
        
        if request.data_return_period_days is not None:
            dpa.data_return_period_days = request.data_return_period_days
        
        if request.data_deletion_period_days is not None:
            dpa.data_deletion_period_days = request.data_deletion_period_days
        
        self.db.commit()
        self.db.refresh(dpa)
        
        return dpa
    
    def sign_dpa(
        self,
        dpa_id: str,
        request: SignDPARequest
    ) -> DataProcessingAgreement:
        """Sign DPA"""
        
        dpa = self.get_dpa(dpa_id)
        if not dpa:
            raise HTTPException(404, "DPA not found")
        
        if request.party == 'controller':
            dpa.signed_by_controller = True
            dpa.signed_by_controller_at = datetime.utcnow()
            dpa.signed_by_controller_name = request.signed_by_name
            dpa.signed_by_controller_title = request.signed_by_title
        elif request.party == 'processor':
            dpa.signed_by_processor = True
            dpa.signed_by_processor_at = datetime.utcnow()
            dpa.signed_by_processor_name = request.signed_by_name
            dpa.signed_by_processor_title = request.signed_by_title
        
        # Check if fully signed
        if dpa.signed_by_controller and dpa.signed_by_processor:
            dpa.status = DPAStatus.ACTIVE.value
            dpa.effective_date = datetime.utcnow()
        else:
            dpa.status = DPAStatus.PENDING_SIGNATURE.value
        
        self.db.commit()
        self.db.refresh(dpa)
        
        return dpa
    
    def create_amendment(
        self,
        dpa_id: str,
        description: str,
        changes_summary: str,
        new_version: str
    ) -> DPAAmendment:
        """Create DPA amendment"""
        
        dpa = self.get_dpa(dpa_id)
        if not dpa:
            raise HTTPException(404, "DPA not found")
        
        # Count existing amendments
        amendment_count = self.db.query(DPAAmendment).filter(
            DPAAmendment.dpa_id == dpa_id
        ).count()
        
        amendment = DPAAmendment(
            dpa_id=dpa_id,
            amendment_number=f"A{amendment_count + 1}",
            description=description,
            changes_summary=changes_summary,
            previous_version=dpa.version,
            new_version=new_version
        )
        
        self.db.add(amendment)
        
        # Update DPA status
        dpa.status = DPAStatus.AMENDED.value
        dpa.version = new_version
        
        self.db.commit()
        self.db.refresh(amendment)
        
        return amendment
    
    def notify_new_subprocessor(
        self,
        dpa_id: str,
        subprocessor_id: str,
        response_days: int = 30
    ) -> DPANotification:
        """Notify customer of new subprocessor"""
        
        subprocessor = self.db.query(Subprocessor).filter(
            Subprocessor.id == subprocessor_id
        ).first()
        
        if not subprocessor:
            raise HTTPException(404, "Subprocessor not found")
        
        notification = DPANotification(
            dpa_id=dpa_id,
            notification_type='new_subprocessor',
            title=f'New Subprocessor: {subprocessor.name}',
            description=f'We have added {subprocessor.name} as a new subprocessor for {subprocessor.category.value} services.',
            subprocessor_id=subprocessor_id,
            response_required=True,
            response_deadline=datetime.utcnow() + timedelta(days=response_days)
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        return notification


class SubprocessorService:
    """Service for subprocessor management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_subprocessor(
        self,
        request: CreateSubprocessorRequest
    ) -> Subprocessor:
        """Create subprocessor"""
        
        subprocessor = Subprocessor(
            name=request.name,
            description=request.description,
            category=request.category.value,
            country=request.country,
            region=request.region,
            data_processed=request.data_processed,
            security_certifications=request.security_certifications,
            gdpr_compliant=request.gdpr_compliant,
            privacy_policy_url=request.privacy_policy_url
        )
        
        self.db.add(subprocessor)
        self.db.commit()
        self.db.refresh(subprocessor)
        
        return subprocessor
    
    def get_subprocessor(self, subprocessor_id: str) -> Optional[Subprocessor]:
        """Get subprocessor by ID"""
        return self.db.query(Subprocessor).filter(
            Subprocessor.id == subprocessor_id
        ).first()
    
    def list_subprocessors(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = True
    ) -> List[Subprocessor]:
        """List subprocessors"""
        
        query = self.db.query(Subprocessor)
        
        if category:
            query = query.filter(Subprocessor.category == category)
        
        if is_active is not None:
            query = query.filter(Subprocessor.is_active == is_active)
        
        return query.order_by(Subprocessor.name).all()
    
    def approve_subprocessor(self, subprocessor_id: str) -> Subprocessor:
        """Approve subprocessor"""
        
        subprocessor = self.get_subprocessor(subprocessor_id)
        if not subprocessor:
            raise HTTPException(404, "Subprocessor not found")
        
        subprocessor.is_active = True
        subprocessor.approved_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(subprocessor)
        
        return subprocessor


# Export
__all__ = [
    'DPAStatus',
    'SubprocessorCategory',
    'DataProcessingAgreement',
    'Subprocessor',
    'DPAAmendment',
    'DPANotification',
    'CreateDPARequest',
    'UpdateDPARequest',
    'SignDPARequest',
    'CreateSubprocessorRequest',
    'DPAResponse',
    'SubprocessorResponse',
    'DPAService',
    'SubprocessorService'
]
