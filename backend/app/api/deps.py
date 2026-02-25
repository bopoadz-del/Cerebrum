from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import db_manager
from app.models.user import User  # Export User for type hints

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_db_session() -> Generator:
    """Get database session from manager"""
    try:
        session_factory = db_manager.sync_session_factory
        db = session_factory()
        yield db
    finally:
        db.close()

# Alias for compatibility with different import styles
get_db = get_db_session

async def get_current_user_id(
    token: str = Depends(oauth2_scheme)
) -> int:
    """Get current user ID from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return int(user_id)
    except JWTError:
        raise credentials_exception

async def get_current_user(
    db: Session = Depends(get_db_session),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current user from token and database"""
    # Handle mock token for development
    if token == "mock-token":
        from uuid import UUID
        mock_user_id = UUID("e727e727-d547-4d96-b070-2294980e5d85")
        user = db.query(User).filter(User.id == mock_user_id).first()
        if user:
            return user
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Handle UUID user IDs
    try:
        from uuid import UUID
        user_uuid = UUID(user_id)
        user = db.query(User).filter(User.id == user_uuid).first()
    except ValueError:
        user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verify user is admin"""
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Re-export User for convenience
__all__ = [
    'get_db', 'get_db_session', 'get_current_user', 
    'get_current_user_id', 'get_current_admin_user', 'User'
]

# --- Async DB dependency (added to fix async endpoints using await db.execute) ---
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

_async_engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(bind=_async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
# --- end async DB dependency ---
