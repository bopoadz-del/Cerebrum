from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, JSON, String, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base


class GoogleDriveProject(Base):
    """
    Maps a Google Drive folder root to a core Project.
    Stores detection results and indexing status for UI.
    """
    __tablename__ = "google_drive_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    root_folder_id = Column(String(128), nullable=False)
    root_folder_name = Column(String(512), nullable=False)

    score = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.0)
    reasons = Column(JSON, nullable=False, default=list)        # [{signal, weight, detail}]
    entry_points = Column(JSON, nullable=False, default=list)   # ["README.md", ...]
    tags = Column(JSON, nullable=False, default=list)

    indexing_status = Column(String(32), nullable=False, default="idle")  # idle|queued|running|done|error
    indexing_progress = Column(JSON, nullable=False, default=dict)        # {"indexed":0,"total":0}
    last_indexed_at = Column(DateTime, nullable=True)

    last_scanned_at = Column(DateTime, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


Index("ix_gdp_user_root", GoogleDriveProject.user_id, GoogleDriveProject.root_folder_id, unique=True)
