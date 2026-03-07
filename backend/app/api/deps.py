"""
API Dependencies

Provides authentication and database dependencies for API endpoints.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import uuid

from sqlalchemy.orm import Session

# Export User model for compatibility
from app.models.user import User

# Export get_db from session
from app.db.session import get_db_session as get_db

# JWT imports
from app.core.security.jwt import jwt_manager, TokenExpiredError, InvalidTokenError
from app.core.logging import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticate user from JWT token and return User object from database.
    
    Args:
        token: JWT access token from Authorization header
        db: Database session
        
    Returns:
        User object from database
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode and validate JWT token
        payload = jwt_manager.decode_token(token, token_type="access")
        user_id = uuid.UUID(payload.sub)
        
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is a superuser (checks if role is 'admin' or 'superuser')."""
    if current_user.role not in ('admin', 'superuser'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# Alias for compatibility
get_current_admin_user = get_current_superuser


async def get_current_user_id(
    current_user: User = Depends(get_current_user)
) -> uuid.UUID:
    """Get current user ID from authenticated user."""
    return current_user.id


# get_db_session is already exported as get_db, but some files import it directly
get_db_session = get_db


# get_async_db is needed by some endpoints
get_async_db = get_db


async def get_current_user_async(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Async version - same as get_current_user."""
    return await get_current_user(token, db)
