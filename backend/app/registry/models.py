"""
Capability Registry Models

Defines the Capability model for self-coding system lifecycle management.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, JSON, Integer, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CapabilityStatus(str, Enum):
    """Lifecycle states for capabilities."""
    DRAFT = "draft"
    PENDING_VALIDATION = "pending_validation"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    DEPRECATED = "deprecated"


class CapabilityType(str, Enum):
    """Types of capabilities that can be generated."""
    API_ENDPOINT = "api_endpoint"
    REACT_COMPONENT = "react_component"
    DATABASE_MODEL = "database_model"
    MIGRATION = "migration"
    SERVICE = "service"
    UTILITY = "utility"
    INTEGRATION = "integration"


class CapabilityDB(Base):
    """SQLAlchemy model for capabilities."""
    __tablename__ = "capabilities"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    status = Column(SQLEnum(CapabilityStatus), default=CapabilityStatus.DRAFT)
    capability_type = Column(SQLEnum(CapabilityType), nullable=False)
    
    # Code artifact location
    code_artifact_url = Column(String(512), nullable=True)
    code_content = Column(String(10000), nullable=True)  # Inline storage for small modules
    
    # Metadata
    description = Column(String(1000), nullable=True)
    author = Column(String(255), nullable=False)
    
    # Dependencies
    dependencies = Column(JSON, default=list)  # List of capability IDs
    required_packages = Column(JSON, default=list)  # pip packages
    
    # Version constraints for dependencies
    dependency_constraints = Column(JSON, default=dict)
    
    # API contract (for endpoints)
    api_contract = Column(JSON, nullable=True)
    
    # Database schema (for models)
    schema_definition = Column(JSON, nullable=True)
    
    # Validation results
    validation_results = Column(JSON, nullable=True)
    security_scan_results = Column(JSON, nullable=True)
    test_results = Column(JSON, nullable=True)
    
    # Rollback info
    previous_version_id = Column(String(36), nullable=True)
    rollback_available = Column(Integer, default=0)
    
    # Metrics
    deployment_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_error_at = Column(DateTime, nullable=True)
    last_error_trace = Column(String(5000), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deployed_at = Column(DateTime, nullable=True)
    
    # A/B testing
    ab_test_group = Column(String(50), nullable=True)
    ab_test_metrics = Column(JSON, default=dict)


class Capability(BaseModel):
    """Pydantic model for capability data validation."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    status: CapabilityStatus = CapabilityStatus.DRAFT
    capability_type: CapabilityType
    
    code_artifact_url: Optional[str] = None
    code_content: Optional[str] = None
    
    description: Optional[str] = None
    author: str = Field(..., min_length=1)
    
    dependencies: List[str] = Field(default_factory=list)
    required_packages: List[str] = Field(default_factory=list)
    dependency_constraints: Dict[str, str] = Field(default_factory=dict)
    
    api_contract: Optional[Dict[str, Any]] = None
    schema_definition: Optional[Dict[str, Any]] = None
    
    validation_results: Optional[Dict[str, Any]] = None
    security_scan_results: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None
    
    previous_version_id: Optional[str] = None
    rollback_available: bool = False
    
    deployment_count: int = 0
    error_count: int = 0
    last_error_at: Optional[datetime] = None
    last_error_trace: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    
    ab_test_group: Optional[str] = None
    ab_test_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


class CapabilityCreate(BaseModel):
    """Model for creating a new capability."""
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    capability_type: CapabilityType
    description: Optional[str] = None
    author: str = Field(..., min_length=1)
    dependencies: List[str] = Field(default_factory=list)
    required_packages: List[str] = Field(default_factory=list)
    api_contract: Optional[Dict[str, Any]] = None
    schema_definition: Optional[Dict[str, Any]] = None


class CapabilityUpdate(BaseModel):
    """Model for updating a capability."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[CapabilityStatus] = None
    code_artifact_url: Optional[str] = None
    code_content: Optional[str] = None
    dependencies: Optional[List[str]] = None
    required_packages: Optional[List[str]] = None
    validation_results: Optional[Dict[str, Any]] = None
    security_scan_results: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None


class DependencyGraph(BaseModel):
    """Model for dependency resolution results."""
    capability_id: str
    dependencies: List[str]
    transitive_deps: List[str]
    circular_deps: List[List[str]]
    unresolved: List[str]
    install_order: List[str]
