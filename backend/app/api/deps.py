from typing import Optional, Generator
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import uuid

from app.db.session import get_db
from app.models.user import User

# OAuth2 scheme (kept for compatibility but not enforced)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    """
    DEV MODE: Auth bypassed.
    Always returns the user with Google Drive connected.
    Any email/password works.
    """
    target_id = uuid.UUID('e727e727-d547-4d96-b070-2294980e5d85')
    
    # Get or create the Drive-connected user
    user = db.query(User).filter(User.id == target_id).first()
    
    if not user:
        # Create fake user if doesn't exist
        user = User(
            id=target_id,
            email="admin@cerebrum.ai",
            hashed_password="$2b$12$fakehash",  # bcrypt fake
            full_name="Admin User",
            is_active=True,
            is_superuser=True
        )
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
__all__ = ["get_db", "get_current_user", "get_current_active_user", "get_current_superuser"]
