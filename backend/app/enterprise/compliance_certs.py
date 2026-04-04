"""
Compliance Certificates Module - SOC 2, ISO 27001, GDPR, HIPAA
Item 298: Compliance certifications
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from app.db.base_class import Base

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class ComplianceType(str, Enum):
    """Types of compliance certifications"""
    SOC2_TYPE1 = "soc2_type1"
    SOC2_TYPE2 = "soc2_type2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    SOC1 = "soc1"
    ISO9001 = "iso9001"
    FEDRAMP = "fedramp"
    NIST = "nist"


class CertificationStatus(str, Enum):
    """Certification status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AUDIT_SCHEDULED = "audit_scheduled"
    AUDIT_IN_PROGRESS = "audit_in_progress"
    CERTIFIED = "certified"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    RENEWAL_DUE = "renewal_due"


# Database Models

class ComplianceCertification(Base):
    """Compliance certification tracking"""
    __tablename__ = 'compliance_certifications'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Certification details
    compliance_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), default=CertificationStatus.PENDING.value)
    
    # Certification body
    certifying_body = Column(String(255), nullable=True)
    certificate_number = Column(String(255), nullable=True)
    
    # Dates
    issue_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    last_audit_date = Column(DateTime, nullable=True)
    next_audit_date = Column(DateTime, nullable=True)
    
    # Scope
    scope_description = Column(Text, nullable=True)
    covered_services = Column(JSONB, default=list)
    excluded_services = Column(JSONB, default=list)
    
    # Documents
    certificate_url = Column(String(500), nullable=True)
    audit_report_url = Column(String(500), nullable=True)
    
    # Controls
    total_controls = Column(Integer, default=0)
    compliant_controls = Column(Integer, default=0)
    non_compliant_controls = Column(Integer, default=0)
    
    # Metadata
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceControl(Base):
    """Individual compliance controls"""
    __tablename__ = 'compliance_controls'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certification_id = Column(UUID(as_uuid=True), ForeignKey('compliance_certifications.id', ondelete='CASCADE'), nullable=False)
    
    # Control details
    control_id = Column(String(100), nullable=False)
    control_name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Category
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    
    # Status
    status = Column(String(50), default='not_implemented')
    implementation_status = Column(String(50), default='pending')
    
    # Evidence
    evidence_required = Column(Boolean, default=True)
    evidence_description = Column(Text, nullable=True)
    evidence_urls = Column(JSONB, default=list)
    
    # Testing
    test_frequency = Column(String(50), default='annual')
    last_tested_at = Column(DateTime, nullable=True)
    test_results = Column(JSONB, nullable=True)
    
    # Assignments
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceEvidence(Base):
    """Compliance evidence storage"""
    __tablename__ = 'compliance_evidence'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_id = Column(UUID(as_uuid=True), ForeignKey('compliance_controls.id', ondelete='CASCADE'), nullable=False)
    
    # Evidence details
    evidence_type = Column(String(50), nullable=False)  # document, screenshot, log, config
    description = Column(Text, nullable=True)
    
    # File
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    
    # Metadata
    collected_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)
    
    # Review
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_status = Column(String(50), default='pending')
    review_notes = Column(Text, nullable=True)


class ComplianceAudit(Base):
    """Compliance audit tracking"""
    __tablename__ = 'compliance_audits'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certification_id = Column(UUID(as_uuid=True), ForeignKey('compliance_certifications.id', ondelete='CASCADE'), nullable=False)
    
    # Audit details
    audit_type = Column(String(50), nullable=False)  # internal, external, certification
    auditor_name = Column(String(255), nullable=True)
    auditor_organization = Column(String(255), nullable=True)
    
    # Dates
    scheduled_date = Column(DateTime, nullable=True)
    started_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    
    # Scope
    scope = Column(Text, nullable=True)
    controls_tested = Column(JSONB, default=list)
    
    # Results
    findings = Column(JSONB, default=list)
    overall_rating = Column(String(50), nullable=True)
    
    # Report
    report_url = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(50), default='scheduled')
    
    created_at = Column(DateTime, default=datetime.utcnow)


class GDPRDataProcessingRecord(Base):
    """GDPR Article 30 records"""
    __tablename__ = 'gdpr_processing_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Processing activity
    activity_name = Column(String(500), nullable=False)
    purpose = Column(Text, nullable=False)
    
    # Data subjects
    data_subject_categories = Column(JSONB, default=list)
    
    # Data categories
    personal_data_categories = Column(JSONB, default=list)
    special_category_data = Column(Boolean, default=False)
    
    # Recipients
    recipients = Column(JSONB, default=list)
    
    # Transfers
    international_transfers = Column(Boolean, default=False)
    transfer_safeguards = Column(Text, nullable=True)
    
    # Retention
    retention_period = Column(String(255), nullable=True)
    retention_justification = Column(Text, nullable=True)
    
    # Security measures
    security_measures = Column(Text, nullable=True)
    
    # DPO consultation
    dpo_consulted = Column(Boolean, default=False)
    dpo_comments = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Schemas

class CreateCertificationRequest(BaseModel):
    """Create compliance certification"""
    compliance_type: ComplianceType
    name: str
    description: Optional[str] = None
    certifying_body: Optional[str] = None
    scope_description: Optional[str] = None
    covered_services: List[str] = Field(default_factory=list)


class UpdateControlRequest(BaseModel):
    """Update compliance control"""
    status: Optional[str] = None
    implementation_status: Optional[str] = None
    evidence_urls: List[str] = Field(default_factory=list)


class CreateEvidenceRequest(BaseModel):
    """Add compliance evidence"""
    evidence_type: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    valid_until: Optional[datetime] = None


class CreateGDPRRecordRequest(BaseModel):
    """Create GDPR processing record"""
    activity_name: str
    purpose: str
    data_subject_categories: List[str] = Field(default_factory=list)
    personal_data_categories: List[str] = Field(default_factory=list)
    special_category_data: bool = False
    recipients: List[str] = Field(default_factory=list)
    international_transfers: bool = False
    retention_period: Optional[str] = None


class ComplianceDashboard(BaseModel):
    """Compliance dashboard data"""
    certifications: List[Dict[str, Any]]
    upcoming_audits: List[Dict[str, Any]]
    expiring_certifications: List[Dict[str, Any]]
    control_compliance: Dict[str, Any]


# Service Classes

class ComplianceService:
    """Service for compliance management"""
    
    COMPLIANCE_FRAMEWORKS = {
        ComplianceType.SOC2_TYPE2: {
            'name': 'SOC 2 Type II',
            'description': 'Service Organization Control 2 Type II',
            'controls': [
                'CC1.0', 'CC2.0', 'CC3.0', 'CC4.0', 'CC5.0',
                'CC6.0', 'CC7.0', 'CC8.0', 'CC9.0', 'CC10.0'
            ]
        },
        ComplianceType.ISO27001: {
            'name': 'ISO/IEC 27001:2013',
            'description': 'Information Security Management System',
            'controls': [
                'A.5', 'A.6', 'A.7', 'A.8', 'A.9', 'A.10',
                'A.11', 'A.12', 'A.13', 'A.14', 'A.15', 'A.16', 'A.17', 'A.18'
            ]
        },
        ComplianceType.GDPR: {
            'name': 'GDPR',
            'description': 'General Data Protection Regulation',
            'controls': [
                'Article 5', 'Article 6', 'Article 7', 'Article 8',
                'Article 13', 'Article 14', 'Article 17', 'Article 25',
                'Article 30', 'Article 32', 'Article 33', 'Article 34'
            ]
        },
        ComplianceType.HIPAA: {
            'name': 'HIPAA',
            'description': 'Health Insurance Portability and Accountability Act',
            'controls': [
                '164.308', '164.310', '164.312', '164.314', '164.316'
            ]
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_certification(
        self,
        tenant_id: Optional[str],
        request: CreateCertificationRequest
    ) -> ComplianceCertification:
        """Create compliance certification"""
        
        framework = self.COMPLIANCE_FRAMEWORKS.get(request.compliance_type, {})
        
        certification = ComplianceCertification(
            tenant_id=tenant_id,
            compliance_type=request.compliance_type.value,
            name=request.name,
            description=request.description or framework.get('description', ''),
            certifying_body=request.certifying_body,
            scope_description=request.scope_description,
            covered_services=request.covered_services,
            total_controls=len(framework.get('controls', []))
        )
        
        self.db.add(certification)
        self.db.commit()
        self.db.refresh(certification)
        
        # Create controls
        self._create_controls(certification, framework.get('controls', []))
        
        return certification
    
    def _create_controls(
        self,
        certification: ComplianceCertification,
        control_codes: List[str]
    ):
        """Create compliance controls"""
        
        for code in control_codes:
            control = ComplianceControl(
                certification_id=certification.id,
                control_id=code,
                control_name=f"Control {code}",
                category=code.split('.')[0] if '.' in code else code
            )
            self.db.add(control)
        
        self.db.commit()
    
    def get_certification(self, certification_id: str) -> Optional[ComplianceCertification]:
        """Get certification by ID"""
        return self.db.query(ComplianceCertification).filter(
            ComplianceCertification.id == certification_id
        ).first()
    
    def list_certifications(
        self,
        tenant_id: Optional[str] = None,
        compliance_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ComplianceCertification]:
        """List certifications"""
        
        query = self.db.query(ComplianceCertification)
        
        if tenant_id:
            query = query.filter(
                (ComplianceCertification.tenant_id == tenant_id) |
                (ComplianceCertification.tenant_id.is_(None))
            )
        
        if compliance_type:
            query = query.filter(
                ComplianceCertification.compliance_type == compliance_type
            )
        
        if status:
            query = query.filter(ComplianceCertification.status == status)
        
        return query.order_by(ComplianceCertification.created_at.desc()).all()
    
    def update_certification_status(
        self,
        certification_id: str,
        status: CertificationStatus,
        certificate_number: Optional[str] = None,
        issue_date: Optional[datetime] = None,
        expiration_date: Optional[datetime] = None
    ) -> ComplianceCertification:
        """Update certification status"""
        
        certification = self.get_certification(certification_id)
        if not certification:
            raise HTTPException(404, "Certification not found")
        
        certification.status = status.value
        
        if certificate_number:
            certification.certificate_number = certificate_number
        
        if issue_date:
            certification.issue_date = issue_date
        
        if expiration_date:
            certification.expiration_date = expiration_date
        
        self.db.commit()
        self.db.refresh(certification)
        
        return certification
    
    def update_control(
        self,
        control_id: str,
        request: UpdateControlRequest
    ) -> ComplianceControl:
        """Update compliance control"""
        
        control = self.db.query(ComplianceControl).filter(
            ComplianceControl.id == control_id
        ).first()
        
        if not control:
            raise HTTPException(404, "Control not found")
        
        if request.status:
            control.status = request.status
        
        if request.implementation_status:
            control.implementation_status = request.implementation_status
        
        if request.evidence_urls:
            control.evidence_urls = request.evidence_urls
        
        self.db.commit()
        self.db.refresh(control)
        
        # Update certification compliance counts
        self._update_compliance_counts(control.certification_id)
        
        return control
    
    def _update_compliance_counts(self, certification_id: str):
        """Update compliance control counts"""
        
        controls = self.db.query(ComplianceControl).filter(
            ComplianceControl.certification_id == certification_id
        ).all()
        
        certification = self.get_certification(str(certification_id))
        
        if certification:
            certification.compliant_controls = sum(
                1 for c in controls if c.status == 'compliant'
            )
            certification.non_compliant_controls = sum(
                1 for c in controls if c.status == 'non_compliant'
            )
            
            self.db.commit()
    
    def add_evidence(
        self,
        control_id: str,
        request: CreateEvidenceRequest,
        collected_by: Optional[str] = None
    ) -> ComplianceEvidence:
        """Add compliance evidence"""
        
        evidence = ComplianceEvidence(
            control_id=control_id,
            evidence_type=request.evidence_type,
            description=request.description,
            file_url=request.file_url,
            valid_until=request.valid_until,
            collected_by=collected_by
        )
        
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        
        return evidence
    
    def get_dashboard(self, tenant_id: Optional[str] = None) -> ComplianceDashboard:
        """Get compliance dashboard"""
        
        # Get certifications
        certifications = self.list_certifications(tenant_id)
        
        cert_data = [
            {
                'id': str(c.id),
                'name': c.name,
                'type': c.compliance_type,
                'status': c.status,
                'expiration_date': c.expiration_date.isoformat() if c.expiration_date else None,
                'compliance_rate': (
                    c.compliant_controls / c.total_controls * 100
                ) if c.total_controls > 0 else 0
            }
            for c in certifications
        ]
        
        # Get upcoming audits
        upcoming_audits = self.db.query(ComplianceAudit).filter(
            ComplianceAudit.scheduled_date >= datetime.utcnow(),
            ComplianceAudit.scheduled_date <= datetime.utcnow() + timedelta(days=90)
        ).order_by(ComplianceAudit.scheduled_date).limit(5).all()
        
        audit_data = [
            {
                'id': str(a.id),
                'certification': a.certification.name if a.certification else None,
                'audit_type': a.audit_type,
                'scheduled_date': a.scheduled_date.isoformat() if a.scheduled_date else None,
                'auditor': a.auditor_name
            }
            for a in upcoming_audits
        ]
        
        # Get expiring certifications
        expiring = [
            c for c in certifications
            if c.expiration_date and c.expiration_date <= datetime.utcnow() + timedelta(days=90)
        ]
        
        expiring_data = [
            {
                'id': str(c.id),
                'name': c.name,
                'expiration_date': c.expiration_date.isoformat()
            }
            for c in expiring
        ]
        
        # Calculate control compliance
        all_controls = self.db.query(ComplianceControl).join(
            ComplianceCertification
        ).filter(
            (ComplianceCertification.tenant_id == tenant_id) |
            (ComplianceCertification.tenant_id.is_(None))
        ).all()
        
        control_compliance = {
            'total': len(all_controls),
            'compliant': sum(1 for c in all_controls if c.status == 'compliant'),
            'non_compliant': sum(1 for c in all_controls if c.status == 'non_compliant'),
            'not_implemented': sum(1 for c in all_controls if c.status == 'not_implemented'),
            'in_progress': sum(1 for c in all_controls if c.status == 'in_progress')
        }
        
        return ComplianceDashboard(
            certifications=cert_data,
            upcoming_audits=audit_data,
            expiring_certifications=expiring_data,
            control_compliance=control_compliance
        )
    
    def check_expiring_certifications(self):
        """Check for expiring certifications and send alerts"""
        
        warning_date = datetime.utcnow() + timedelta(days=90)
        
        expiring = self.db.query(ComplianceCertification).filter(
            ComplianceCertification.expiration_date <= warning_date,
            ComplianceCertification.expiration_date > datetime.utcnow(),
            ComplianceCertification.status == CertificationStatus.CERTIFIED.value
        ).all()
        
        for cert in expiring:
            cert.status = CertificationStatus.RENEWAL_DUE.value
        
        self.db.commit()


class GDPRService:
    """Service for GDPR compliance"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_processing_record(
        self,
        tenant_id: str,
        request: CreateGDPRRecordRequest
    ) -> GDPRDataProcessingRecord:
        """Create GDPR Article 30 processing record"""
        
        record = GDPRDataProcessingRecord(
            tenant_id=tenant_id,
            activity_name=request.activity_name,
            purpose=request.purpose,
            data_subject_categories=request.data_subject_categories,
            personal_data_categories=request.personal_data_categories,
            special_category_data=request.special_category_data,
            recipients=request.recipients,
            international_transfers=request.international_transfers,
            retention_period=request.retention_period
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        return record
    
    def list_processing_records(
        self,
        tenant_id: str
    ) -> List[GDPRDataProcessingRecord]:
        """List GDPR processing records"""
        return self.db.query(GDPRDataProcessingRecord).filter(
            GDPRDataProcessingRecord.tenant_id == tenant_id
        ).order_by(GDPRDataProcessingRecord.created_at.desc()).all()


# Export
__all__ = [
    'ComplianceType',
    'CertificationStatus',
    'ComplianceCertification',
    'ComplianceControl',
    'ComplianceEvidence',
    'ComplianceAudit',
    'GDPRDataProcessingRecord',
    'CreateCertificationRequest',
    'UpdateControlRequest',
    'CreateEvidenceRequest',
    'CreateGDPRRecordRequest',
    'ComplianceDashboard',
    'ComplianceService',
    'GDPRService'
]
