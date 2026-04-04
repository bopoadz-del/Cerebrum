"""
Conversation Session Model

Long-session mode with capacity tracking for smart context.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base


class ConversationSession(Base):
    """
    Database-backed conversation session for long-session mode.
    
    Tracks session capacity, message count, and expiration.
    """
    
    __tablename__ = "conversation_sessions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User association
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Session token for API access (64 char random string)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    
    # Optional session title
    title = Column(String(255), nullable=True)
    
    # Capacity tracking (0-100 percent)
    capacity_percent = Column(Integer, nullable=False, default=0)
    
    # Message count for capacity calculation
    message_count = Column(Integer, nullable=False, default=0)
    
    # Token count (when available from LLM)
    token_count = Column(Integer, nullable=False, default=0)
    
    # Session state
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ConversationSession(id={self.id}, user_id={self.user_id}, capacity={self.capacity_percent}%)>"
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at
    
    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_token": self.session_token,
            "title": self.title,
            "capacity_percent": self.capacity_percent,
            "message_count": self.message_count,
            "token_count": self.token_count,
            "is_active": self.is_active,
            "is_expired": self.is_expired(),
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
