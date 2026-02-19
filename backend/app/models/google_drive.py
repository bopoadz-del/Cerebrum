"""
Google Drive OAuth Token Model
Stores OAuth tokens and metadata for Google Drive integrations
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class GoogleDriveToken(Base):
    """OAuth tokens for Google Drive API access"""
    __tablename__ = "google_drive_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)  # Critical for long-term access
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(DateTime, nullable=False)  # When access_token expires
    
    # Google user info
    google_user_id = Column(String(255), nullable=True)
    google_email = Column(String(255), nullable=True)
    
    # Scopes granted
    scopes = Column(Text, nullable=True)  # Space-separated scopes
    
    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationship
    # user relationship removed temporarily

    def is_expired(self) -> bool:
        """Check if access token is expired (with 5 min buffer)"""
        from datetime import timedelta
        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=5))

    def __repr__(self):
        return f"<GoogleDriveToken user_id={self.user_id} email={self.google_email} active={self.is_active}>"
