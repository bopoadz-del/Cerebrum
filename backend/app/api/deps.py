from typing import Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import uuid

# Export User model for compatibility
from app.models.user import User

# Export get_db from session
from app.db.session import get_db_session as get_db

# Fake User class for auth bypass
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

# Additional exports needed by endpoints
async def get_current_user_id(current_user: FakeUser = Depends(get_current_user)) -> uuid.UUID:
    """DEV MODE: Returns fake user ID."""
    return current_user.id

# get_db_session is already exported as get_db, but some files import it directly
get_db_session = get_db

# get_async_db is needed by some endpoints
get_async_db = get_db

# get_current_user_async for async compatibility
async def get_current_user_async(token: Optional[str] = Depends(oauth2_scheme)) -> FakeUser:
    """DEV MODE: Async version, returns fake user."""
    return FakeUser()
