from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, JSON, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base


class ProjectType(str, enum.Enum):
    SOFTWARE_REPO = "software_repo"
    CLIENT_CONSULTING = "client_consulting"
    JOB_APPLICATION = "job_application"
    LEGAL_FINANCE = "legal_finance"
    RESEARCH_NOTES = "research_notes"
    DESIGN_MEDIA = "design_media"
    GENERAL_PROJECT = "general_project"
    UNKNOWN = "unknown"


class Project(Base):
    """
    Core Project entity.

    Required because other models already ForeignKey("projects.id")
    (see app/models/economics.py). Keep it minimal and extensible.
    """
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(512), nullable=False)

    # SQLAlchemy Enum stored as text (Postgres enum handling depends on your setup;
    # this is the safest default for mixed environments).
    type = Column(Enum(ProjectType, name="project_type"), nullable=False, default=ProjectType.UNKNOWN)

    tags = Column(JSON, nullable=False, default=list)
    meta = Column("metadata", JSON, nullable=False, default=dict)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
