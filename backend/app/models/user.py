"""
User Model

SQLAlchemy model for user management with UUID primary keys,
role-based access, tenant isolation, and MFA support.
"""

import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import BaseModel
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.models.audit import AuditLog

logger = get_logger(__name__)

# Association table for user roles
user_roles_table = Table(
    "user_roles",
    BaseModel.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), default=datetime.utcnow),
    Column("assigned_by", UUID(as_uuid=True), nullable=True),
)


class Role(BaseModel):
    """
    Role model for RBAC.
    
    Defines roles with associated permissions for access control.
    """
    
    __tablename__ = "roles"
    
    # Override id from BaseModel to prevent soft delete
    deleted_at = None  # Roles don't support soft delete
    
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_roles_table,
        back_populates="roles",
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"
    
    def to_dict(self) -> dict:
        """Convert role to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(BaseModel):
    """
    User model with authentication and authorization support.
    
    Attributes:
        id: UUID primary key
        email: Unique email address
        hashed_password: Bcrypt hashed password
        full_name: User's full name
        role: Primary role for quick access
        tenant_id: Tenant ID for multi-tenancy
        is_active: Whether account is active
        is_verified: Whether email is verified
        mfa_enabled: Whether MFA is enabled
        mfa_secret: TOTP secret for MFA
        roles: Many-to-many relationship with Role
    """
    
    __tablename__ = "users"
    
    # Authentication fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Role and tenant
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    
    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # MFA fields
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mfa_backup_codes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    mfa_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Security fields
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Preferences
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=user_roles_table,
        back_populates="users",
        lazy="selectin",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        lazy="selectin",
    )
    
    def __init__(self, **kwargs):
        """Initialize user with proper defaults."""
        # Set defaults before calling super to ensure test-time creation works
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        if "is_verified" not in kwargs:
            kwargs["is_verified"] = False
        if "mfa_enabled" not in kwargs:
            kwargs["mfa_enabled"] = False
        if "failed_login_attempts" not in kwargs:
            kwargs["failed_login_attempts"] = 0
        if "role" not in kwargs:
            kwargs["role"] = "user"
        if "timezone" not in kwargs:
            kwargs["timezone"] = "UTC"
        if "language" not in kwargs:
            kwargs["language"] = "en"
        if "preferences" not in kwargs:
            kwargs["preferences"] = {}
        if "tenant_id" not in kwargs:
            # Generate a default tenant_id if not provided
            kwargs["tenant_id"] = uuid.uuid4()
        super().__init__(**kwargs)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    @property
    def can_login(self) -> bool:
        """Check if user can login."""
        return self.is_active and not self.is_deleted and not self.is_locked
    
    @property
    def all_permissions(self) -> list:
        """Get all permissions from all roles."""
        permissions = set()
        for role in self.roles:
            permissions.update(role.permissions)
        return list(permissions)
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has specific role."""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.all_permissions
    
    def record_login(self, ip_address: Optional[str] = None) -> None:
        """Record successful login."""
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def record_failed_login(self, max_attempts: int = 5, lock_duration_minutes: int = 30) -> None:
        """Record failed login attempt."""
        # Handle None case for safety
        current_attempts = self.failed_login_attempts or 0
        self.failed_login_attempts = current_attempts + 1
        
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lock_duration_minutes)
            logger.warning(
                f"User account locked",
                user_id=str(self.id),
                attempts=self.failed_login_attempts,
                locked_until=self.locked_until.isoformat(),
            )
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive fields
            
        Returns:
            User dictionary
        """
        data = {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "tenant_id": str(self.tenant_id),
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "mfa_enabled": self.mfa_enabled,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "avatar_url": self.avatar_url,
            "timezone": self.timezone,
            "language": self.language,
            "roles": [role.to_dict() for role in self.roles],
        }
        
        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None,
                "preferences": self.preferences,
            })
        
        return data
    
    def to_public_dict(self) -> dict:
        """Convert user to public dictionary (minimal info)."""
        return {
            "id": str(self.id),
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
        }


class APIKey(BaseModel):
    """
    API Key model for programmatic access.
    
    Allows users to create API keys for service-to-service
    authentication.
    """
    
    __tablename__ = "api_keys"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    scopes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", backref="api_keys")
    
    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, user_id={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if self.expires_at and self.expires_at < datetime.utcnow():
            return True
        return False
    
    @property
    def is_valid(self) -> bool:
        """Check if API key is valid for use."""
        return self.is_active and not self.is_deleted and not self.is_expired
    
    def record_usage(self) -> None:
        """Record API key usage."""
        self.last_used_at = datetime.utcnow()
