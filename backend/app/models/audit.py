"""
Audit Log Model

Provides comprehensive audit logging with hash chain integrity
for tamper-evident logging.
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.models.user import User

logger = get_logger(__name__)


class AuditLog(Base):
    """
    Audit log entry with hash chain integrity.
    
    Each audit log entry includes a hash of the previous entry,
    creating a tamper-evident chain of records.
    
    Attributes:
        id: UUID primary key
        timestamp: When the action occurred
        user_id: User who performed the action
        tenant_id: Tenant context
        action: Action type (create, update, delete, login, etc.)
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        details: Additional details (JSON)
        ip_address: Client IP address
        user_agent: Client user agent
        request_id: Request correlation ID
        previous_hash: Hash of previous audit log entry
        current_hash: Hash of this entry
    """
    
    __tablename__ = "audit_logs"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    
    # User context
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Action details
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Client context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Hash chain for integrity
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"resource={self.resource_type}, user_id={self.user_id})>"
        )
    
    @staticmethod
    def calculate_hash(
        timestamp: datetime,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        details: Optional[dict],
        previous_hash: Optional[str],
    ) -> str:
        """
        Calculate hash for audit log entry.
        
        Args:
            timestamp: Entry timestamp
            user_id: User ID
            action: Action type
            resource_type: Resource type
            resource_id: Resource ID
            details: Additional details
            previous_hash: Previous entry hash
            
        Returns:
            SHA-256 hash string
        """
        # Create hash data
        hash_data = {
            "timestamp": timestamp.isoformat() if timestamp else None,
            "user_id": str(user_id) if user_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": json.dumps(details, sort_keys=True, default=str) if details else None,
            "previous_hash": previous_hash,
        }
        
        # Create canonical JSON representation
        hash_string = json.dumps(hash_data, sort_keys=True, separators=(",", ":"))
        
        # Calculate SHA-256 hash
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def verify_integrity(self, previous_entry: Optional["AuditLog"] = None) -> bool:
        """
        Verify entry integrity by recalculating hash.
        
        Args:
            previous_entry: Previous audit log entry
            
        Returns:
            True if integrity is verified
        """
        # Verify previous hash matches
        if previous_entry:
            expected_previous_hash = previous_entry.current_hash
            if self.previous_hash != expected_previous_hash:
                logger.error(
                    "Audit log chain broken",
                    entry_id=str(self.id),
                    expected=self.previous_hash,
                    actual=expected_previous_hash,
                )
                return False
        
        # Recalculate current hash
        calculated_hash = self.calculate_hash(
            timestamp=self.timestamp,
            user_id=self.user_id,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            details=self.details,
            previous_hash=self.previous_hash,
        )
        
        if calculated_hash != self.current_hash:
            logger.error(
                "Audit log hash mismatch",
                entry_id=str(self.id),
                expected=self.current_hash,
                actual=calculated_hash,
            )
            return False
        
        return True
    
    def to_dict(self) -> dict:
        """Convert audit log to dictionary."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
        }


class AuditLogger:
    """
    Audit logger for creating tamper-evident audit logs.
    
    Manages the hash chain and creates audit log entries.
    """
    
    def __init__(self) -> None:
        """Initialize audit logger."""
        self._last_hash: Optional[str] = None
    
    async def log(
        self,
        db_session: Any,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Create audit log entry.
        
        Args:
            db_session: Database session
            action: Action type
            resource_type: Resource type
            resource_id: Resource ID
            user_id: User ID
            tenant_id: Tenant ID
            details: Additional details
            ip_address: Client IP
            user_agent: User agent
            request_id: Request ID
            session_id: Session ID
            
        Returns:
            Created audit log entry
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        
        session: AsyncSession = db_session
        
        # Get last audit log for hash chain
        result = await session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1)
        )
        last_entry = result.scalar_one_or_none()
        previous_hash = last_entry.current_hash if last_entry else None
        
        # Create timestamp
        timestamp = datetime.utcnow()
        
        # Calculate hash
        current_hash = AuditLog.calculate_hash(
            timestamp=timestamp,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            previous_hash=previous_hash,
        )
        
        # Create audit log entry
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=timestamp,
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            previous_hash=previous_hash,
            current_hash=current_hash,
        )
        
        session.add(audit_log)
        await session.flush()
        
        logger.debug(
            f"Audit log created",
            action=action,
            resource_type=resource_type,
            user_id=str(user_id) if user_id else None,
        )
        
        return audit_log
    
    async def verify_chain(
        self,
        db_session: Any,
        limit: int = 1000,
    ) -> tuple[bool, list]:
        """
        Verify integrity of audit log chain.
        
        Args:
            db_session: Database session
            limit: Maximum entries to verify
            
        Returns:
            Tuple of (is_valid, list of invalid entry IDs)
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        
        session: AsyncSession = db_session
        
        result = await session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.asc()).limit(limit)
        )
        entries = result.scalars().all()
        
        invalid_entries = []
        previous_entry = None
        
        for entry in entries:
            if not entry.verify_integrity(previous_entry):
                invalid_entries.append(str(entry.id))
            previous_entry = entry
        
        is_valid = len(invalid_entries) == 0
        
        if not is_valid:
            logger.error(
                f"Audit log chain verification failed",
                invalid_count=len(invalid_entries),
            )
        
        return is_valid, invalid_entries


# Global audit logger instance
audit_logger = AuditLogger()
