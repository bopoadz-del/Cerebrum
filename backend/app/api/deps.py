from typing import Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import uuid

# Fake User class that doesn't need DB
class FakeUser:
    def __init__(self):
        self.id = uuid.UUID('e727e727-d547-4d96-b070-2294980e5d85')
        self.email = "admin@test.com"
        self.is_active = True
        self.is_superuser = True

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> FakeUser:
    """DEV MODE: No DB query, always returns fake user."""
    return FakeUser()

async def get_current_active_user(current_user: FakeUser = Depends(get_current_user)) -> FakeUser:
    """DEV MODE: Always active."""
    return current_user

async def get_current_superuser(current_user: FakeUser = Depends(get_current_user)) -> FakeUser:
    """DEV MODE: Always superuser."""
    return current_user

# Alias for compatibility
get_current_admin_user = get_current_superuser

# DB dependency still needed for other endpoints
from app.db.session import get_db_session as get_db
