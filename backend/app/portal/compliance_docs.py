"""
Compliance Documents Module
Handles insurance, bond, and license verification.
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


class ComplianceDocType(str, Enum):
    INSURANCE_GENERAL_LIABILITY = "insurance_general_liability"
    INSURANCE_AUTO = "insurance_auto"
    INSURANCE_WORKERS_COMP = "insurance_workers_comp"
    INSURANCE_UMBRELLA = "insurance_umbrella"
    INSURANCE_PROFESSIONAL = "insurance_professional"
    BID_BOND = "bid_bond"
    PERFORMANCE_BOND = "performance_bond"
    PAYMENT_BOND = "payment_bond"
    LICENSE_CONTRACTOR = "license_contractor"
    LICENSE_TRADE = "license_trade"
    CERTIFICATION_OSHA = "certification_osha"
    CERTIFICATION_EPA = "certification_epa"
    CERTIFICATION_OTHER = "certification_other"
    W9 = "w9"
    COI = "coi"


class ComplianceStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    EXPIRED = "expired"
    EXPIRING_SOON = "expiring_soon"
    REJECTED = "rejected"


class ComplianceDocument(Base):
    """Compliance document record."""
    __tablename__ = 'compliance_documents'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'), nullable=False)
    
    document_type = Column(String(100), nullable=False)
    document_name = Column(String(500), nullable=False)
    
    # Insurance specific fields
    insurance_carrier = Column(String(255))
    policy_number = Column(String(255))
    coverage_amount = Column(Integer)  # cents
    
    # Bond specific fields
    bond_surety = Column(String(255))
    bond_number = Column(String(255))
    bond_amount = Column(Integer)  # cents
    
    # License specific fields
    license_number = Column(String(255))
    license_state = Column(String(50))
    license_class = Column(String(100))
    
    effective_date = Column(Date)
    expiration_date = Column(Date)
    
    document_url = Column(String(1000))
    
    status = Column(String(50), default=ComplianceStatus.PENDING_REVIEW)
    
    reviewed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    
    is_primary = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceRequirement(Base):
    """Compliance requirement for projects."""
    __tablename__ = 'compliance_requirements'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    document_type = Column(String(100), nullable=False)
    
    required = Column(Boolean, default=True)
    minimum_coverage = Column(Integer)  # cents for insurance/bonds
    
    description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceVerification(Base):
    """Compliance verification record."""
    __tablename__ = 'compliance_verifications'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'), nullable=False)
    
    verified_at = Column(DateTime, default=datetime.utcnow)
    verified_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    status = Column(String(50))  # compliant, non_compliant, partially_compliant
    
    requirements_met = Column(Integer, default=0)
    requirements_total = Column(Integer, default=0)
    
    missing_documents = Column(JSONB, default=list)
    expired_documents = Column(JSONB, default=list)
    
    notes = Column(Text)


# Pydantic Models

class InsuranceDocumentCreateRequest(BaseModel):
    company_id: str
    document_type: ComplianceDocType
    document_name: str
    insurance_carrier: str
    policy_number: str
    coverage_amount: int  # cents
    effective_date: str
    expiration_date: str
    document_url: str


class BondDocumentCreateRequest(BaseModel):
    company_id: str
    document_type: ComplianceDocType
    document_name: str
    bond_surety: str
    bond_number: str
    bond_amount: int  # cents
    effective_date: str
    expiration_date: str
    document_url: str


class LicenseDocumentCreateRequest(BaseModel):
    company_id: str
    document_type: ComplianceDocType
    document_name: str
    license_number: str
    license_state: str
    license_class: Optional[str] = None
    effective_date: str
    expiration_date: str
    document_url: str


class ComplianceRequirementCreateRequest(BaseModel):
    project_id: str
    document_type: ComplianceDocType
    required: bool = True
    minimum_coverage: Optional[int] = None  # cents
    description: Optional[str] = None


class ReviewComplianceRequest(BaseModel):
    action: str  # approve, reject
    notes: Optional[str] = None


class ComplianceDocumentResponse(BaseModel):
    id: str
    company_id: str
    company_name: Optional[str]
    document_type: str
    document_name: str
    insurance_carrier: Optional[str]
    policy_number: Optional[str]
    coverage_amount: Optional[int]
    bond_surety: Optional[str]
    bond_number: Optional[str]
    bond_amount: Optional[int]
    license_number: Optional[str]
    license_state: Optional[str]
    effective_date: Optional[date]
    expiration_date: Optional[date]
    days_until_expiration: int
    status: str
    reviewed_by_name: Optional[str]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ComplianceSummary(BaseModel):
    company_id: str
    company_name: str
    overall_status: str
    documents_total: int
    documents_approved: int
    documents_expired: int
    documents_expiring_soon: int
    coverage_compliant: bool


class ComplianceService:
    """Service for compliance document management."""
    
    EXPIRING_SOON_DAYS = 30
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_insurance_document(
        self,
        tenant_id: str,
        user_id: str,
        request: InsuranceDocumentCreateRequest
    ) -> ComplianceDocument:
        """Create an insurance document record."""
        doc = ComplianceDocument(
            tenant_id=tenant_id,
            company_id=request.company_id,
            document_type=request.document_type,
            document_name=request.document_name,
            insurance_carrier=request.insurance_carrier,
            policy_number=request.policy_number,
            coverage_amount=request.coverage_amount,
            effective_date=datetime.strptime(request.effective_date, "%Y-%m-%d").date(),
            expiration_date=datetime.strptime(request.expiration_date, "%Y-%m-%d").date(),
            document_url=request.document_url,
            status=ComplianceStatus.PENDING_REVIEW
        )
        
        self.db.add(doc)
        self.db.commit()
        return doc
    
    def create_bond_document(
        self,
        tenant_id: str,
        user_id: str,
        request: BondDocumentCreateRequest
    ) -> ComplianceDocument:
        """Create a bond document record."""
        doc = ComplianceDocument(
            tenant_id=tenant_id,
            company_id=request.company_id,
            document_type=request.document_type,
            document_name=request.document_name,
            bond_surety=request.bond_surety,
            bond_number=request.bond_number,
            bond_amount=request.bond_amount,
            effective_date=datetime.strptime(request.effective_date, "%Y-%m-%d").date(),
            expiration_date=datetime.strptime(request.expiration_date, "%Y-%m-%d").date(),
            document_url=request.document_url,
            status=ComplianceStatus.PENDING_REVIEW
        )
        
        self.db.add(doc)
        self.db.commit()
        return doc
    
    def create_license_document(
        self,
        tenant_id: str,
        user_id: str,
        request: LicenseDocumentCreateRequest
    ) -> ComplianceDocument:
        """Create a license document record."""
        doc = ComplianceDocument(
            tenant_id=tenant_id,
            company_id=request.company_id,
            document_type=request.document_type,
            document_name=request.document_name,
            license_number=request.license_number,
            license_state=request.license_state,
            license_class=request.license_class,
            effective_date=datetime.strptime(request.effective_date, "%Y-%m-%d").date(),
            expiration_date=datetime.strptime(request.expiration_date, "%Y-%m-%d").date(),
            document_url=request.document_url,
            status=ComplianceStatus.PENDING_REVIEW
        )
        
        self.db.add(doc)
        self.db.commit()
        return doc
    
    def review_document(
        self,
        tenant_id: str,
        document_id: str,
        reviewer_id: str,
        request: ReviewComplianceRequest
    ) -> ComplianceDocument:
        """Review a compliance document."""
        doc = self.db.query(ComplianceDocument).filter(
            ComplianceDocument.tenant_id == tenant_id,
            ComplianceDocument.id == document_id
        ).first()
        
        if not doc:
            raise ValueError("Document not found")
        
        doc.status = ComplianceStatus.APPROVED if request.action == "approve" else ComplianceStatus.REJECTED
        doc.reviewed_by = reviewer_id
        doc.reviewed_at = datetime.utcnow()
        doc.review_notes = request.notes
        
        self.db.commit()
        return doc
    
    def create_requirement(
        self,
        tenant_id: str,
        user_id: str,
        request: ComplianceRequirementCreateRequest
    ) -> ComplianceRequirement:
        """Create a compliance requirement for a project."""
        req = ComplianceRequirement(
            tenant_id=tenant_id,
            project_id=request.project_id,
            document_type=request.document_type,
            required=request.required,
            minimum_coverage=request.minimum_coverage,
            description=request.description
        )
        
        self.db.add(req)
        self.db.commit()
        return req
    
    def get_documents(
        self,
        tenant_id: str,
        company_id: Optional[str] = None,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        expiring_soon: bool = False
    ) -> List[ComplianceDocument]:
        """Get compliance documents with filters."""
        query = self.db.query(ComplianceDocument).filter(
            ComplianceDocument.tenant_id == tenant_id
        )
        
        if company_id:
            query = query.filter(ComplianceDocument.company_id == company_id)
        if document_type:
            query = query.filter(ComplianceDocument.document_type == document_type)
        if status:
            query = query.filter(ComplianceDocument.status == status)
        
        if expiring_soon:
            soon = date.today() + __import__('datetime').timedelta(days=self.EXPIRING_SOON_DAYS)
            query = query.filter(
                ComplianceDocument.expiration_date <= soon,
                ComplianceDocument.expiration_date >= date.today()
            )
        
        return query.order_by(ComplianceDocument.expiration_date).all()
    
    def get_company_compliance_summary(
        self,
        tenant_id: str,
        company_id: str
    ) -> ComplianceSummary:
        """Get compliance summary for a company."""
        docs = self.db.query(ComplianceDocument).filter(
            ComplianceDocument.tenant_id == tenant_id,
            ComplianceDocument.company_id == company_id
        ).all()
        
        total = len(docs)
        approved = len([d for d in docs if d.status == ComplianceStatus.APPROVED])
        expired = len([d for d in docs if d.expiration_date and d.expiration_date < date.today()])
        expiring_soon = len([d for d in docs if d.expiration_date and 
                             0 <= (d.expiration_date - date.today()).days <= self.EXPIRING_SOON_DAYS])
        
        # Determine overall status
        if expired > 0:
            overall = "non_compliant"
        elif expiring_soon > 0:
            overall = "expiring_soon"
        elif approved == total and total > 0:
            overall = "compliant"
        else:
            overall = "partial"
        
        return ComplianceSummary(
            company_id=company_id,
            company_name="",  # Would be populated from company record
            overall_status=overall,
            documents_total=total,
            documents_approved=approved,
            documents_expired=expired,
            documents_expiring_soon=expiring_soon,
            coverage_compliant=True  # Would check against requirements
        )
    
    def check_project_compliance(
        self,
        tenant_id: str,
        project_id: str,
        company_id: str
    ) -> Dict[str, Any]:
        """Check if a company meets project compliance requirements."""
        # Get project requirements
        requirements = self.db.query(ComplianceRequirement).filter(
            ComplianceRequirement.tenant_id == tenant_id,
            ComplianceRequirement.project_id == project_id,
            ComplianceRequirement.required == True
        ).all()
        
        # Get company documents
        docs = self.db.query(ComplianceDocument).filter(
            ComplianceDocument.tenant_id == tenant_id,
            ComplianceDocument.company_id == company_id,
            ComplianceDocument.status == ComplianceStatus.APPROVED
        ).all()
        
        req_met = 0
        missing = []
        expired = []
        
        for req in requirements:
            matching_doc = None
            for doc in docs:
                if doc.document_type == req.document_type:
                    matching_doc = doc
                    break
            
            if not matching_doc:
                missing.append(req.document_type)
            elif matching_doc.expiration_date and matching_doc.expiration_date < date.today():
                expired.append(req.document_type)
            else:
                req_met += 1
        
        status = "compliant" if req_met == len(requirements) else "non_compliant" if len(missing) > 0 else "expired"
        
        return {
            "company_id": company_id,
            "project_id": project_id,
            "status": status,
            "requirements_met": req_met,
            "requirements_total": len(requirements),
            "missing_documents": missing,
            "expired_documents": expired
        }
    
    def get_expiring_documents(
        self,
        tenant_id: str,
        days: int = 30
    ) -> List[ComplianceDocument]:
        """Get documents expiring within specified days."""
        soon = date.today() + __import__('datetime').timedelta(days=days)
        
        return self.db.query(ComplianceDocument).filter(
            ComplianceDocument.tenant_id == tenant_id,
            ComplianceDocument.expiration_date <= soon,
            ComplianceDocument.expiration_date >= date.today(),
            ComplianceDocument.status == ComplianceStatus.APPROVED
        ).order_by(ComplianceDocument.expiration_date).all()
    
    def update_document_status(self):
        """Update document statuses based on expiration dates."""
        today = date.today()
        soon = today + __import__('datetime').timedelta(days=self.EXPIRING_SOON_DAYS)
        
        # Mark expired documents
        expired = self.db.query(ComplianceDocument).filter(
            ComplianceDocument.expiration_date < today,
            ComplianceDocument.status.in_([ComplianceStatus.APPROVED, ComplianceStatus.EXPIRING_SOON])
        ).all()
        
        for doc in expired:
            doc.status = ComplianceStatus.EXPIRED
        
        # Mark expiring soon
        expiring = self.db.query(ComplianceDocument).filter(
            ComplianceDocument.expiration_date >= today,
            ComplianceDocument.expiration_date <= soon,
            ComplianceDocument.status == ComplianceStatus.APPROVED
        ).all()
        
        for doc in expiring:
            doc.status = ComplianceStatus.EXPIRING_SOON
        
        self.db.commit()
