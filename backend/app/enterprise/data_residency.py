"""
Data Residency Module - EU/US/Middle East Data Centers
Item 289: Data residency and regional data centers
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from app.db.base_class import Base

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, create_engine
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum
import boto3


class DataRegion(str, Enum):
    """Available data regions"""
    US_EAST = "us-east-1"           # N. Virginia
    US_WEST = "us-west-2"           # Oregon
    EU_WEST = "eu-west-1"           # Ireland
    EU_CENTRAL = "eu-central-1"     # Frankfurt
    EU_NORTH = "eu-north-1"         # Stockholm
    UK = "eu-west-2"                # London
    CA = "ca-central-1"             # Canada
    AU = "ap-southeast-2"           # Sydney
    SG = "ap-southeast-1"           # Singapore
    JP = "ap-northeast-1"           # Tokyo
    AE = "me-south-1"               # Bahrain (Middle East)
    IN = "ap-south-1"               # Mumbai


class DataClassification(str, Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# Database Models

class DataRegionConfig(Base):
    """Configuration for data regions"""
    __tablename__ = 'data_region_configs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_code = Column(String(50), unique=True, nullable=False)
    
    # Region details
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    continent = Column(String(50), nullable=False)
    
    # Infrastructure
    database_host = Column(String(255), nullable=False)
    database_port = Column(Integer, default=5432)
    database_name = Column(String(100), nullable=False)
    
    # Storage
    s3_bucket = Column(String(255), nullable=False)
    s3_region = Column(String(50), nullable=False)
    
    # CDN
    cloudfront_domain = Column(String(255), nullable=True)
    
    # Compliance
    gdpr_compliant = Column(Boolean, default=False)
    hipaa_compliant = Column(Boolean, default=False)
    soc2_compliant = Column(Boolean, default=False)
    iso27001_compliant = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Capacity
    max_tenants = Column(Integer, nullable=True)
    current_tenants = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class TenantDataResidency(Base):
    """Tenant data residency configuration"""
    __tablename__ = 'tenant_data_residency'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Primary region
    primary_region = Column(String(50), nullable=False)
    
    # Replication settings
    replicated_regions = Column(JSONB, default=list)
    replication_mode = Column(String(50), default='async')  # sync, async, none
    
    # Backup settings
    backup_enabled = Column(Boolean, default=True)
    backup_region = Column(String(50), nullable=True)
    backup_retention_days = Column(Integer, default=30)
    
    # Data classification
    default_classification = Column(String(50), default=DataClassification.INTERNAL.value)
    
    # Compliance requirements
    required_compliance = Column(JSONB, default=list)
    
    # Migration status
    migration_status = Column(String(50), nullable=True)
    migration_started_at = Column(DateTime, nullable=True)
    migration_completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DataClassificationRule(Base):
    """Rules for automatic data classification"""
    __tablename__ = 'data_classification_rules'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Classification criteria
    data_types = Column(JSONB, default=list)  # ['ssn', 'email', 'financial']
    patterns = Column(JSONB, default=list)  # regex patterns
    keywords = Column(JSONB, default=list)
    
    # Result
    classification = Column(String(50), nullable=False)
    
    # Actions
    actions = Column(JSONB, default=list)  # ['encrypt', 'notify', 'restrict_access']
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CrossBorderTransfer(Base):
    """Track cross-border data transfers"""
    __tablename__ = 'cross_border_transfers'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Transfer details
    from_region = Column(String(50), nullable=False)
    to_region = Column(String(50), nullable=False)
    
    # Data details
    data_type = Column(String(100), nullable=False)
    data_classification = Column(String(50), nullable=False)
    record_count = Column(Integer, nullable=True)
    
    # Legal basis
    legal_basis = Column(String(100), nullable=True)  # consent, contract, legitimate_interest, etc.
    dpa_reference = Column(String(255), nullable=True)
    
    # Status
    status = Column(String(50), default='pending')  # pending, approved, rejected, completed
    
    # Approvals
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Pydantic Schemas

class DataRegionResponse(BaseModel):
    """Data region response"""
    code: str
    name: str
    display_name: str
    country: str
    continent: str
    gdpr_compliant: bool
    hipaa_compliant: bool
    soc2_compliant: bool
    iso27001_compliant: bool
    is_default: bool


class TenantResidencyConfigRequest(BaseModel):
    """Configure tenant data residency"""
    primary_region: str
    replicated_regions: List[str] = Field(default_factory=list)
    replication_mode: str = 'async'
    backup_enabled: bool = True
    backup_region: Optional[str] = None
    required_compliance: List[str] = Field(default_factory=list)


class DataClassificationRequest(BaseModel):
    """Create data classification rule"""
    name: str
    description: Optional[str] = None
    data_types: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    classification: str
    actions: List[str] = Field(default_factory=list)


class CrossBorderTransferRequest(BaseModel):
    """Request cross-border data transfer"""
    to_region: str
    data_type: str
    data_classification: str
    record_count: Optional[int] = None
    legal_basis: str
    dpa_reference: Optional[str] = None


# Service Classes

class DataResidencyService:
    """Service for managing data residency"""
    
    REGION_DETAILS = {
        DataRegion.US_EAST: {
            'name': 'US East (N. Virginia)',
            'country': 'United States',
            'continent': 'North America',
            'gdpr_compliant': False,
            'hipaa_compliant': True,
            'soc2_compliant': True,
            'iso27001_compliant': True
        },
        DataRegion.US_WEST: {
            'name': 'US West (Oregon)',
            'country': 'United States',
            'continent': 'North America',
            'gdpr_compliant': False,
            'hipaa_compliant': True,
            'soc2_compliant': True,
            'iso27001_compliant': True
        },
        DataRegion.EU_WEST: {
            'name': 'EU West (Ireland)',
            'country': 'Ireland',
            'continent': 'Europe',
            'gdpr_compliant': True,
            'hipaa_compliant': False,
            'soc2_compliant': True,
            'iso27001_compliant': True
        },
        DataRegion.EU_CENTRAL: {
            'name': 'EU Central (Frankfurt)',
            'country': 'Germany',
            'continent': 'Europe',
            'gdpr_compliant': True,
            'hipaa_compliant': False,
            'soc2_compliant': True,
            'iso27001_compliant': True
        },
        DataRegion.UK: {
            'name': 'UK (London)',
            'country': 'United Kingdom',
            'continent': 'Europe',
            'gdpr_compliant': True,
            'hipaa_compliant': False,
            'soc2_compliant': True,
            'iso27001_compliant': True
        },
        DataRegion.AE: {
            'name': 'Middle East (Bahrain)',
            'country': 'Bahrain',
            'continent': 'Asia',
            'gdpr_compliant': False,
            'hipaa_compliant': False,
            'soc2_compliant': True,
            'iso27001_compliant': True
        },
        DataRegion.SG: {
            'name': 'Asia Pacific (Singapore)',
            'country': 'Singapore',
            'continent': 'Asia',
            'gdpr_compliant': False,
            'hipaa_compliant': False,
            'soc2_compliant': True,
            'iso27001_compliant': True
        },
        DataRegion.AU: {
            'name': 'Asia Pacific (Sydney)',
            'country': 'Australia',
            'continent': 'Oceania',
            'gdpr_compliant': False,
            'hipaa_compliant': False,
            'soc2_compliant': True,
            'iso27001_compliant': True
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
        self._engines = {}
    
    def list_available_regions(self) -> List[DataRegionResponse]:
        """List all available data regions"""
        
        regions = []
        
        for region_code, details in self.REGION_DETAILS.items():
            regions.append(DataRegionResponse(
                code=region_code.value,
                name=details['name'],
                display_name=details['name'],
                country=details['country'],
                continent=details['continent'],
                gdpr_compliant=details['gdpr_compliant'],
                hipaa_compliant=details['hipaa_compliant'],
                soc2_compliant=details['soc2_compliant'],
                iso27001_compliant=details['iso27001_compliant'],
                is_default=(region_code == DataRegion.US_EAST)
            ))
        
        return regions
    
    def get_region_for_tenant(self, tenant_id: str) -> Optional[str]:
        """Get primary data region for tenant"""
        
        residency = self.db.query(TenantDataResidency).filter(
            TenantDataResidency.tenant_id == tenant_id
        ).first()
        
        if residency:
            return residency.primary_region
        
        return DataRegion.US_EAST.value
    
    def configure_tenant_residency(
        self,
        tenant_id: str,
        request: TenantResidencyConfigRequest
    ) -> TenantDataResidency:
        """Configure tenant data residency"""
        
        # Validate region
        if request.primary_region not in [r.value for r in DataRegion]:
            raise HTTPException(400, "Invalid primary region")
        
        # Check compliance requirements
        region_details = self.REGION_DETAILS.get(DataRegion(request.primary_region))
        
        for compliance in request.required_compliance:
            if compliance == 'gdpr' and not region_details['gdpr_compliant']:
                raise HTTPException(400, f"Region {request.primary_region} is not GDPR compliant")
            if compliance == 'hipaa' and not region_details['hipaa_compliant']:
                raise HTTPException(400, f"Region {request.primary_region} is not HIPAA compliant")
        
        # Get or create residency config
        residency = self.db.query(TenantDataResidency).filter(
            TenantDataResidency.tenant_id == tenant_id
        ).first()
        
        if not residency:
            residency = TenantDataResidency(tenant_id=tenant_id)
            self.db.add(residency)
        
        residency.primary_region = request.primary_region
        residency.replicated_regions = request.replicated_regions
        residency.replication_mode = request.replication_mode
        residency.backup_enabled = request.backup_enabled
        residency.backup_region = request.backup_region
        residency.required_compliance = request.required_compliance
        
        self.db.commit()
        self.db.refresh(residency)
        
        return residency
    
    def get_database_session(self, tenant_id: str) -> Session:
        """Get database session for tenant's region"""
        
        region = self.get_region_for_tenant(tenant_id)
        
        if region not in self._engines:
            # Create engine for region
            config = self.db.query(DataRegionConfig).filter(
                DataRegionConfig.region_code == region
            ).first()
            
            if not config:
                raise HTTPException(500, f"Region configuration not found: {region}")
            
            db_url = f"postgresql://{config.database_host}:{config.database_port}/{config.database_name}"
            self._engines[region] = create_engine(db_url)
        
        SessionLocal = sessionmaker(bind=self._engines[region])
        return SessionLocal()
    
    def get_storage_bucket(self, tenant_id: str) -> str:
        """Get S3 bucket for tenant's region"""
        
        region = self.get_region_for_tenant(tenant_id)
        
        config = self.db.query(DataRegionConfig).filter(
            DataRegionConfig.region_code == region
        ).first()
        
        if not config:
            raise HTTPException(500, f"Region configuration not found: {region}")
        
        return config.s3_bucket


class DataClassificationService:
    """Service for data classification"""
    
    PII_PATTERNS = {
        'ssn': r'^\d{3}-\d{2}-\d{4}$',
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^\+?1?\d{9,15}$',
        'credit_card': r'^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$',
        'bank_account': r'^\d{8,17}$'
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_classification_rule(
        self,
        tenant_id: str,
        request: DataClassificationRequest
    ) -> DataClassificationRule:
        """Create data classification rule"""
        
        rule = DataClassificationRule(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            data_types=request.data_types,
            patterns=request.patterns,
            keywords=request.keywords,
            classification=request.classification,
            actions=request.actions
        )
        
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        return rule
    
    def classify_data(
        self,
        tenant_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify data based on rules"""
        
        # Get active rules
        rules = self.db.query(DataClassificationRule).filter(
            DataClassificationRule.tenant_id == tenant_id,
            DataClassificationRule.is_active == True
        ).all()
        
        classifications = {}
        
        for field_name, value in data.items():
            field_classification = DataClassification.INTERNAL.value
            matched_rules = []
            
            for rule in rules:
                if self._matches_rule(value, rule):
                    field_classification = rule.classification
                    matched_rules.append(rule.name)
            
            # Also check built-in patterns
            if isinstance(value, str):
                for pattern_name, pattern in self.PII_PATTERNS.items():
                    import re
                    if re.match(pattern, value):
                        field_classification = DataClassification.CONFIDENTIAL.value
                        matched_rules.append(f'pattern:{pattern_name}')
            
            classifications[field_name] = {
                'classification': field_classification,
                'matched_rules': matched_rules
            }
        
        return classifications
    
    def _matches_rule(self, value: Any, rule: DataClassificationRule) -> bool:
        """Check if value matches classification rule"""
        
        if not isinstance(value, str):
            return False
        
        # Check keywords
        for keyword in (rule.keywords or []):
            if keyword.lower() in value.lower():
                return True
        
        # Check patterns
        import re
        for pattern in (rule.patterns or []):
            if re.search(pattern, value):
                return True
        
        return False


class CrossBorderTransferService:
    """Service for managing cross-border data transfers"""
    
    RESTRICTED_TRANSFERS = [
        # EU to non-adequate countries without safeguards
        ('eu-west-1', 'us-east-1'),
        ('eu-central-1', 'us-east-1'),
        # Add more restrictions as needed
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def request_transfer(
        self,
        tenant_id: str,
        user_id: str,
        request: CrossBorderTransferRequest
    ) -> CrossBorderTransfer:
        """Request cross-border data transfer"""
        
        # Get tenant's primary region
        residency = self.db.query(TenantDataResidency).filter(
            TenantDataResidency.tenant_id == tenant_id
        ).first()
        
        from_region = residency.primary_region if residency else DataRegion.US_EAST.value
        
        # Check if transfer is restricted
        is_restricted = (from_region, request.to_region) in self.RESTRICTED_TRANSFERS
        
        transfer = CrossBorderTransfer(
            tenant_id=tenant_id,
            from_region=from_region,
            to_region=request.to_region,
            data_type=request.data_type,
            data_classification=request.data_classification,
            record_count=request.record_count,
            legal_basis=request.legal_basis,
            dpa_reference=request.dpa_reference,
            requested_by=user_id,
            status='pending' if is_restricted else 'approved'
        )
        
        if not is_restricted:
            transfer.approved_at = datetime.utcnow()
        
        self.db.add(transfer)
        self.db.commit()
        self.db.refresh(transfer)
        
        return transfer
    
    def approve_transfer(
        self,
        transfer_id: str,
        approver_id: str
    ) -> CrossBorderTransfer:
        """Approve cross-border transfer"""
        
        transfer = self.db.query(CrossBorderTransfer).filter(
            CrossBorderTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise HTTPException(404, "Transfer not found")
        
        if transfer.status != 'pending':
            raise HTTPException(400, "Transfer is not pending approval")
        
        transfer.status = 'approved'
        transfer.approved_by = approver_id
        transfer.approved_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(transfer)
        
        return transfer
    
    def complete_transfer(self, transfer_id: str) -> CrossBorderTransfer:
        """Mark transfer as completed"""
        
        transfer = self.db.query(CrossBorderTransfer).filter(
            CrossBorderTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            raise HTTPException(404, "Transfer not found")
        
        transfer.status = 'completed'
        transfer.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(transfer)
        
        return transfer


# Export
__all__ = [
    'DataRegion',
    'DataClassification',
    'DataRegionConfig',
    'TenantDataResidency',
    'DataClassificationRule',
    'CrossBorderTransfer',
    'DataRegionResponse',
    'TenantResidencyConfigRequest',
    'DataClassificationRequest',
    'CrossBorderTransferRequest',
    'DataResidencyService',
    'DataClassificationService',
    'CrossBorderTransferService'
]
