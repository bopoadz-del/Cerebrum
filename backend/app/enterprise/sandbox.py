"""
Sandbox Module - Isolated Sandbox Environments
Item 295: Isolated sandbox environments
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class SandboxStatus(str, Enum):
    """Sandbox environment status"""
    CREATING = "creating"
    ACTIVE = "active"
    PAUSED = "paused"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"
    FAILED = "failed"


class SandboxType(str, Enum):
    """Sandbox types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    DEMO = "demo"
    TRAINING = "training"


# Database Models

class SandboxEnvironment(Base):
    """Sandbox environment"""
    __tablename__ = 'sandbox_environments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Environment info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sandbox_type = Column(String(50), default=SandboxType.DEVELOPMENT.value)
    
    # Infrastructure
    environment_id = Column(String(255), nullable=True)  # External ID (e.g., Kubernetes namespace)
    database_name = Column(String(255), nullable=True)
    subdomain = Column(String(255), unique=True, nullable=True)
    
    # Status
    status = Column(String(50), default=SandboxStatus.CREATING.value)
    
    # Configuration
    config = Column(JSONB, default=dict)
    features_enabled = Column(JSONB, default=list)
    sample_data_loaded = Column(Boolean, default=False)
    
    # Resources
    max_projects = Column(Integer, default=5)
    max_users = Column(Integer, default=10)
    max_storage_gb = Column(Integer, default=10)
    
    # Lifecycle
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_accessed_at = Column(DateTime, nullable=True)
    destroyed_at = Column(DateTime, nullable=True)
    
    # Parent (for cloned sandboxes)
    parent_sandbox_id = Column(UUID(as_uuid=True), ForeignKey('sandbox_environments.id'), nullable=True)


class SandboxCloneRequest(Base):
    """Sandbox clone requests"""
    __tablename__ = 'sandbox_clone_requests'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_sandbox_id = Column(UUID(as_uuid=True), ForeignKey('sandbox_environments.id'), nullable=False)
    target_sandbox_id = Column(UUID(as_uuid=True), ForeignKey('sandbox_environments.id'), nullable=True)
    
    # Clone options
    include_projects = Column(Boolean, default=True)
    include_users = Column(Boolean, default=False)
    include_documents = Column(Boolean, default=True)
    include_settings = Column(Boolean, default=True)
    
    # Status
    status = Column(String(50), default='pending')
    progress_percentage = Column(Integer, default=0)
    
    # Timestamps
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class SandboxBackup(Base):
    """Sandbox backups"""
    __tablename__ = 'sandbox_backups'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sandbox_id = Column(UUID(as_uuid=True), ForeignKey('sandbox_environments.id', ondelete='CASCADE'), nullable=False)
    
    # Backup info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Storage
    backup_url = Column(String(500), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(50), default='pending')
    
    # Timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Pydantic Schemas

class CreateSandboxRequest(BaseModel):
    """Create sandbox environment"""
    name: str
    description: Optional[str] = None
    sandbox_type: SandboxType = SandboxType.DEVELOPMENT
    expires_days: Optional[int] = 30
    sample_data: bool = True
    features_enabled: List[str] = Field(default_factory=list)
    max_projects: int = 5
    max_users: int = 10


class CloneSandboxRequest(BaseModel):
    """Clone sandbox request"""
    name: str
    include_projects: bool = True
    include_users: bool = False
    include_documents: bool = True
    include_settings: bool = True


class SandboxResponse(BaseModel):
    """Sandbox response"""
    id: str
    name: str
    sandbox_type: str
    status: str
    subdomain: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime


class SandboxConfig(BaseModel):
    """Sandbox configuration"""
    database_separate: bool = True
    redis_separate: bool = True
    storage_separate: bool = True
    enable_webhooks: bool = False
    enable_email: bool = False
    enable_integrations: bool = False


# Service Classes

class SandboxService:
    """Service for sandbox environment management"""
    
    DEFAULT_FEATURES = [
        'projects',
        'documents',
        'tasks',
        'team_management',
        'reports'
    ]
    
    def __init__(self, db: Session, kubernetes_client=None):
        self.db = db
        self.k8s = kubernetes_client
    
    def create_sandbox(
        self,
        tenant_id: str,
        request: CreateSandboxRequest,
        created_by: Optional[str] = None
    ) -> SandboxEnvironment:
        """Create new sandbox environment"""
        
        # Generate unique subdomain
        subdomain = f"{tenant_id[:8]}-{str(uuid.uuid4())[:8]}-sandbox"
        
        expires_at = None
        if request.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
        
        sandbox = SandboxEnvironment(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            sandbox_type=request.sandbox_type.value,
            subdomain=subdomain,
            status=SandboxStatus.CREATING.value,
            features_enabled=request.features_enabled or self.DEFAULT_FEATURES,
            sample_data_loaded=request.sample_data,
            max_projects=request.max_projects,
            max_users=request.max_users,
            expires_at=expires_at,
            created_by=created_by
        )
        
        self.db.add(sandbox)
        self.db.commit()
        self.db.refresh(sandbox)
        
        # Provision infrastructure
        self._provision_sandbox(sandbox)
        
        return sandbox
    
    def _provision_sandbox(self, sandbox: SandboxEnvironment):
        """Provision sandbox infrastructure"""
        
        # In production, this would:
        # 1. Create Kubernetes namespace
        # 2. Deploy isolated database
        # 3. Configure networking
        # 4. Set up storage
        
        # For now, simulate provisioning
        sandbox.environment_id = f"ns-{sandbox.subdomain}"
        sandbox.database_name = f"db_{sandbox.subdomain.replace('-', '_')}"
        sandbox.status = SandboxStatus.ACTIVE.value
        
        # Load sample data if requested
        if sandbox.sample_data_loaded:
            self._load_sample_data(sandbox)
        
        self.db.commit()
    
    def _load_sample_data(self, sandbox: SandboxEnvironment):
        """Load sample data into sandbox"""
        
        # Create sample projects
        sample_projects = [
            {'name': 'Sample Construction Project', 'type': 'construction'},
            {'name': 'Demo Renovation', 'type': 'renovation'}
        ]
        
        # This would create actual records in the sandbox database
        pass
    
    def get_sandbox(self, sandbox_id: str) -> Optional[SandboxEnvironment]:
        """Get sandbox by ID"""
        return self.db.query(SandboxEnvironment).filter(
            SandboxEnvironment.id == sandbox_id
        ).first()
    
    def list_sandboxes(
        self,
        tenant_id: str,
        status: Optional[str] = None
    ) -> List[SandboxEnvironment]:
        """List sandbox environments"""
        
        query = self.db.query(SandboxEnvironment).filter(
            SandboxEnvironment.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(SandboxEnvironment.status == status)
        
        return query.order_by(SandboxEnvironment.created_at.desc()).all()
    
    def clone_sandbox(
        self,
        source_sandbox_id: str,
        request: CloneSandboxRequest,
        requested_by: str
    ) -> SandboxCloneRequest:
        """Request sandbox clone"""
        
        source = self.get_sandbox(source_sandbox_id)
        if not source:
            raise HTTPException(404, "Source sandbox not found")
        
        # Create clone request
        clone_request = SandboxCloneRequest(
            source_sandbox_id=source_sandbox_id,
            include_projects=request.include_projects,
            include_users=request.include_users,
            include_documents=request.include_documents,
            include_settings=request.include_settings,
            requested_by=requested_by
        )
        
        self.db.add(clone_request)
        self.db.commit()
        self.db.refresh(clone_request)
        
        # Start clone process
        self._execute_clone(clone_request, request.name)
        
        return clone_request
    
    def _execute_clone(self, clone_request: SandboxCloneRequest, target_name: str):
        """Execute sandbox clone"""
        
        source = self.get_sandbox(str(clone_request.source_sandbox_id))
        
        # Create target sandbox
        target = SandboxEnvironment(
            tenant_id=source.tenant_id,
            name=target_name,
            description=f"Cloned from {source.name}",
            sandbox_type=source.sandbox_type,
            parent_sandbox_id=source.id,
            status=SandboxStatus.CREATING.value
        )
        
        self.db.add(target)
        self.db.commit()
        
        clone_request.target_sandbox_id = target.id
        clone_request.status = 'in_progress'
        
        # Clone data based on options
        if clone_request.include_projects:
            self._clone_projects(source, target)
            clone_request.progress_percentage = 30
        
        if clone_request.include_documents:
            self._clone_documents(source, target)
            clone_request.progress_percentage = 60
        
        if clone_request.include_settings:
            self._clone_settings(source, target)
            clone_request.progress_percentage = 90
        
        # Complete clone
        target.status = SandboxStatus.ACTIVE.value
        clone_request.status = 'completed'
        clone_request.progress_percentage = 100
        clone_request.completed_at = datetime.utcnow()
        
        self.db.commit()
    
    def _clone_projects(self, source: SandboxEnvironment, target: SandboxEnvironment):
        """Clone projects from source to target"""
        # Implementation would copy project data
        pass
    
    def _clone_documents(self, source: SandboxEnvironment, target: SandboxEnvironment):
        """Clone documents from source to target"""
        # Implementation would copy document data
        pass
    
    def _clone_settings(self, source: SandboxEnvironment, target: SandboxEnvironment):
        """Clone settings from source to target"""
        target.config = source.config.copy()
        target.features_enabled = source.features_enabled.copy()
    
    def create_backup(
        self,
        sandbox_id: str,
        name: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> SandboxBackup:
        """Create sandbox backup"""
        
        sandbox = self.get_sandbox(sandbox_id)
        if not sandbox:
            raise HTTPException(404, "Sandbox not found")
        
        backup = SandboxBackup(
            sandbox_id=sandbox_id,
            name=name,
            description=description,
            created_by=created_by
        )
        
        self.db.add(backup)
        self.db.commit()
        self.db.refresh(backup)
        
        # Execute backup
        self._execute_backup(backup)
        
        return backup
    
    def _execute_backup(self, backup: SandboxBackup):
        """Execute sandbox backup"""
        
        sandbox = self.get_sandbox(str(backup.sandbox_id))
        
        # In production, this would:
        # 1. Dump database
        # 2. Archive files
        # 3. Upload to storage
        
        backup.status = 'completed'
        backup.completed_at = datetime.utcnow()
        backup.backup_url = f"s3://backups/{backup.id}"
        backup.size_bytes = 1024 * 1024 * 100  # Placeholder: 100MB
        
        self.db.commit()
    
    def restore_backup(
        self,
        backup_id: str,
        target_sandbox_id: str
    ):
        """Restore sandbox from backup"""
        
        backup = self.db.query(SandboxBackup).filter(
            SandboxBackup.id == backup_id
        ).first()
        
        if not backup:
            raise HTTPException(404, "Backup not found")
        
        target = self.get_sandbox(target_sandbox_id)
        if not target:
            raise HTTPException(404, "Target sandbox not found")
        
        # In production, restore from backup
        target.status = SandboxStatus.CREATING.value
        self.db.commit()
        
        # Simulate restore
        target.status = SandboxStatus.ACTIVE.value
        self.db.commit()
    
    def destroy_sandbox(self, sandbox_id: str, destroyed_by: Optional[str] = None):
        """Destroy sandbox environment"""
        
        sandbox = self.get_sandbox(sandbox_id)
        if not sandbox:
            raise HTTPException(404, "Sandbox not found")
        
        sandbox.status = SandboxStatus.DESTROYING.value
        self.db.commit()
        
        # Deprovision infrastructure
        self._deprovision_sandbox(sandbox)
        
        sandbox.status = SandboxStatus.DESTROYED.value
        sandbox.destroyed_at = datetime.utcnow()
        self.db.commit()
    
    def _deprovision_sandbox(self, sandbox: SandboxEnvironment):
        """Deprovision sandbox infrastructure"""
        
        # In production, this would:
        # 1. Delete Kubernetes namespace
        # 2. Drop database
        # 3. Remove storage
        # 4. Clean up networking
        pass
    
    def cleanup_expired_sandboxes(self):
        """Clean up expired sandbox environments"""
        
        expired = self.db.query(SandboxEnvironment).filter(
            SandboxEnvironment.expires_at < datetime.utcnow(),
            SandboxEnvironment.status.in_([
                SandboxStatus.ACTIVE.value,
                SandboxStatus.PAUSED.value
            ])
        ).all()
        
        for sandbox in expired:
            self.destroy_sandbox(str(sandbox.id))


# Export
__all__ = [
    'SandboxStatus',
    'SandboxType',
    'SandboxEnvironment',
    'SandboxCloneRequest',
    'SandboxBackup',
    'CreateSandboxRequest',
    'CloneSandboxRequest',
    'SandboxResponse',
    'SandboxConfig',
    'SandboxService'
]
