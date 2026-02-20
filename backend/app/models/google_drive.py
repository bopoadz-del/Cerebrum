"""
Google Drive OAuth Token Model
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base


class GoogleDriveToken(Base):
    __tablename__ = "google_drive_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(DateTime, nullable=False)
    google_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    def is_expired(self):
        from datetime import timedelta
        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=5))
