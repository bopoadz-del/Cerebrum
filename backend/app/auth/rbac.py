"""
Role-Based Access Control (RBAC) System

Provides role management, permission assignment, and access control
decision-making for Cerebrum's 14-layer architecture.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Set, Dict, Any
from enum import Enum
from dataclasses import dataclass, field

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.config import settings
from app.models.user import User, Role, user_roles_table
from app.auth.permissions import (
    LayerPermission,
    PermissionScope,
    PERMISSION_GROUPS,
    validate_permission,
    get_permission_description,
)

logger = get_logger(__name__)


class SystemRole(str, Enum):
    """System-defined roles that cannot be deleted or modified."""
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"
    SERVICE = "service"
    GUEST = "guest"


@dataclass
class RoleDefinition:
    """Definition of a role with its permissions."""
    name: str
    description: str
    permissions: List[str]
    is_system: bool = False
    is_default: bool = False


# System role definitions
SYSTEM_ROLES = {
    SystemRole.ADMIN: RoleDefinition(
        name="admin",
        description="Full system administrator with access to all layers and administrative functions",
        permissions=[p.value for p in PERMISSION_GROUPS["admin"]],
        is_system=True,
    ),
    SystemRole.ENGINEER: RoleDefinition(
        name="engineer",
        description="Engineer with full operational access to create, modify, and execute across all layers",
        permissions=[p.value for p in PERMISSION_GROUPS["engineer"]],
        is_system=True,
    ),
    SystemRole.VIEWER: RoleDefinition(
        name="viewer",
        description="Read-only viewer with access to view data across all layers",
        permissions=[p.value for p in PERMISSION_GROUPS["viewer"]],
        is_system=True,
        is_default=True,
    ),
    SystemRole.SERVICE: RoleDefinition(
        name="service",
        description="Service account for programmatic access with limited permissions",
        permissions=[
            LayerPermission.BLOCKS_READ.value,
            LayerPermission.BLOCKS_EXECUTE.value,
            LayerPermission.WAREHOUSE_READ.value,
            LayerPermission.INTERFACE_READ.value,
            LayerPermission.INTERFACE_EXECUTE.value,
        ],
        is_system=True,
    ),
    SystemRole.GUEST: RoleDefinition(
        name="guest",
        description="Guest user with minimal read-only access",
        permissions=[
            LayerPermission.INTERFACE_READ.value,
            LayerPermission.PRESENTATION_READ.value,
        ],
        is_system=True,
    ),
}


class RBACManager:
    """
    Role-Based Access Control Manager.
    
    Handles role creation, permission assignment, and access control decisions.
    """
    
    def __init__(self):
        self._role_cache: Dict[str, RoleDefinition] = {}
        self._permission_cache: Dict[uuid.UUID, Set[str]] = {}
    
    async def initialize_system_roles(self, db: AsyncSession) -> None:
        """
        Initialize system roles in the database.
        
        Args:
            db: Database session
        """
        for role_enum, role_def in SYSTEM_ROLES.items():
            # Check if role exists
            result = await db.execute(
                select(Role).where(Role.name == role_def.name)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update system role if permissions changed
                if set(existing.permissions) != set(role_def.permissions):
                    existing.permissions = role_def.permissions
                    existing.description = role_def.description
                    existing.is_system = role_def.is_system
                    logger.info(f"Updated system role: {role_def.name}")
            else:
                # Create new system role
                role = Role(
                    name=role_def.name,
                    description=role_def.description,
                    permissions=role_def.permissions,
                    is_system=role_def.is_system,
                )
                db.add(role)
                logger.info(f"Created system role: {role_def.name}")
        
        await db.flush()
    
    async def create_role(
        self,
        db: AsyncSession,
        name: str,
        description: str,
        permissions: List[str],
        created_by: Optional[uuid.UUID] = None,
    ) -> Role:
        """
        Create a new custom role.
        
        Args:
            db: Database session
            name: Role name (must be unique)
            description: Role description
            permissions: List of permission strings
            created_by: User ID who created the role
            
        Returns:
            Created Role instance
            
        Raises:
            ValueError: If role name already exists or is a system role name
        """
        # Validate role name
        if name in [r.value for r in SystemRole]:
            raise ValueError(f"Cannot create role with system name: {name}")
        
        # Check if role exists
        result = await db.execute(select(Role).where(Role.name == name))
        if result.scalar_one_or_none():
            raise ValueError(f"Role already exists: {name}")
        
        # Validate permissions
        valid_permissions = []
        for perm in permissions:
            if validate_permission(perm):
                valid_permissions.append(perm)
            else:
                logger.warning(f"Invalid permission skipped: {perm}")
        
        role = Role(
            name=name,
            description=description,
            permissions=valid_permissions,
            is_system=False,
        )
        db.add(role)
        await db.flush()
        
        logger.info(
            f"Created custom role: {name}",
            role_id=str(role.id),
            created_by=str(created_by) if created_by else None,
        )
        
        return role
    
    async def get_role(self, db: AsyncSession, role_id: uuid.UUID) -> Optional[Role]:
        """Get role by ID."""
        result = await db.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()
    
    async def get_role_by_name(self, db: AsyncSession, name: str) -> Optional[Role]:
        """Get role by name."""
        result = await db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()
    
    async def list_roles(
        self,
        db: AsyncSession,
        include_system: bool = True,
    ) -> List[Role]:
        """
        List all roles.
        
        Args:
            db: Database session
            include_system: Whether to include system roles
            
        Returns:
            List of Role instances
        """
        query = select(Role)
        if not include_system:
            query = query.where(Role.is_system == False)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_role(
        self,
        db: AsyncSession,
        role_id: uuid.UUID,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> Role:
        """
        Update a custom role.
        
        Args:
            db: Database session
            role_id: Role ID
            description: New description
            permissions: New permissions list
            
        Returns:
            Updated Role instance
            
        Raises:
            ValueError: If role is a system role
        """
        role = await self.get_role(db, role_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")
        
        if role.is_system:
            raise ValueError(f"Cannot modify system role: {role.name}")
        
        if description is not None:
            role.description = description
        
        if permissions is not None:
            valid_permissions = []
            for perm in permissions:
                if validate_permission(perm):
                    valid_permissions.append(perm)
            role.permissions = valid_permissions
        
        logger.info(f"Updated role: {role.name}", role_id=str(role_id))
        return role
    
    async def delete_role(self, db: AsyncSession, role_id: uuid.UUID) -> None:
        """
        Delete a custom role.
        
        Args:
            db: Database session
            role_id: Role ID
            
        Raises:
            ValueError: If role is a system role or has assigned users
        """
        role = await self.get_role(db, role_id)
        if not role:
            raise ValueError(f"Role not found: {role_id}")
        
        if role.is_system:
            raise ValueError(f"Cannot delete system role: {role.name}")
        
        # Check if role has users
        result = await db.execute(
            select(user_roles_table).where(user_roles_table.c.role_id == role_id)
        )
        if result.first():
            raise ValueError(f"Cannot delete role with assigned users: {role.name}")
        
        await db.delete(role)
        logger.info(f"Deleted role: {role.name}", role_id=str(role_id))
    
    async def assign_role_to_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Assign a role to a user.
        
        Args:
            db: Database session
            user_id: User ID
            role_id: Role ID
            assigned_by: User ID who assigned the role
        """
        from sqlalchemy import insert
        
        # Check if already assigned
        result = await db.execute(
            select(user_roles_table).where(
                and_(
                    user_roles_table.c.user_id == user_id,
                    user_roles_table.c.role_id == role_id,
                )
            )
        )
        if result.first():
            logger.debug(f"Role {role_id} already assigned to user {user_id}")
            return
        
        # Assign role
        await db.execute(
            insert(user_roles_table).values(
                user_id=user_id,
                role_id=role_id,
                assigned_at=datetime.utcnow(),
                assigned_by=assigned_by,
            )
        )
        
        # Invalidate cache
        self._permission_cache.pop(user_id, None)
        
        logger.info(
            f"Assigned role to user",
            role_id=str(role_id),
            user_id=str(user_id),
            assigned_by=str(assigned_by) if assigned_by else None,
        )
    
    async def remove_role_from_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> None:
        """
        Remove a role from a user.
        
        Args:
            db: Database session
            user_id: User ID
            role_id: Role ID
        """
        from sqlalchemy import delete
        
        await db.execute(
            delete(user_roles_table).where(
                and_(
                    user_roles_table.c.user_id == user_id,
                    user_roles_table.c.role_id == role_id,
                )
            )
        )
        
        # Invalidate cache
        self._permission_cache.pop(user_id, None)
        
        logger.info(
            f"Removed role from user",
            role_id=str(role_id),
            user_id=str(user_id),
        )
    
    async def get_user_permissions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Set[str]:
        """
        Get all permissions for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Set of permission strings
        """
        # Check cache
        if user_id in self._permission_cache:
            return self._permission_cache[user_id]
        
        # Get user with roles
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return set()
        
        # Collect all permissions
        permissions: Set[str] = set()
        for role in user.roles:
            permissions.update(role.permissions)
        
        # Cache permissions
        self._permission_cache[user_id] = permissions
        
        return permissions
    
    def has_permission(
        self,
        user_permissions: Set[str],
        required_permission: str,
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_permissions: Set of user permissions
            required_permission: Required permission string
            
        Returns:
            True if user has permission
        """
        # System admin has all permissions
        if LayerPermission.SYSTEM_ADMIN.value in user_permissions:
            return True
        
        return required_permission in user_permissions
    
    def has_any_permission(
        self,
        user_permissions: Set[str],
        required_permissions: List[str],
    ) -> bool:
        """
        Check if user has any of the required permissions.
        
        Args:
            user_permissions: Set of user permissions
            required_permissions: List of required permission strings
            
        Returns:
            True if user has any of the permissions
        """
        if LayerPermission.SYSTEM_ADMIN.value in user_permissions:
            return True
        
        return any(p in user_permissions for p in required_permissions)
    
    def has_all_permissions(
        self,
        user_permissions: Set[str],
        required_permissions: List[str],
    ) -> bool:
        """
        Check if user has all required permissions.
        
        Args:
            user_permissions: Set of user permissions
            required_permissions: List of required permission strings
            
        Returns:
            True if user has all permissions
        """
        if LayerPermission.SYSTEM_ADMIN.value in user_permissions:
            return True
        
        return all(p in user_permissions for p in required_permissions)
    
    async def check_layer_access(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        layer: str,
        scope: PermissionScope,
    ) -> bool:
        """
        Check if user has access to a specific layer.
        
        Args:
            db: Database session
            user_id: User ID
            layer: Layer name (e.g., "foundation")
            scope: Permission scope (e.g., PermissionScope.READ)
            
        Returns:
            True if user has access
        """
        permission = f"{layer.lower()}:{scope.value}"
        user_permissions = await self.get_user_permissions(db, user_id)
        return self.has_permission(user_permissions, permission)
    
    async def require_permission(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        permission: str,
    ) -> bool:
        """
        Require a specific permission (raises if not found).
        
        Args:
            db: Database session
            user_id: User ID
            permission: Required permission string
            
        Returns:
            True if user has permission
            
        Raises:
            PermissionError: If user doesn't have permission
        """
        user_permissions = await self.get_user_permissions(db, user_id)
        
        if not self.has_permission(user_permissions, permission):
            logger.warning(
                f"Permission denied",
                user_id=str(user_id),
                required_permission=permission,
            )
            raise PermissionError(
                f"User does not have required permission: {permission}"
            )
        
        return True
    
    async def get_user_roles(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[Role]:
        """Get all roles assigned to a user."""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return []
        
        return list(user.roles)
    
    async def has_role(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        role_name: str,
    ) -> bool:
        """Check if user has a specific role."""
        roles = await self.get_user_roles(db, user_id)
        return any(r.name == role_name for r in roles)
    
    async def set_user_roles(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        role_ids: List[uuid.UUID],
        assigned_by: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Set roles for a user (replaces existing roles).
        
        Args:
            db: Database session
            user_id: User ID
            role_ids: List of role IDs
            assigned_by: User ID who assigned the roles
        """
        from sqlalchemy import delete
        
        # Remove existing roles
        await db.execute(
            delete(user_roles_table).where(user_roles_table.c.user_id == user_id)
        )
        
        # Assign new roles
        for role_id in role_ids:
            await self.assign_role_to_user(db, user_id, role_id, assigned_by)
        
        # Invalidate cache
        self._permission_cache.pop(user_id, None)
        
        logger.info(
            f"Set user roles",
            user_id=str(user_id),
            role_count=len(role_ids),
            assigned_by=str(assigned_by) if assigned_by else None,
        )
    
    def invalidate_user_cache(self, user_id: uuid.UUID) -> None:
        """Invalidate permission cache for a user."""
        self._permission_cache.pop(user_id, None)
    
    async def get_role_permissions_summary(
        self,
        db: AsyncSession,
        role_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get permission summary for a role.
        
        Args:
            db: Database session
            role_id: Role ID
            
        Returns:
            Dictionary with permission summary
        """
        role = await self.get_role(db, role_id)
        if not role:
            return {}
        
        # Group permissions by layer
        layers: Dict[str, List[str]] = {}
        for perm in role.permissions:
            parts = perm.split(":")
            if len(parts) == 2:
                layer, scope = parts
                if layer not in layers:
                    layers[layer] = []
                layers[layer].append(scope)
        
        return {
            "role_id": str(role_id),
            "role_name": role.name,
            "total_permissions": len(role.permissions),
            "permissions_by_layer": layers,
        }


# Global RBAC manager instance
rbac_manager = RBACManager()


async def check_permission(
    db: AsyncSession,
    user_id: uuid.UUID,
    permission: str,
) -> bool:
    """
    Check if user has a specific permission (convenience function).
    
    Args:
        db: Database session
        user_id: User ID
        permission: Required permission
        
    Returns:
        True if user has permission
    """
    user_permissions = await rbac_manager.get_user_permissions(db, user_id)
    return rbac_manager.has_permission(user_permissions, permission)


async def require_admin(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """
    Require system admin permission.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        True if user is admin
        
    Raises:
        PermissionError: If user is not admin
    """
    return await rbac_manager.require_permission(
        db,
        user_id,
        LayerPermission.SYSTEM_ADMIN.value,
    )


# Permission decorators for common use cases
LAYER_PERMISSIONS = {
    "foundation": LayerPermission,
    "sensing": LayerPermission,
    "connectivity": LayerPermission,
    "edge": LayerPermission,
    "ingestion": LayerPermission,
    "stream": LayerPermission,
    "processing": LayerPermission,
    "warehouse": LayerPermission,
    "intelligence": LayerPermission,
    "blocks": LayerPermission,
    "interface": LayerPermission,
    "intelligence_services": LayerPermission,
    "presentation": LayerPermission,
    "application": LayerPermission,
}
