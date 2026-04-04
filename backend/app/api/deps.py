"""
API Dependencies

Provides authentication and database dependencies for API endpoints.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import uuid
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

# Export User model for compatibility
from app.models.user import User

# Export get_db from session
from app.db.session import get_db_session as get_db

# JWT imports
import jwt
from app.core.security.jwt import jwt_manager, TokenExpiredError, InvalidTokenError
from app.core.logging import get_logger

logger = get_logger(__name__)

# SLEEP MODE: Set to True to disable authentication (for development only)
# SECURITY: Default is 'false' - authentication is REQUIRED unless explicitly disabled
AUTH_SLEEP_MODE_RAW = os.environ.get('AUTH_SLEEP_MODE', 'false').lower() in ('true', '1', 'yes')

# CRITICAL: Force disable sleep mode in production regardless of env var
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development').lower()
if ENVIRONMENT in ('production', 'prod', 'staging'):
    if AUTH_SLEEP_MODE_RAW:
        logger.warning(f"AUTH_SLEEP_MODE was enabled but FORCE-DISABLED in {ENVIRONMENT} environment!")
    AUTH_SLEEP_MODE = False
else:
    AUTH_SLEEP_MODE = AUTH_SLEEP_MODE_RAW
# Hardcoded sleep mode user ID (consistent fake user)
SLEEP_MODE_USER_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticate user from JWT token and return User object from database.
    
    SLEEP MODE: When AUTH_SLEEP_MODE is True, returns a fake user without checking token.
    
    Args:
        token: JWT access token from Authorization header
        db: Database session
        
    Returns:
        User object from database
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    # SLEEP MODE: Bypass authentication
    if AUTH_SLEEP_MODE:
        # Return a fake user that exists in the database or create one
        result = await db.execute(select(User).where(User.id == SLEEP_MODE_USER_ID))
        user = result.scalar_one_or_none()
        if not user:
            # Create sleep mode user if not exists
            user = User(
                id=SLEEP_MODE_USER_ID,
                email="sleep@mode.local",
                hashed_password="sleep_mode",
                full_name="Sleep Mode User",
                role="admin",
                tenant_id=SLEEP_MODE_USER_ID,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("Created sleep mode user")
        return user
    
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
    except jwt.exceptions.DecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
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
    stmt = select(User).filter(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
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


# =============================================================================
# Rate Limiting - User ID based key function
# =============================================================================

def get_user_id_for_rate_limit(request) -> str:
    """
    Get rate limit key based on user ID (for authenticated users) or IP address.
    
    This function is used by SlowAPI's Limiter to determine the rate limit key.
    - For authenticated users: uses "user:{user_id}" to prevent shared IP exhaustion
    - For anonymous users: falls back to "ip:{remote_address}" 
    
    This solves the problem where multiple users behind NAT/mobile networks share
    the same IP and exhaust the rate limit quota.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Rate limit key string (user:uuid or ip:address)
    """
    from fastapi import Request
    
    if not isinstance(request, Request):
        # Fallback for non-request contexts
        return "ip:unknown"
    
    # Try to extract JWT token from Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        try:
            # Decode token without DB lookup - just extract user ID
            payload = jwt_manager.decode_token(token, token_type="access")
            user_id = payload.sub
            return f"user:{user_id}"
        except (TokenExpiredError, InvalidTokenError, ValueError, jwt.exceptions.DecodeError):
            # Token is invalid/expired - treat as anonymous
            pass
    
    # Fall back to IP address for unauthenticated requests
    client_host = request.client.host if request.client else None
    if client_host:
        return f"ip:{client_host}"
    
    # Last resort - use X-Forwarded-For header if available
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"
    
    return "ip:unknown"
