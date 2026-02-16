"""
Role Mapping Module - External Group to Internal Role Mapping
Item 287: External group to role mapping
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class RoleLevel(str, Enum):
    """Role hierarchy levels"""
    SYSTEM = "system"      # Platform-wide roles
    TENANT = "tenant"      # Organization-level roles
    PROJECT = "project"    # Project-level roles
    MODULE = "module"      # Module/feature-level roles


class Permission(str, Enum):
    """Standard permissions"""
    # User management
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    
    # Project management
    PROJECTS_READ = "projects:read"
    PROJECTS_CREATE = "projects:create"
    PROJECTS_UPDATE = "projects:update"
    PROJECTS_DELETE = "projects:delete"
    
    # Document management
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_CREATE = "documents:create"
    DOCUMENTS_UPDATE = "documents:update"
    DOCUMENTS_DELETE = "documents:delete"
    
    # Financial
    FINANCIAL_READ = "financial:read"
    FINANCIAL_CREATE = "financial:create"
    FINANCIAL_APPROVE = "financial:approve"
    
    # Admin
    ADMIN_FULL = "admin:full"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_USERS = "admin:users"
    ADMIN_BILLING = "admin:billing"
    
    # Reports
    REPORTS_READ = "reports:read"
    REPORTS_CREATE = "reports:create"
    
    # Integrations
    INTEGRATIONS_READ = "integrations:read"
    INTEGRATIONS_MANAGE = "integrations:manage"


# Database Models

class Role(Base):
    """Internal role definition"""
    __tablename__ = 'roles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Role info
    name = Column(String(100), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Hierarchy
    level = Column(String(50), default=RoleLevel.TENANT.value)
    parent_role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=True)
    
    # Permissions
    permissions = Column(JSONB, default=list)
    
    # Settings
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExternalRoleMapping(Base):
    """Mapping from external groups to internal roles"""
    __tablename__ = 'external_role_mappings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # External source
    source_type = Column(String(50), nullable=False)  # saml, oidc, scim, ldap
    source_id = Column(UUID(as_uuid=True), nullable=False)  # Provider ID
    
    # External group info
    external_group_id = Column(String(255), nullable=False)
    external_group_name = Column(String(255), nullable=True)
    
    # Internal role mapping
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    
    # Additional permissions to grant
    additional_permissions = Column(JSONB, default=list)
    
    # Conditions
    conditions = Column(JSONB, default=dict)  # e.g., {"domain": "company.com"}
    
    # Status
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority wins on conflicts
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_external_mappings_tenant_source', 'tenant_id', 'source_type', 'source_id'),
        Index('ix_external_mappings_group', 'external_group_id'),
    )


class UserRoleAssignment(Base):
    """User role assignments"""
    __tablename__ = 'user_role_assignments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    
    # Assignment context
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=True)
    module = Column(String(100), nullable=True)
    
    # Source of assignment
    source = Column(String(50), default='manual')  # manual, saml, oidc, scim, api
    source_details = Column(JSONB, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    __table_args__ = (
        Index('ix_user_roles_tenant_user', 'tenant_id', 'user_id'),
        Index('ix_user_roles_user_role', 'user_id', 'role_id'),
    )


class PermissionSet(Base):
    """Predefined permission sets"""
    __tablename__ = 'permission_sets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSONB, default=list)
    
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class RoleCreateRequest(BaseModel):
    """Create role request"""
    name: str
    display_name: str
    description: Optional[str] = None
    level: RoleLevel = RoleLevel.TENANT
    permissions: List[str] = Field(default_factory=list)
    parent_role_id: Optional[str] = None


class RoleResponse(BaseModel):
    """Role response"""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    level: str
    permissions: List[str]
    is_system: bool


class ExternalRoleMappingRequest(BaseModel):
    """Create external role mapping request"""
    source_type: str  # saml, oidc, scim, ldap
    source_id: str
    external_group_id: str
    external_group_name: Optional[str] = None
    role_id: str
    additional_permissions: List[str] = Field(default_factory=list)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 0


class UserRoleAssignmentRequest(BaseModel):
    """Assign role to user request"""
    user_id: str
    role_id: str
    project_id: Optional[str] = None
    module: Optional[str] = None
    expires_at: Optional[datetime] = None


# Service Classes

class RoleService:
    """Service for role management"""
    
    # Predefined system roles
    SYSTEM_ROLES = {
        'super_admin': {
            'display_name': 'Super Administrator',
            'level': RoleLevel.SYSTEM,
            'permissions': [p.value for p in Permission]
        },
        'tenant_admin': {
            'display_name': 'Tenant Administrator',
            'level': RoleLevel.TENANT,
            'permissions': [
                Permission.USERS_READ.value,
                Permission.USERS_CREATE.value,
                Permission.USERS_UPDATE.value,
                Permission.PROJECTS_FULL.value,
                Permission.ADMIN_SETTINGS.value,
                Permission.ADMIN_USERS.value,
                Permission.ADMIN_BILLING.value
            ]
        },
        'project_manager': {
            'display_name': 'Project Manager',
            'level': RoleLevel.PROJECT,
            'permissions': [
                Permission.PROJECTS_READ.value,
                Permission.PROJECTS_UPDATE.value,
                Permission.DOCUMENTS_READ.value,
                Permission.DOCUMENTS_CREATE.value,
                Permission.DOCUMENTS_UPDATE.value,
                Permission.FINANCIAL_READ.value,
                Permission.REPORTS_READ.value,
                Permission.REPORTS_CREATE.value
            ]
        },
        'user': {
            'display_name': 'Standard User',
            'level': RoleLevel.TENANT,
            'permissions': [
                Permission.PROJECTS_READ.value,
                Permission.DOCUMENTS_READ.value,
                Permission.DOCUMENTS_CREATE.value
            ]
        },
        'viewer': {
            'display_name': 'Viewer',
            'level': RoleLevel.TENANT,
            'permissions': [
                Permission.PROJECTS_READ.value,
                Permission.DOCUMENTS_READ.value,
                Permission.REPORTS_READ.value
            ]
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def initialize_system_roles(self, tenant_id: Optional[str] = None):
        """Initialize system roles"""
        
        for role_name, role_data in self.SYSTEM_ROLES.items():
            existing = self.db.query(Role).filter(
                Role.name == role_name,
                Role.tenant_id == tenant_id,
                Role.is_system == True
            ).first()
            
            if not existing:
                role = Role(
                    tenant_id=tenant_id,
                    name=role_name,
                    display_name=role_data['display_name'],
                    level=role_data['level'].value,
                    permissions=role_data['permissions'],
                    is_system=True
                )
                self.db.add(role)
        
        self.db.commit()
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID"""
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_role_by_name(self, tenant_id: str, name: str) -> Optional[Role]:
        """Get role by name"""
        return self.db.query(Role).filter(
            Role.tenant_id == tenant_id,
            Role.name == name
        ).first()
    
    def list_roles(
        self,
        tenant_id: str,
        level: Optional[RoleLevel] = None,
        include_system: bool = True
    ) -> List[Role]:
        """List roles for tenant"""
        
        query = self.db.query(Role).filter(
            (Role.tenant_id == tenant_id) | (Role.is_system == True)
        )
        
        if level:
            query = query.filter(Role.level == level.value)
        
        if not include_system:
            query = query.filter(Role.is_system == False)
        
        return query.order_by(Role.display_name).all()
    
    def create_role(
        self,
        tenant_id: str,
        request: RoleCreateRequest,
        created_by: Optional[str] = None
    ) -> Role:
        """Create new role"""
        
        # Check for duplicate name
        existing = self.get_role_by_name(tenant_id, request.name)
        if existing:
            raise HTTPException(409, "Role with this name already exists")
        
        role = Role(
            tenant_id=tenant_id,
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            level=request.level.value,
            parent_role_id=request.parent_role_id,
            permissions=request.permissions,
            is_system=False
        )
        
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        
        return role
    
    def get_user_permissions(
        self,
        tenant_id: str,
        user_id: str,
        project_id: Optional[str] = None
    ) -> List[str]:
        """Get all permissions for a user"""
        
        permissions = set()
        
        # Get active role assignments
        query = self.db.query(UserRoleAssignment).filter(
            UserRoleAssignment.tenant_id == tenant_id,
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.is_active == True
        )
        
        if project_id:
            query = query.filter(
                (UserRoleAssignment.project_id == project_id) |
                (UserRoleAssignment.project_id.is_(None))
            )
        
        assignments = query.all()
        
        for assignment in assignments:
            role = self.get_role(str(assignment.role_id))
            if role:
                permissions.update(role.permissions or [])
        
        return list(permissions)
    
    def has_permission(
        self,
        tenant_id: str,
        user_id: str,
        permission: str,
        project_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific permission"""
        
        user_permissions = self.get_user_permissions(tenant_id, user_id, project_id)
        
        # Check for exact permission or wildcard
        if permission in user_permissions:
            return True
        
        # Check wildcard permissions (e.g., "admin:*")
        resource = permission.split(':')[0]
        wildcard = f"{resource}:*"
        if wildcard in user_permissions or Permission.ADMIN_FULL.value in user_permissions:
            return True
        
        return False


class ExternalRoleMappingService:
    """Service for external group to role mapping"""
    
    def __init__(self, db: Session):
        self.db = db
        self.role_service = RoleService(db)
    
    def create_mapping(
        self,
        tenant_id: str,
        request: ExternalRoleMappingRequest
    ) -> ExternalRoleMapping:
        """Create external role mapping"""
        
        # Validate role exists
        role = self.role_service.get_role(request.role_id)
        if not role:
            raise HTTPException(404, "Role not found")
        
        mapping = ExternalRoleMapping(
            tenant_id=tenant_id,
            source_type=request.source_type,
            source_id=request.source_id,
            external_group_id=request.external_group_id,
            external_group_name=request.external_group_name,
            role_id=request.role_id,
            additional_permissions=request.additional_permissions,
            conditions=request.conditions,
            priority=request.priority
        )
        
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        
        return mapping
    
    def get_mappings_for_source(
        self,
        tenant_id: str,
        source_type: str,
        source_id: str
    ) -> List[ExternalRoleMapping]:
        """Get all mappings for a source"""
        
        return self.db.query(ExternalRoleMapping).filter(
            ExternalRoleMapping.tenant_id == tenant_id,
            ExternalRoleMapping.source_type == source_type,
            ExternalRoleMapping.source_id == source_id,
            ExternalRoleMapping.is_active == True
        ).order_by(ExternalRoleMapping.priority.desc()).all()
    
    def map_external_groups_to_roles(
        self,
        tenant_id: str,
        source_type: str,
        source_id: str,
        external_groups: List[str],
        user_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Map external groups to internal roles"""
        
        mappings = self.get_mappings_for_source(tenant_id, source_type, source_id)
        
        role_assignments = []
        
        for group in external_groups:
            for mapping in mappings:
                if mapping.external_group_id == group:
                    # Check conditions
                    if self._check_conditions(mapping.conditions, user_context):
                        role = self.role_service.get_role(str(mapping.role_id))
                        if role:
                            permissions = list(role.permissions or [])
                            permissions.extend(mapping.additional_permissions or [])
                            
                            role_assignments.append({
                                'role_id': str(mapping.role_id),
                                'role_name': role.name,
                                'permissions': list(set(permissions)),
                                'source': source_type,
                                'external_group': group,
                                'priority': mapping.priority
                            })
        
        # Sort by priority (highest first)
        role_assignments.sort(key=lambda x: x['priority'], reverse=True)
        
        return role_assignments
    
    def _check_conditions(
        self,
        conditions: Dict[str, Any],
        user_context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if user meets mapping conditions"""
        
        if not conditions or not user_context:
            return True
        
        for key, value in conditions.items():
            if key == 'domain':
                email = user_context.get('email', '')
                if not email.endswith(f'@{value}'):
                    return False
            elif key == 'email_pattern':
                import re
                email = user_context.get('email', '')
                if not re.match(value, email):
                    return False
            elif key in user_context:
                if user_context[key] != value:
                    return False
        
        return True
    
    def apply_external_role_mappings(
        self,
        tenant_id: str,
        user_id: str,
        source_type: str,
        source_id: str,
        external_groups: List[str],
        user_context: Optional[Dict[str, Any]] = None
    ) -> List[UserRoleAssignment]:
        """Apply external role mappings to user"""
        
        assignments = []
        
        # Get role mappings
        role_mappings = self.map_external_groups_to_roles(
            tenant_id, source_type, source_id, external_groups, user_context
        )
        
        # Deactivate existing assignments from this source
        existing = self.db.query(UserRoleAssignment).filter(
            UserRoleAssignment.tenant_id == tenant_id,
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.source == source_type
        ).all()
        
        for existing_assignment in existing:
            existing_assignment.is_active = False
        
        # Create new assignments
        for mapping in role_mappings:
            assignment = UserRoleAssignment(
                tenant_id=tenant_id,
                user_id=user_id,
                role_id=mapping['role_id'],
                source=source_type,
                source_details={
                    'external_group': mapping['external_group'],
                    'source_id': source_id
                }
            )
            
            self.db.add(assignment)
            assignments.append(assignment)
        
        self.db.commit()
        
        return assignments


class PermissionService:
    """Service for permission checking and management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.role_service = RoleService(db)
    
    def check_permission(
        self,
        tenant_id: str,
        user_id: str,
        required_permission: str,
        project_id: Optional[str] = None,
        raise_exception: bool = True
    ) -> bool:
        """Check if user has required permission"""
        
        has = self.role_service.has_permission(
            tenant_id, user_id, required_permission, project_id
        )
        
        if not has and raise_exception:
            raise HTTPException(403, "Insufficient permissions")
        
        return has
    
    def check_any_permission(
        self,
        tenant_id: str,
        user_id: str,
        permissions: List[str],
        project_id: Optional[str] = None
    ) -> bool:
        """Check if user has any of the required permissions"""
        
        for permission in permissions:
            if self.role_service.has_permission(tenant_id, user_id, permission, project_id):
                return True
        
        return False
    
    def check_all_permissions(
        self,
        tenant_id: str,
        user_id: str,
        permissions: List[str],
        project_id: Optional[str] = None
    ) -> bool:
        """Check if user has all required permissions"""
        
        for permission in permissions:
            if not self.role_service.has_permission(tenant_id, user_id, permission, project_id):
                return False
        
        return True


# Export
__all__ = [
    'RoleLevel',
    'Permission',
    'Role',
    'ExternalRoleMapping',
    'UserRoleAssignment',
    'PermissionSet',
    'RoleCreateRequest',
    'RoleResponse',
    'ExternalRoleMappingRequest',
    'UserRoleAssignmentRequest',
    'RoleService',
    'ExternalRoleMappingService',
    'PermissionService'
]
