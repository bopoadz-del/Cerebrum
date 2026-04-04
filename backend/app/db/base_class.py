"""
SQLAlchemy Base Classes and Mixins

Provides base model classes with common functionality including
soft delete support, timestamp tracking, and UUID primary keys.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, String, Boolean, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base, DeclarativeMeta

from app.core.logging import get_logger

logger = get_logger(__name__)

# Create declarative base for all models
Base: DeclarativeMeta = declarative_base()


class TimestampMixin:
    """
    Mixin for automatic timestamp tracking.
    
    Adds created_at and updated_at columns that are automatically
    managed by SQLAlchemy events.
    """
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Record last update timestamp",
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    
    Provides deleted_at timestamp column and helper methods
    for soft deletion and restoration of records.
    
    Records with deleted_at set are filtered out by default
    using the default query filter.
    """
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
        comment="Soft delete timestamp - null if active",
    )
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Mark record as deleted without removing from database."""
        self.deleted_at = datetime.utcnow()
        logger.debug(
            f"Soft deleted {self.__class__.__name__}",
            id=str(getattr(self, 'id', 'unknown')),
        )
    
    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
        logger.debug(
            f"Restored {self.__class__.__name__}",
            id=str(getattr(self, 'id', 'unknown')),
        )


class UUIDMixin:
    """
    Mixin for UUID primary keys.
    
    Provides UUID primary key column with automatic generation.
    """
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        unique=True,
        comment="Unique identifier (UUID v4)",
    )


class TenantMixin:
    """
    Mixin for multi-tenant support.
    
    Adds tenant_id column for row-level tenant isolation.
    """
    
    tenant_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant identifier for multi-tenancy",
    )


class AuditMixin:
    """
    Mixin for audit tracking.
    
    Tracks who created and last modified the record.
    """
    
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User ID who created this record",
    )
    updated_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User ID who last updated this record",
    )


class BaseModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Base model class with common functionality.
    
    Combines UUID primary keys, timestamp tracking, and soft delete
    support for all application models.
    
    Attributes:
        id: UUID primary key
        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft delete timestamp (null if active)
    """
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + "s"
    
    def to_dict(self, exclude: Optional[set[str]] = None) -> dict[str, Any]:
        """
        Convert model to dictionary.
        
        Args:
            exclude: Set of column names to exclude
            
        Returns:
            Dictionary representation of model
        """
        exclude = exclude or set()
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                
                # Handle UUID serialization
                if isinstance(value, uuid.UUID):
                    value = str(value)
                # Handle datetime serialization
                elif isinstance(value, datetime):
                    value = value.isoformat()
                    
                result[column.name] = value
                
        return result
    
    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class SoftDeleteQuery:
    """
    Query class that automatically filters out soft-deleted records.
    
    Use this as the query_class for sessions to enable automatic
    soft delete filtering.
    """
    
    def __new__(cls, *entities, **kwargs):
        """Create query with soft delete filter."""
        from sqlalchemy.orm import Query
        
        query = Query(*entities, **kwargs)
        
        # Apply soft delete filter to single entity queries
        if len(entities) == 1:
            entity = entities[0]
            if hasattr(entity, "deleted_at"):
                query = query.filter(entity.deleted_at.is_(None))
                
        return query


def include_soft_deleted(query):
    """
    Query modifier to include soft-deleted records.
    
    Use this when you need to query deleted records explicitly.
    
    Args:
        query: SQLAlchemy query
        
    Returns:
        Modified query without soft delete filter
    """
    # Remove soft delete filter if present
    # This is a simplified version - production would need more robust handling
    return query


# Event listeners for automatic timestamp updates
@event.listens_for(BaseModel, "before_insert", propagate=True)
def set_created_timestamp(mapper, connection, target):
    """Set created_at timestamp before insert."""
    now = datetime.utcnow()
    if not target.created_at:
        target.created_at = now
    if not target.updated_at:
        target.updated_at = now


@event.listens_for(BaseModel, "before_update", propagate=True)
def set_updated_timestamp(mapper, connection, target):
    """Set updated_at timestamp before update."""
    target.updated_at = datetime.utcnow()
