"""
Tenant Isolation Module - Complete Data Isolation with Row-Level Security
Item 281: Multi-tenancy with tenant isolation
"""

from typing import Optional, List, Dict, Any, Callable
from functools import wraps
from contextvars import ContextVar
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, Index, Integer,
    event, text, inspect, create_engine
)
from sqlalchemy.orm import Session, declared_attr
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.dialects.postgresql import UUID, JSONB
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pydantic import BaseModel
from app.db.base_class import Base
from app.core.deps import get_db
from app.core.config import settings

# Get secret key from settings - must be configured
SECRET_KEY = settings.SECRET_KEY

# Context variable for current tenant
tenant_context: ContextVar[Optional[str]] = ContextVar('tenant_context', default=None)


class TenantTier(str, Enum):
    """Tenant subscription tiers"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class TenantStatus(str, Enum):
    """Tenant account statuses"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class DataResidencyRegion(str, Enum):
    """Data residency regions"""
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    EU_CENTRAL = "eu-central"
    UK = "uk"
    CA = "ca"
    AU = "au"
    AE = "ae"  # UAE/Middle East
    SG = "sg"  # Singapore/APAC


# Base model with tenant isolation


class TenantMixin:
    """Mixin to add tenant_id to all models"""
    
    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True), 
            ForeignKey('tenants.id', ondelete='CASCADE'),
            nullable=False,
            index=True
        )


class Tenant(Base):
    """Tenant/Organization model"""
    __tablename__ = 'tenants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Subscription & Billing
    tier = Column(String(50), default=TenantTier.STARTER.value)
    status = Column(String(50), default=TenantStatus.PENDING.value)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    
    # Data Residency
    data_region = Column(String(50), default=DataResidencyRegion.US_EAST.value)
    database_shard = Column(String(100), nullable=True)
    
    # White-labeling
    custom_domain = Column(String(255), nullable=True, unique=True)
    brand_colors = Column(JSONB, default=dict)
    logo_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    custom_css = Column(String(10000), nullable=True)
    
    # Security Settings
    sso_enabled = Column(Boolean, default=False)
    sso_provider = Column(String(100), nullable=True)
    sso_config = Column(JSONB, default=dict)
    mfa_required = Column(Boolean, default=False)
    ip_allowlist = Column(JSONB, default=list)
    password_policy = Column(JSONB, default=dict)
    session_timeout_minutes = Column(Integer, default=480)
    
    # Features & Limits
    features = Column(JSONB, default=dict)
    usage_limits = Column(JSONB, default=dict)
    current_usage = Column(JSONB, default=dict)
    
    # Metadata
    settings = Column(JSONB, default=dict)
    metadata = Column(JSONB, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trial_ends_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_tenants_status_tier', 'status', 'tier'),
        Index('ix_tenants_data_region', 'data_region'),
    )


class TenantUser(Base):
    """User-tenant membership with roles"""
    __tablename__ = 'tenant_users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Role within tenant
    role = Column(String(50), default='member')
    permissions = Column(JSONB, default=list)
    
    # External SSO mapping
    external_id = Column(String(255), nullable=True)
    sso_group_mappings = Column(JSONB, default=list)
    
    # Status
    is_active = Column(Boolean, default=True)
    invited_at = Column(DateTime, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_tenant_users_tenant_user', 'tenant_id', 'user_id', unique=True),
        Index('ix_tenant_users_user_tenant', 'user_id', 'tenant_id'),
    )


class TenantAuditLog(Base):
    """Audit log for tenant activities"""
    __tablename__ = 'tenant_audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_audit_logs_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_audit_logs_action', 'action'),
    )


# Row-Level Security Functions

def set_tenant_rls_policy(session: Session, tenant_id: str):
    """Set RLS policy for current session"""
    session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant_id}
    )


def enable_rls_on_table(connection, table_name: str):
    """Enable RLS on a table"""
    connection.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    
    # Create policy
    policy_sql = f"""
    CREATE POLICY tenant_isolation_policy ON {table_name}
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID)
    """
    connection.execute(text(policy_sql))


def create_tenant_rls_trigger():
    """Create trigger function for automatic tenant_id assignment"""
    return """
    CREATE OR REPLACE FUNCTION set_tenant_id()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.tenant_id IS NULL THEN
            NEW.tenant_id := current_setting('app.current_tenant_id', true)::UUID;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """


# Tenant Context Manager

class TenantContext:
    """Context manager for tenant isolation"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.token = None
    
    def __enter__(self):
        self.token = tenant_context.set(self.tenant_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        tenant_context.reset(self.token)


def get_current_tenant_id() -> Optional[str]:
    """Get current tenant ID from context"""
    return tenant_context.get()


# Decorators

def with_tenant(tenant_id: str):
    """Decorator to run function within tenant context"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with TenantContext(tenant_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def require_tenant_access(roles: List[str] = None):
    """Decorator to require tenant access with specific roles"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_id = get_current_tenant_id()
            if not tenant_id:
                raise HTTPException(status_code=403, detail="No tenant context")
            
            # Check role permissions here
            if roles:
                user_role = kwargs.get('current_user', {}).get('role')
                if user_role not in roles:
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# FastAPI Dependencies

security = HTTPBearer()


async def get_current_tenant(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Tenant:
    """Extract and validate tenant from request"""
    
    # Try custom domain first
    host = request.headers.get('host', '')
    tenant = db.query(Tenant).filter(Tenant.custom_domain == host).first()
    
    if not tenant:
        # Try from JWT token
        try:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            tenant_id = payload.get('tenant_id')
            if tenant_id:
                tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        except jwt.InvalidTokenError:
            pass
    
    if not tenant:
        # Try from header
        tenant_id = request.headers.get('X-Tenant-ID')
        if tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant or tenant.status != TenantStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="Invalid or inactive tenant")
    
    # Set tenant context
    tenant_context.set(str(tenant.id))
    
    return tenant


# Tenant-Aware Query Builder

class TenantQueryBuilder:
    """Build queries with automatic tenant filtering"""
    
    def __init__(self, session: Session, model_class):
        self.session = session
        self.model = model_class
        self.tenant_id = get_current_tenant_id()
    
    def query(self):
        """Get base query filtered by tenant"""
        q = self.session.query(self.model)
        if self.tenant_id and hasattr(self.model, 'tenant_id'):
            q = q.filter(self.model.tenant_id == self.tenant_id)
        return q
    
    def get(self, id: str):
        """Get by ID with tenant filter"""
        q = self.query()
        return q.filter(self.model.id == id).first()
    
    def filter_by(self, **kwargs):
        """Filter with tenant isolation"""
        q = self.query()
        return q.filter_by(**kwargs)
    
    def create(self, **kwargs):
        """Create with tenant_id auto-set"""
        if self.tenant_id and hasattr(self.model, 'tenant_id'):
            kwargs['tenant_id'] = self.tenant_id
        instance = self.model(**kwargs)
        self.session.add(instance)
        return instance


# Tenant Usage Tracking

class TenantUsageTracker:
    """Track and enforce tenant usage limits"""
    
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    def check_limit(self, resource: str, amount: int = 1) -> bool:
        """Check if usage is within limits"""
        limits = self.tenant.usage_limits or {}
        current = self.tenant.current_usage or {}
        
        limit = limits.get(resource)
        used = current.get(resource, 0)
        
        if limit is None:
            return True
        
        return (used + amount) <= limit
    
    def increment_usage(self, resource: str, amount: int = 1):
        """Increment usage counter"""
        current = self.tenant.current_usage or {}
        current[resource] = current.get(resource, 0) + amount
        self.tenant.current_usage = current
        self.db.commit()
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get usage report for tenant"""
        limits = self.tenant.usage_limits or {}
        current = self.tenant.current_usage or {}
        
        report = {}
        for resource, limit in limits.items():
            used = current.get(resource, 0)
            report[resource] = {
                'limit': limit,
                'used': used,
                'remaining': max(0, limit - used),
                'percentage': (used / limit * 100) if limit > 0 else 0
            }
        
        return report


# Cross-tenant operations (for super admins)

class CrossTenantManager:
    """Manage operations across multiple tenants (super admin only)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_all_tenants(
        self, 
        status: Optional[str] = None,
        tier: Optional[str] = None,
        region: Optional[str] = None
    ) -> List[Tenant]:
        """List all tenants with optional filtering"""
        query = self.db.query(Tenant)
        
        if status:
            query = query.filter(Tenant.status == status)
        if tier:
            query = query.filter(Tenant.tier == tier)
        if region:
            query = query.filter(Tenant.data_region == region)
        
        return query.all()
    
    def migrate_tenant_data(self, from_tenant_id: str, to_tenant_id: str):
        """Migrate data between tenants"""
        # Implementation for data migration
        pass
    
    def clone_tenant_config(self, source_tenant_id: str, target_tenant_id: str):
        """Clone tenant configuration"""
        source = self.db.query(Tenant).filter(Tenant.id == source_tenant_id).first()
        target = self.db.query(Tenant).filter(Tenant.id == target_tenant_id).first()
        
        if source and target:
            target.features = source.features
            target.usage_limits = source.usage_limits
            target.settings = source.settings
            self.db.commit()


# Database sharding support

class ShardRouter:
    """Route database queries to appropriate shard"""
    
    def __init__(self, shard_map: Dict[str, str]):
        self.shard_map = shard_map
        self.engines = {}
    
    def get_engine(self, tenant_id: str):
        """Get database engine for tenant"""
        shard = self.shard_map.get(tenant_id, 'default')
        if shard not in self.engines:
            self.engines[shard] = create_engine(shard)
        return self.engines[shard]
    
    def get_session(self, tenant_id: str) -> Session:
        """Get session for tenant's shard"""
        engine = self.get_engine(tenant_id)
        return Session(bind=engine)


# Export
__all__ = [
    'Tenant',
    'TenantUser', 
    'TenantAuditLog',
    'TenantTier',
    'TenantStatus',
    'DataResidencyRegion',
    'TenantContext',
    'TenantQueryBuilder',
    'TenantUsageTracker',
    'CrossTenantManager',
    'ShardRouter',
    'get_current_tenant_id',
    'with_tenant',
    'require_tenant_access',
    'get_current_tenant',
    'set_tenant_rls_policy',
    'enable_rls_on_table',
]
