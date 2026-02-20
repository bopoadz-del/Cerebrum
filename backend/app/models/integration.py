"""
Integration Token Model

Stores OAuth tokens for third-party integrations.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class IntegrationToken(BaseModel):
    """
    OAuth token storage for integrations.
    
    Stores access tokens, refresh tokens, and metadata for
    third-party service integrations like Google Drive.
    """
    
    __tablename__ = "integration_tokens"
    
    # Token identification
    token_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Service identifier (e.g., 'google_drive', 'procore', 'slack')
    service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # OAuth tokens
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_uri: Mapped[str] = mapped_column(String(255), nullable=False, default="https://oauth2.googleapis.com/token")
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="")  # Space-separated scopes
    
    # Token expiry and rotation
    expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rotation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<IntegrationToken {self.service} user={self.user_id}>"


class IntegrationProvider:
    """Integration provider constants."""
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    DROPBOX = "dropbox"
    SLACK = "slack"
    PROCORE = "procore"
