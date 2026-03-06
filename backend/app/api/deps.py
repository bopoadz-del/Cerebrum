from typing import Optional, Generator, AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import uuid

from app.db.session import get_db_session as get_db
from app.db.session import get_db_session
from app.models.user import User

# OAuth2 scheme (kept for compatibility but not enforced)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    """DEV MODE: Auth bypassed. Returns Drive-connected user."""
    target_id = uuid.UUID('e727e727-d547-4d96-b070-2294980e5d85')
    user = db.query(User).filter(User.id == target_id).first()
    if not user:
        user = User(id=target_id, email="admin@test.com", hashed_password="fake", is_active=True, is_superuser=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """DEV MODE: Always active."""
    return current_user

def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """DEV MODE: Always superuser."""
    return current_user

# Keep get_db export
__all__ = ["get_db", "get_db_session", "get_async_db", "get_current_user", "get_current_user_async", "get_current_user_id", "get_current_active_user", "get_current_superuser"]


async def get_current_user_id(
    current_user: User = Depends(get_current_user),
) -> str:
    """Get current user ID as string."""
    return str(current_user.id)


# Async versions for compatibility
get_async_db = get_db_session


async def get_current_user_async(
    db: AsyncSession = Depends(get_db_session),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    """DEV MODE: Auth bypassed. Returns Drive-connected user (async version)."""
    from sqlalchemy import select
    target_id = uuid.UUID('e727e727-d547-4d96-b070-2294980e5d85')
    result = await db.execute(select(User).where(User.id == target_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=target_id, email="admin@test.com", hashed_password="fake", is_active=True, is_superuser=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """DEV MODE: All users are admins."""
    return current_user
