"""
Dependency injection utilities for FastAPI endpoints.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database.session import get_db_session
from app.core.config import get_settings

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Returns a user dict with at minimum an 'id' field.
    For stub implementation, returns a default user.
    """
    settings = get_settings()
    
    # If no credentials provided, return default user for development
    if not credentials:
        return {
            "id": "default-user-id",
            "email": "admin@cerebrum.local",
            "name": "Admin User",
            "role": "admin",
            "permissions": ["*"]
        }
    
    # TODO: Implement actual JWT validation
    # For now, return the token as user id for stub
    return {
        "id": credentials.credentials[:20] if credentials.credentials else "token-user",
        "email": "user@cerebrum.local",
        "name": "API User",
        "role": "user",
        "permissions": ["read"]
    }


def require_permissions(required_permissions: list):
    """
    Dependency factory to require specific permissions.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: dict = Depends(require_permissions(["admin"]))
        ):
            return {"message": "Admin access granted"}
    """
    def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        user_permissions = current_user.get("permissions", [])
        
        # Check if user has wildcard permission or all required permissions
        has_wildcard = "*" in user_permissions
        has_all_required = all(
            perm in user_permissions or perm == "read" and "*" in user_permissions
            for perm in required_permissions
        )
        
        if not (has_wildcard or has_all_required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permissions}"
            )
        
        return current_user
    
    return permission_checker
