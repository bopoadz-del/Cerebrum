"""
Role-Based Access Control (RBAC)

Provides role-based permission checking with decorator support
and role hierarchy.
"""

import functools
from enum import Enum
from typing import Callable, List, Optional, Set, TypeVar, cast

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db_session

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., object])


class Role(str, Enum):
    """System role enumeration."""
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"


class Permission(str, Enum):
    """System permission enumeration."""
    # User permissions
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"
    
    # Project permissions
    PROJECTS_READ = "projects:read"
    PROJECTS_WRITE = "projects:write"
    PROJECTS_DELETE = "projects:delete"
    
    # Task permissions
    TASKS_READ = "tasks:read"
    TASKS_WRITE = "tasks:write"
    TASKS_DELETE = "tasks:delete"
    
    # Settings permissions
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    
    # Admin permissions
    ADMIN_ACCESS = "admin:access"
    AUDIT_READ = "audit:read"


# Role hierarchy - higher roles inherit lower role permissions
ROLE_HIERARCHY: dict[Role, List[Role]] = {
    Role.SUPERADMIN: [Role.ADMIN, Role.MANAGER, Role.USER, Role.VIEWER],
    Role.ADMIN: [Role.MANAGER, Role.USER, Role.VIEWER],
    Role.MANAGER: [Role.USER, Role.VIEWER],
    Role.USER: [Role.VIEWER],
    Role.VIEWER: [],
}

# Default permissions per role
ROLE_PERMISSIONS: dict[Role, List[Permission]] = {
    Role.SUPERADMIN: [Permission.ADMIN_ACCESS],  # Superadmin has all permissions
    Role.ADMIN: [
        Permission.USERS_READ, Permission.USERS_WRITE, Permission.USERS_DELETE,
        Permission.PROJECTS_READ, Permission.PROJECTS_WRITE, Permission.PROJECTS_DELETE,
        Permission.TASKS_READ, Permission.TASKS_WRITE, Permission.TASKS_DELETE,
        Permission.SETTINGS_READ, Permission.SETTINGS_WRITE,
        Permission.AUDIT_READ,
    ],
    Role.MANAGER: [
        Permission.USERS_READ,
        Permission.PROJECTS_READ, Permission.PROJECTS_WRITE,
        Permission.TASKS_READ, Permission.TASKS_WRITE, Permission.TASKS_DELETE,
    ],
    Role.USER: [
        Permission.PROJECTS_READ,
        Permission.TASKS_READ, Permission.TASKS_WRITE,
    ],
    Role.VIEWER: [
        Permission.PROJECTS_READ,
        Permission.TASKS_READ,
    ],
}


class RBACError(Exception):
    """RBAC-related error."""
    pass


class PermissionDeniedError(RBACError):
    """Permission denied error."""
    pass


class RBACManager:
    """
    Role-Based Access Control manager.
    
    Manages role permissions and provides permission checking
    with role hierarchy support.
    """
    
    def __init__(self) -> None:
        """Initialize RBAC manager."""
        self._role_hierarchy = ROLE_HIERARCHY
        self._role_permissions = ROLE_PERMISSIONS
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """
        Get all permissions for a role including inherited ones.
        
        Args:
            role: User role
            
        Returns:
            Set of permissions
        """
        permissions: Set[Permission] = set()
        
        # Add direct permissions
        permissions.update(self._role_permissions.get(role, []))
        
        # Add inherited permissions from hierarchy
        for inherited_role in self._role_hierarchy.get(role, []):
            permissions.update(self._role_permissions.get(inherited_role, []))
        
        return permissions
    
    def has_permission(
        self,
        user_role: Role,
        required_permission: Permission,
    ) -> bool:
        """
        Check if role has specific permission.
        
        Args:
            user_role: User's role
            required_permission: Required permission
            
        Returns:
            True if role has permission
        """
        # Superadmin has all permissions
        if user_role == Role.SUPERADMIN:
            return True
        
        permissions = self.get_role_permissions(user_role)
        return required_permission in permissions
    
    def has_any_permission(
        self,
        user_role: Role,
        required_permissions: List[Permission],
    ) -> bool:
        """
        Check if role has any of the required permissions.
        
        Args:
            user_role: User's role
            required_permissions: List of required permissions
            
        Returns:
            True if role has any permission
        """
        return any(
            self.has_permission(user_role, perm)
            for perm in required_permissions
        )
    
    def has_all_permissions(
        self,
        user_role: Role,
        required_permissions: List[Permission],
    ) -> bool:
        """
        Check if role has all required permissions.
        
        Args:
            user_role: User's role
            required_permissions: List of required permissions
            
        Returns:
            True if role has all permissions
        """
        return all(
            self.has_permission(user_role, perm)
            for perm in required_permissions
        )
    
    def require_permission(self, permission: Permission) -> Callable[[F], F]:
        """
        Decorator to require specific permission.
        
        Args:
            permission: Required permission
            
        Returns:
            Decorator function
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(*args: object, **kwargs: object) -> object:
                # Get request from kwargs or args
                request = kwargs.get('request')
                if not request:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                
                if not request:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Request object not found",
                    )
                
                # Get user from request state
                user = getattr(request.state, 'user', None)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )
                
                user_role = getattr(user, 'role', None)
                if not user_role:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User role not found",
                    )
                
                if not self.has_permission(Role(user_role), permission):
                    logger.warning(
                        f"Permission denied",
                        user_id=user.id,
                        required=permission,
                        role=user_role,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission}",
                    )
                
                return await func(*args, **kwargs)
            
            return cast(F, wrapper)
        return decorator
    
    def require_role(self, *roles: Role) -> Callable[[F], F]:
        """
        Decorator to require specific role(s).
        
        Args:
            *roles: Required roles
            
        Returns:
            Decorator function
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(*args: object, **kwargs: object) -> object:
                request = kwargs.get('request')
                if not request:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                
                if not request:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Request object not found",
                    )
                
                user = getattr(request.state, 'user', None)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )
                
                user_role = getattr(user, 'role', None)
                if not user_role or Role(user_role) not in roles:
                    logger.warning(
                        f"Role requirement not met",
                        user_id=user.id,
                        required=[r.value for r in roles],
                        actual=user_role,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions",
                    )
                
                return await func(*args, **kwargs)
            
            return cast(F, wrapper)
        return decorator


# Global RBAC manager instance
rbac = RBACManager()


def require_permission(permission: Permission) -> Callable[[F], F]:
    """Require permission decorator convenience function."""
    return rbac.require_permission(permission)


def require_role(*roles: Role) -> Callable[[F], F]:
    """Require role decorator convenience function."""
    return rbac.require_role(*roles)


def check_permission(user_role: str, permission: Permission) -> bool:
    """Check permission convenience function."""
    try:
        return rbac.has_permission(Role(user_role), permission)
    except ValueError:
        return False
