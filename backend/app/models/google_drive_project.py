"""
Google Drive Project Models

Stub models for Google Drive integration.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean
from app.db.base_class import Base


class GoogleDriveProject(Base):
    """Google Drive project integration model."""
    __tablename__ = "google_drive_projects"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), nullable=False, index=True)
    drive_folder_id = Column(String(255), nullable=False)
    folder_name = Column(String(500), nullable=True)
    folder_path = Column(Text, nullable=True)
    is_synced = Column(Boolean, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
