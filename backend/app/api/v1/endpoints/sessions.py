"""
Conversation Sessions API Endpoints

Long-session mode with capacity tracking endpoints.
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, get_current_user_id
from app.services.session_service import SessionService
from app.models.conversation_session import ConversationSession

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class SessionCreateRequest(BaseModel):
    """Request to create a new session."""
    title: Optional[str] = Field(None, max_length=255, description="Optional session title")
    ttl_hours: int = Field(24, ge=1, le=168, description="Session TTL in hours (1-168)")


class SessionCapacityUpdateRequest(BaseModel):
    """Request to update session capacity."""
    capacity_percent: int = Field(..., ge=0, le=100, description="Capacity percentage (0-100)")


class SessionResponse(BaseModel):
    """Session response schema."""
    id: str
    session_token: str
    title: Optional[str]
    capacity_percent: int
    message_count: int
    token_count: int
    is_active: bool
    is_expired: bool
    last_activity_at: Optional[str]
    expires_at: Optional[str]
    created_at: Optional[str]
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    sessions: List[SessionResponse]
    total: int


class SessionCreateResponse(BaseModel):
    """Response after creating a session."""
    session_token: str
    session: SessionResponse


class CapacityResponse(BaseModel):
    """Capacity update response."""
    session_token: str
    capacity_percent: int
    message_count: int


# =============================================================================
# API Endpoints
# =============================================================================

@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new session",
    description="Create a new conversation session with optional title and TTL.",
)
async def create_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> SessionCreateResponse:
    """
    Create a new conversation session.
    
    Returns session token for use in subsequent requests.
    """
    service = SessionService(db)
    
    session = await service.create_session(
        user_id=user_id,
        title=request.title,
        ttl_hours=request.ttl_hours,
    )
    
    return SessionCreateResponse(
        session_token=session.session_token,
        session=SessionResponse(**session.to_dict()),
    )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List user sessions",
    description="Get all active sessions for the current user.",
)
async def list_sessions(
    active_only: bool = Query(True, description="Only return active sessions"),
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> SessionListResponse:
    """
    List all conversation sessions for the current user.
    """
    service = SessionService(db)
    sessions = await service.get_user_sessions(user_id, active_only=active_only)
    
    return SessionListResponse(
        sessions=[SessionResponse(**s.to_dict()) for s in sessions],
        total=len(sessions),
    )


@router.get(
    "/{session_token}",
    response_model=SessionResponse,
    summary="Get session by token",
    description="Get session details by session token.",
)
async def get_session(
    session_token: str,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> SessionResponse:
    """
    Get a specific session by its token.
    """
    service = SessionService(db)
    session = await service.get_session_by_token(session_token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )
    
    # Verify ownership
    if str(session.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return SessionResponse(**session.to_dict())


@router.patch(
    "/{session_token}/capacity",
    response_model=CapacityResponse,
    summary="Update session capacity",
    description="Update the capacity percentage for a session.",
)
async def update_capacity(
    session_token: str,
    request: SessionCapacityUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> CapacityResponse:
    """
    Update session capacity percentage.
    
    This is typically called by the backend when capacity changes,
    but can be called manually for testing/admin purposes.
    """
    service = SessionService(db)
    
    # Verify session exists and belongs to user
    session = await service.get_session_by_token(session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )
    
    if str(session.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    updated = await service.update_capacity(
        session_token,
        request.capacity_percent,
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update capacity",
        )
    
    return CapacityResponse(
        session_token=session_token,
        capacity_percent=updated.capacity_percent,
        message_count=updated.message_count,
    )


@router.get(
    "/{session_token}/capacity",
    response_model=CapacityResponse,
    summary="Get session capacity",
    description="Get current capacity and message count for a session.",
)
async def get_capacity(
    session_token: str,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> CapacityResponse:
    """
    Get current session capacity.
    """
    service = SessionService(db)
    session = await service.get_session_by_token(session_token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )
    
    if str(session.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return CapacityResponse(
        session_token=session_token,
        capacity_percent=session.capacity_percent,
        message_count=session.message_count,
    )


@router.post(
    "/{session_token}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate session",
    description="Deactivate (close) a conversation session.",
)
async def deactivate_session(
    session_token: str,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> None:
    """
    Deactivate a conversation session.
    """
    service = SessionService(db)
    
    # Verify ownership
    session = await service.get_session_by_token(session_token, check_active=False)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    if str(session.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    success = await service.deactivate_session(session_token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate session",
        )


@router.post(
    "/{session_token}/touch",
    response_model=SessionResponse,
    summary="Touch session",
    description="Update last activity timestamp for a session.",
)
async def touch_session(
    session_token: str,
    db: AsyncSession = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id),
) -> SessionResponse:
    """
    Update session last activity timestamp.
    """
    service = SessionService(db)
    session = await service.get_session_by_token(session_token)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired",
        )
    
    if str(session.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    session.touch()
    await db.commit()
    await db.refresh(session)
    
    return SessionResponse(**session.to_dict())
