"""
Conversation Session Service

Provides business logic for long-session mode with capacity tracking.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from app.models.conversation_session import ConversationSession

logger = logging.getLogger(__name__)

# Session configuration
DEFAULT_SESSION_TTL_HOURS = 24
MAX_SESSION_TTL_HOURS = 168  # 7 days
MAX_CAPACITY_PERCENT = 100
# TODO: Replace with actual token count from LLM when available
# Baseline: ~10 messages = 10% capacity (rough estimate)
MESSAGES_PER_CAPACITY_UNIT = 10


def generate_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(48)


def calculate_capacity_percent(message_count: int, token_count: int = 0) -> int:
    """
    Calculate session capacity percentage.
    
    Uses message count as baseline until real token count is available.
    
    Args:
        message_count: Number of messages in session
        token_count: Actual token count (when available from LLM)
        
    Returns:
        Capacity percentage (0-100)
    """
    # TODO: Replace with real token count when LLM integration is ready
    # For now, use message count as a proxy
    if token_count > 0:
        # Real token-based calculation
        # Assuming ~4000 token context window
        percent = min(100, int((token_count / 4000) * 100))
    else:
        # Message-based proxy
        percent = min(100, int((message_count / MESSAGES_PER_CAPACITY_UNIT) * 10))
    
    return min(MAX_CAPACITY_PERCENT, max(0, percent))


class SessionService:
    """Service for managing conversation sessions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
    ) -> ConversationSession:
        """
        Create a new conversation session.
        
        Args:
            user_id: User ID for session ownership
            title: Optional session title
            ttl_hours: Session TTL in hours (max 168)
            
        Returns:
            Created ConversationSession
        """
        # Clamp TTL to max
        ttl_hours = min(ttl_hours, MAX_SESSION_TTL_HOURS)
        
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=ttl_hours)
        
        session = ConversationSession(
            user_id=user_id,
            session_token=generate_session_token(),
            title=title,
            capacity_percent=0,
            message_count=0,
            token_count=0,
            is_active=True,
            last_activity_at=now,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        logger.info(
            f"Created conversation session: {session.session_token[:8]}... "
            f"for user {user_id}, expires_at={expires_at.isoformat()}"
        )
        
        return session
    
    async def get_session_by_token(
        self,
        session_token: str,
        check_active: bool = True,
    ) -> Optional[ConversationSession]:
        """
        Get session by token.
        
        Args:
            session_token: Session token to look up
            check_active: If True, only return active non-expired sessions
            
        Returns:
            ConversationSession or None
        """
        query = select(ConversationSession).where(
            ConversationSession.session_token == session_token
        )
        
        if check_active:
            query = query.where(
                and_(
                    ConversationSession.is_active == True,
                    ConversationSession.expires_at > datetime.utcnow(),
                )
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> List[ConversationSession]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID to look up
            active_only: If True, only return active non-expired sessions
            
        Returns:
            List of ConversationSession objects
        """
        query = select(ConversationSession).where(
            ConversationSession.user_id == user_id
        )
        
        if active_only:
            query = query.where(
                and_(
                    ConversationSession.is_active == True,
                    ConversationSession.expires_at > datetime.utcnow(),
                )
            )
        
        query = query.order_by(ConversationSession.last_activity_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_capacity(
        self,
        session_token: str,
        capacity_percent: int,
    ) -> Optional[ConversationSession]:
        """
        Update session capacity percentage.
        
        Args:
            session_token: Session token to update
            capacity_percent: New capacity percentage (0-100)
            
        Returns:
            Updated ConversationSession or None if not found
        """
        # Clamp capacity to valid range
        capacity_percent = min(MAX_CAPACITY_PERCENT, max(0, capacity_percent))
        
        query = (
            update(ConversationSession)
            .where(ConversationSession.session_token == session_token)
            .values(
                capacity_percent=capacity_percent,
                updated_at=datetime.utcnow(),
            )
            .returning(ConversationSession)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        session = result.scalar_one_or_none()
        if session:
            logger.info(
                f"Updated session capacity: {session_token[:8]}... = {capacity_percent}%"
            )
        
        return session
    
    async def increment_message_count(
        self,
        session_token: str,
        tokens_used: int = 0,
    ) -> Optional[ConversationSession]:
        """
        Increment message count and update capacity.
        
        Call this when a new message is added to the session.
        
        Args:
            session_token: Session token to update
            tokens_used: Number of tokens used (if available from LLM)
            
        Returns:
            Updated ConversationSession or None
        """
        # Get current session
        session = await self.get_session_by_token(session_token, check_active=False)
        if not session:
            return None
        
        # Update counts
        session.message_count += 1
        session.token_count += tokens_used
        session.last_activity_at = datetime.utcnow()
        
        # Recalculate capacity
        session.capacity_percent = calculate_capacity_percent(
            session.message_count,
            session.token_count,
        )
        
        await self.db.commit()
        await self.db.refresh(session)
        
        return session
    
    async def deactivate_session(
        self,
        session_token: str,
    ) -> bool:
        """
        Deactivate a session.
        
        Args:
            session_token: Session token to deactivate
            
        Returns:
            True if deactivated, False if not found
        """
        query = (
            update(ConversationSession)
            .where(ConversationSession.session_token == session_token)
            .values(
                is_active=False,
                updated_at=datetime.utcnow(),
            )
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        success = result.rowcount > 0
        if success:
            logger.info(f"Deactivated session: {session_token[:8]}...")
        
        return success
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Deactivate all expired sessions.
        
        Returns:
            Number of sessions deactivated
        """
        query = (
            update(ConversationSession)
            .where(
                and_(
                    ConversationSession.is_active == True,
                    ConversationSession.expires_at <= datetime.utcnow(),
                )
            )
            .values(
                is_active=False,
                updated_at=datetime.utcnow(),
            )
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        
        return count
