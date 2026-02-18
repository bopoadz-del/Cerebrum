"""
Document Model

Stores indexed documents from Google Drive for ZVec semantic search.
"""

import uuid
from typing import Optional

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import BaseModel


class Document(BaseModel):
    """Document model for storing indexed Drive files."""
    
    __tablename__ = "documents"
    
    # Google Drive file ID
    drive_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # File metadata
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Indexing status: pending, indexed, error, archived
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    
    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )


class DocumentChunk(BaseModel):
    """Document chunks for large file segmentation."""
    
    __tablename__ = "document_chunks"
    
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False
    )
    
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
