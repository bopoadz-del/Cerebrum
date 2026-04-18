"""
Formula Executor Database Models

Models for logging formula executions and maintaining audit trail.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from sqlalchemy import Column, String, DateTime, Float, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User


class FormulaExecutionLog(Base):
    """
    Log of formula executions for audit trail.
    
    Tracks:
    - Who executed what formula
    - Input and output values
    - Credibility scores
    - Execution metadata (time, source, etc.)
    """
    
    __tablename__ = "formula_execution_logs"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Execution identifier (exposed to API)
    execution_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    
    # User context
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Formula information
    formula_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    formula_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    formula_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Execution data
    inputs: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    outputs: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Credibility scoring
    credibility_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    credibility_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uncertain"
    )
    credibility_factors: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Execution status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Timing
    execution_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="api"
    )  # api, chat, agent, natural_language
    request_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="formula_executions")
    
    # Indexes
    __table_args__ = (
        Index("idx_formula_exec_user_time", "user_id", "executed_at"),
        Index("idx_formula_exec_type_status", "formula_type", "status"),
        Index("idx_formula_exec_score", "credibility_score"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "execution_id": self.execution_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "formula_id": self.formula_id,
            "formula_type": self.formula_type,
            "formula_name": self.formula_name,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "credibility": {
                "score": self.credibility_score,
                "level": self.credibility_level,
                "factors": self.credibility_factors
            },
            "status": self.status,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "source": self.source,
            "request_id": self.request_id,
        }


class FormulaAuditLogger:
    """
    Audit logger for formula executions.
    
    Provides interface for logging formula executions
    to the database with proper audit trail.
    """
    
    async def log_formula_execution(
        self,
        execution_id: str,
        user_id: Optional[uuid.UUID],
        formula_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        credibility_score: float,
        status: str,
        error_message: Optional[str] = None,
        source: str = "api",
        request_id: Optional[str] = None,
        db_session=None
    ) -> str:
        """
        Log a formula execution to the audit database.
        
        Args:
            execution_id: Unique execution identifier
            user_id: User who executed the formula
            formula_id: Formula that was executed
            inputs: Input values
            outputs: Output values
            credibility_score: Calculated credibility score
            status: Execution status
            error_message: Error message if failed
            source: Source of execution (api, chat, agent)
            request_id: Request correlation ID
            db_session: Database session (will create if None)
        
        Returns:
            Audit log ID
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import async_session
        
        # Create log entry
        log_entry = FormulaExecutionLog(
            execution_id=execution_id,
            user_id=user_id,
            formula_id=formula_id,
            formula_type=outputs.get("formula_type", "unknown") if isinstance(outputs, dict) else "unknown",
            formula_name=outputs.get("formula_name") if isinstance(outputs, dict) else None,
            inputs=inputs,
            outputs=outputs if isinstance(outputs, dict) else {"result": outputs},
            credibility_score=credibility_score,
            credibility_level=self._get_credibility_level(credibility_score),
            status=status,
            error_message=error_message,
            source=source,
            request_id=request_id
        )
        
        # Save to database
        if db_session:
            db_session.add(log_entry)
            await db_session.flush()
        else:
            async with async_session() as session:
                session.add(log_entry)
                await session.commit()
        
        return str(log_entry.id)
    
    def _get_credibility_level(self, score: float) -> str:
        """Get credibility level string from score."""
        if score > 0.8:
            return "high"
        elif score > 0.5:
            return "medium"
        elif score > 0.3:
            return "low"
        else:
            return "uncertain"
    
    async def get_execution_history(
        self,
        user_id: Optional[uuid.UUID] = None,
        formula_id: Optional[str] = None,
        formula_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        db_session=None
    ) -> list:
        """
        Get execution history with optional filters.
        
        Args:
            user_id: Filter by user
            formula_id: Filter by formula
            formula_type: Filter by formula type
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset
            db_session: Database session
        
        Returns:
            List of FormulaExecutionLog entries
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import async_session
        
        session = db_session or async_session()
        
        query = select(FormulaExecutionLog)
        
        if user_id:
            query = query.where(FormulaExecutionLog.user_id == user_id)
        if formula_id:
            query = query.where(FormulaExecutionLog.formula_id == formula_id)
        if formula_type:
            query = query.where(FormulaExecutionLog.formula_type == formula_type)
        if status:
            query = query.where(FormulaExecutionLog.status == status)
        
        query = query.order_by(FormulaExecutionLog.executed_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        entries = result.scalars().all()
        
        if not db_session:
            await session.close()
        
        return list(entries)
    
    async def get_execution_stats(
        self,
        user_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db_session=None
    ) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            user_id: Filter by user
            start_date: Start of date range
            end_date: End of date range
            db_session: Database session
        
        Returns:
            Statistics dictionary
        """
        from sqlalchemy import func, select
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import async_session
        
        session = db_session or async_session()
        
        query = select(
            func.count().label("total"),
            func.avg(FormulaExecutionLog.credibility_score).label("avg_credibility"),
            func.avg(FormulaExecutionLog.execution_time_ms).label("avg_execution_time"),
            func.sum(
                func.case(
                    (FormulaExecutionLog.status == "success", 1),
                    else_=0
                )
            ).label("success_count")
        )
        
        if user_id:
            query = query.where(FormulaExecutionLog.user_id == user_id)
        if start_date:
            query = query.where(FormulaExecutionLog.executed_at >= start_date)
        if end_date:
            query = query.where(FormulaExecutionLog.executed_at <= end_date)
        
        result = await session.execute(query)
        row = result.one()
        
        # Get by type
        type_query = select(
            FormulaExecutionLog.formula_type,
            func.count().label("count")
        ).group_by(FormulaExecutionLog.formula_type)
        
        if user_id:
            type_query = type_query.where(FormulaExecutionLog.user_id == user_id)
        if start_date:
            type_query = type_query.where(FormulaExecutionLog.executed_at >= start_date)
        if end_date:
            type_query = type_query.where(FormulaExecutionLog.executed_at <= end_date)
        
        type_result = await session.execute(type_query)
        by_type = {row[0]: row[1] for row in type_result.all()}
        
        if not db_session:
            await session.close()
        
        total = row.total or 0
        success = row.success_count or 0
        
        return {
            "total_executions": total,
            "successful": success,
            "failed": total - success,
            "success_rate": success / total if total > 0 else 0.0,
            "average_credibility": round(row.avg_credibility or 0, 3),
            "average_execution_time_ms": round(row.avg_execution_time or 0, 2),
            "by_formula_type": by_type
        }


# Global audit logger instance
_formula_audit_logger: Optional[FormulaAuditLogger] = None


def get_formula_audit_logger() -> FormulaAuditLogger:
    """Get or create formula audit logger singleton."""
    global _formula_audit_logger
    if _formula_audit_logger is None:
        _formula_audit_logger = FormulaAuditLogger()
    return _formula_audit_logger
