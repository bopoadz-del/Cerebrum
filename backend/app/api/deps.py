from typing import Generator, Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import db_manager
from app.models.user import User  # Export User for type hints

# --- Async DB dependency (lazy initialization) ---
_async_engine = None
AsyncSessionLocal = None

def _get_async_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(settings.async_database_url, pool_pre_ping=True, pool_size=5, max_overflow=0)
    return _async_engine

def _get_async_session_local():
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = sessionmaker(bind=_get_async_engine(), class_=AsyncSession, expire_on_commit=False)
    return AsyncSessionLocal

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    session_local = _get_async_session_local()
    async with session_local() as session:
        try:
            yield session
        finally:
            await session.close()
# --- end async DB dependency ---

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

async def get_current_user_async(
    db: AsyncSession = Depends(get_async_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Get current user from token and database (async version)"""
    from sqlalchemy import select
    
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
    from uuid import UUID
    try:
        user_uuid = UUID(user_id)
        result = await db.execute(select(User).where(User.id == user_uuid))
    except ValueError:
        result = await db.execute(select(User).where(User.id == user_id))
    
    user = result.scalar_one_or_none()
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
    'get_current_user_id', 'get_current_admin_user', 'User',
    'get_async_db', 'get_current_user_async'
]
