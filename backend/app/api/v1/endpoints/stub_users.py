"""Users API Endpoints (Stub)

RESTful API for user management.
This is a stub implementation - replace with full implementation as needed.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()


# Pydantic Models
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int


# Stub data
STUB_USERS = [
    {"id": "1", "email": "admin@cerebrum.ai", "full_name": "Admin User", "role": "admin", "is_active": True},
    {"id": "2", "email": "user@cerebrum.ai", "full_name": "Regular User", "role": "user", "is_active": True},
]


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
):
    """List all users."""
    return UserListResponse(
        items=[UserResponse(**u) for u in STUB_USERS],
        total=len(STUB_USERS)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_stub():
    """Get current authenticated user."""
    return UserResponse(**STUB_USERS[0])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get a specific user by ID."""
    for user in STUB_USERS:
        if user["id"] == user_id:
            return UserResponse(**user)
    raise HTTPException(status_code=404, detail="User not found")


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, data: UserUpdateRequest):
    """Update a user."""
    for user in STUB_USERS:
        if user["id"] == user_id:
            if data.full_name:
                user["full_name"] = data.full_name
            if data.email:
                user["email"] = data.email
            return UserResponse(**user)
    raise HTTPException(status_code=404, detail="User not found")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """Delete a user."""
    for user in STUB_USERS:
        if user["id"] == user_id:
            return
    raise HTTPException(status_code=404, detail="User not found")
