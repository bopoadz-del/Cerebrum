"""
Admin Endpoints

Provides administrative endpoints for user management,
system configuration, and monitoring.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security.password import password_manager
from app.core.security.rbac import require_role, Role, rbac
from app.core.security.session import session_manager
from app.db.session import get_db_session
from app.models.user import User, Role as RoleModel
from app.models.audit import audit_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin")


# =============================================================================
# Schemas
# =============================================================================

class UserCreateRequest(BaseModel):
    """Create user request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: str = Field(default="user")
    tenant_id: Optional[str] = None
    is_active: bool = True
    is_verified: bool = True


class UserUpdateRequest(BaseModel):
    """Update user request."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserResponse(BaseModel):
    """User response."""
    id: str
    email: str
    full_name: Optional[str]
    role: str
    tenant_id: str
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    last_login_at: Optional[str]
    created_at: str
    updated_at: str


class UserListResponse(BaseModel):
    """User list response."""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


class RoleCreateRequest(BaseModel):
    """Create role request."""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class RoleResponse(BaseModel):
    """Role response."""
    id: str
    name: str
    description: Optional[str]
    permissions: List[str]
    is_system: bool
    created_at: str


class SystemStatsResponse(BaseModel):
    """System statistics response."""
    total_users: int
    active_users: int
    verified_users: int
    mfa_enabled_users: int
    total_roles: int


# =============================================================================
# User Management Endpoints
# =============================================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(Role.ADMIN, Role.SUPERADMIN)),
) -> UserListResponse:
    """
    List all users with pagination and filtering.
    
    Args:
        request: HTTP request
        page: Page number
        page_size: Items per page
        role: Filter by role
        is_active: Filter by active status
        search: Search term for email or name
        db: Database session
        current_user: Current admin user
        
    Returns:
        Paginated user list
    """
    # Build query
    query = select(User).where(User.deleted_at.is_(None))
    
    # Apply filters
    if role:
        query = query.where(User.role == role)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(User.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Log admin action
    await audit_logger.log(
        db_session=db,
        action="users_list",
        resource_type="users",
        user_id=current_user.id,
        details={"page": page, "page_size": page_size, "filters": {"role": role, "is_active": is_active}},
        ip_address=request.client.host if request.client else None,
    )
    
    return UserListResponse(
        items=[UserResponse(**user.to_dict()) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    data: UserCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(Role.ADMIN, Role.SUPERADMIN)),
) -> UserResponse:
    """
    Create a new user.
    
    Args:
        request: HTTP request
        data: User creation data
        db: Database session
        current_user: Current admin user
        
    Returns:
        Created user
    """
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Validate password
    is_valid, errors = password_manager.validate(data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid password: {', '.join(errors)}",
        )
    
    # Create user
    user = User(
        id=uuid.uuid4(),
        email=data.email,
        hashed_password=password_manager.hash(data.password),
        full_name=data.full_name,
        role=data.role,
        tenant_id=uuid.UUID(data.tenant_id) if data.tenant_id else current_user.tenant_id,
        is_active=data.is_active,
        is_verified=data.is_verified,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Log action
    await audit_logger.log(
        db_session=db,
        action="user_create",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        details={"email": user.email, "role": user.role},
        ip_address=request.client.host if request.client else None,
    )
    
    logger.info(
        f"User created by admin",
        user_id=str(user.id),
        admin_id=str(current_user.id),
    )
    
    return UserResponse(**user.to_dict())


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(Role.ADMIN, Role.SUPERADMIN)),
) -> UserResponse:
    """
    Get user by ID.
    
    Args:
        request: HTTP request
        user_id: User ID
        db: Database session
        current_user: Current admin user
        
    Returns:
        User details
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(**user.to_dict())


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    request: Request,
    user_id: str,
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(Role.ADMIN, Role.SUPERADMIN)),
) -> UserResponse:
    """
    Update user.
    
    Args:
        request: HTTP request
        user_id: User ID
        data: Update data
        db: Database session
        current_user: Current admin user
        
    Returns:
        Updated user
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent modifying superadmin (except by superadmin)
    if user.role == Role.SUPERADMIN.value and current_user.role != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify superadmin user",
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    
    # Log action
    await audit_logger.log(
        db_session=db,
        action="user_update",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        details=update_data,
        ip_address=request.client.host if request.client else None,
    )
    
    return UserResponse(**user.to_dict())


@router.delete("/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(Role.ADMIN, Role.SUPERADMIN)),
) -> dict:
    """
    Soft delete user.
    
    Args:
        request: HTTP request
        user_id: User ID
        db: Database session
        current_user: Current admin user
        
    Returns:
        Success message
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent deleting self
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    # Prevent deleting superadmin
    if user.role == Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete superadmin user",
        )
    
    # Soft delete
    user.soft_delete()
    user.is_active = False
    
    # Invalidate sessions
    await session_manager.invalidate_user_sessions(user_id)
    
    await db.commit()
    
    # Log action
    await audit_logger.log(
        db_session=db,
        action="user_delete",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/unlock")
async def unlock_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(Role.ADMIN, Role.SUPERADMIN)),
) -> dict:
    """
    Unlock a locked user account.
    
    Args:
        request: HTTP request
        user_id: User ID
        db: Database session
        current_user: Current admin user
        
    Returns:
        Success message
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Log action
    await audit_logger.log(
        db_session=db,
        action="user_unlock",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    
    return {"message": "User unlocked successfully"}


# =============================================================================
# System Endpoints
# =============================================================================

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(Role.ADMIN, Role.SUPERADMIN)),
) -> SystemStatsResponse:
    """
    Get system statistics.
    
    Args:
        request: HTTP request
        db: Database session
        current_user: Current admin user
        
    Returns:
        System statistics
    """
    # Total users
    total_result = await db.execute(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )
    total_users = total_result.scalar()
    
    # Active users
    active_result = await db.execute(
        select(func.count()).select_from(User).where(
            User.deleted_at.is_(None),
            User.is_active == True
        )
    )
    active_users = active_result.scalar()
    
    # Verified users
    verified_result = await db.execute(
        select(func.count()).select_from(User).where(
            User.deleted_at.is_(None),
            User.is_verified == True
        )
    )
    verified_users = verified_result.scalar()
    
    # MFA enabled users
    mfa_result = await db.execute(
        select(func.count()).select_from(User).where(
            User.deleted_at.is_(None),
            User.mfa_enabled == True
        )
    )
    mfa_enabled_users = mfa_result.scalar()
    
    # Total roles
    roles_result = await db.execute(
        select(func.count()).select_from(RoleModel)
    )
    total_roles = roles_result.scalar()
    
    return SystemStatsResponse(
        total_users=total_users,
        active_users=active_users,
        verified_users=verified_users,
        mfa_enabled_users=mfa_enabled_users,
        total_roles=total_roles,
    )
