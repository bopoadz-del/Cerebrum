"""
API Dependencies

Provides reusable dependencies for authentication, authorization,
and database session management across all API endpoints.
"""

from typing import Optional, List

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.jwt import decode_token, TokenExpiredError, InvalidTokenError
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import db_manager
from app.models.user import User

logger = get_logger(__name__)

# HTTP Bearer token scheme
token_scheme = HTTPBearer(auto_error=False)


# =============================================================================
# Database Session Dependency
# =============================================================================

async def get_db_session() -> AsyncSession:
    """
    Get database session with automatic rollback on error.
    
    D10: Safe DB Session Rollback Pattern
    """
    async with db_manager.async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(token_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Authorization credentials
        db: Database session
        
    Returns:
        Authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        payload = decode_token(token, token_type="access")
        user_id = payload.sub
        
        # Fetch user from database
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )
        
        return user
        
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current authenticated user with admin privileges.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User if they are an admin
        
    Raises:
        HTTPException: If user is not an admin
    """
    # Check if user has admin role
    is_admin = False
    if current_user.roles:
        for role in current_user.roles:
            if role.name.lower() in ("admin", "superadmin", "administrator"):
                is_admin = True
                break
    
    # Also check permissions
    if not is_admin and current_user.permissions:
        if "admin:read" in current_user.permissions or "admin:write" in current_user.permissions:
            is_admin = True
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    
    return current_user


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(token_scheme),
) -> str:
    """
    Get current user ID from JWT token.
    
    Lightweight alternative to get_current_user that doesn't hit the database.
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        User ID string
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        payload = decode_token(token, token_type="access")
        return payload.sub
        
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# B5: Role-Based Access Control (RBAC)
# =============================================================================

class RoleChecker:
    """
    Role-based permission checker.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_permission("admin:read"))])
        async def admin_endpoint():
            return {"ok": True}
    """
    
    def __init__(self, required_permission: str):
        """
        Initialize role checker.
        
        Args:
            required_permission: Required permission (e.g., "admin:read", "user:write")
        """
        self.required_permission = required_permission
    
    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        """
        Check if user has required permission.
        
        Args:
            user: Current authenticated user
            
        Returns:
            User if authorized
            
        Raises:
            HTTPException: If user lacks permission
        """
        # Get user permissions (from roles or direct permissions)
        user_permissions = await self._get_user_permissions(user)
        
        if self.required_permission not in user_permissions:
            logger.warning(
                "Permission denied",
                user_id=str(user.id),
                required_permission=self.required_permission,
                user_permissions=user_permissions,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.required_permission} required",
            )
        
        return user
    
    async def _get_user_permissions(self, user: User) -> List[str]:
        """Get all permissions for a user."""
        permissions = set()
        
        # Add role-based permissions
        if user.roles:
            for role in user.roles:
                if role.permissions:
                    permissions.update(role.permissions)
        
        # Add direct permissions
        if user.permissions:
            permissions.update(user.permissions)
        
        return list(permissions)


def require_permission(permission: str):
    """
    Create a permission dependency.
    
    Args:
        permission: Required permission (e.g., "admin:read", "projects:write")
        
    Returns:
        Dependency that checks for the permission
        
    Example:
        @router.get("/admin")
        async def admin_dashboard(
            user: User = Depends(require_permission("admin:read"))
        ):
            return {"ok": True}
    """
    return Depends(RoleChecker(permission))


# =============================================================================
# B6: Tenant Isolation Enforcement
# =============================================================================

async def get_tenant_id(request: Request) -> str:
    """
    Extract tenant ID from request headers.
    
    Args:
        request: HTTP request
        
    Returns:
        Tenant ID
        
    Raises:
        HTTPException: If tenant header is missing
    """
    tenant_id = request.headers.get("X-Tenant-ID")
    
    if not tenant_id:
        logger.warning("Tenant header missing", path=request.url.path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header required",
        )
    
    return tenant_id


async def get_tenant_db(
    tenant_id: str = Depends(get_tenant_id),
) -> AsyncSession:
    """
    Get database session with tenant context.
    
    Injects tenant ID into database session for row-level security.
    
    Args:
        tenant_id: Tenant ID from header
        
    Yields:
        Database session with tenant context
    """
    async with db_manager.async_session_factory() as session:
        # Store tenant ID in session info for RLS policies
        session.info["tenant_id"] = tenant_id
        
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class TenantIsolationMiddleware:
    """
    Middleware to enforce tenant isolation.
    
    Validates that all requests include tenant header and
    sets tenant context for the request lifecycle.
    """
    
    async def __call__(self, request: Request, call_next):
        """Process request with tenant validation."""
        # Skip tenant check for health endpoints
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if not tenant_id and not settings.DEBUG:
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-ID header required",
            )
        
        # Set tenant context for logging
        if tenant_id:
            from structlog.contextvars import bind_contextvars
            bind_contextvars(tenant_id=tenant_id)
        
        response = await call_next(request)
        
        # Add tenant ID to response headers for debugging
        if tenant_id:
            response.headers["X-Tenant-ID"] = tenant_id
        
        return response


# =============================================================================
# C8: Stricter Auth Endpoint Limits
# =============================================================================

# Rate limit configurations for auth endpoints
AUTH_RATE_LIMITS = {
    "login": "5/minute",
    "register": "3/hour",
    "refresh": "10/minute",
    "forgot_password": "3/hour",
    "reset_password": "3/hour",
    "verify_email": "10/minute",
    "mfa_verify": "5/minute",
}


def get_auth_rate_limit(endpoint: str) -> str:
    """
    Get rate limit for authentication endpoint.
    
    Args:
        endpoint: Auth endpoint name
        
    Returns:
        Rate limit string (e.g., "5/minute")
    """
    return AUTH_RATE_LIMITS.get(endpoint, "5/minute")


# =============================================================================
# Common Permission Constants
# =============================================================================

class Permissions:
    """Common permission constants."""
    
    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_DELETE = "admin:delete"
    
    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    
    # Document permissions
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    DOCUMENT_DELETE = "document:delete"
    
    # BIM permissions
    BIM_READ = "bim:read"
    BIM_WRITE = "bim:write"
    
    # ML permissions
    ML_READ = "ml:read"
    ML_WRITE = "ml:write"
    
    # Audit permissions
    AUDIT_READ = "audit:read"
    
    # All permissions list
    ALL = [
        ADMIN_READ, ADMIN_WRITE, ADMIN_DELETE,
        USER_READ, USER_WRITE, USER_DELETE,
        PROJECT_READ, PROJECT_WRITE, PROJECT_DELETE,
        DOCUMENT_READ, DOCUMENT_WRITE, DOCUMENT_DELETE,
        BIM_READ, BIM_WRITE,
        ML_READ, ML_WRITE,
        AUDIT_READ,
    ]
