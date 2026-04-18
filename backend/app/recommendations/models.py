"""
Database Models for Recommendations

SQLAlchemy models for storing user behavior, recommendations,
and user similarities for collaborative filtering.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class UserBehavior(BaseModel):
    """
    User behavior tracking model.
    
    Records user interactions with recommendations, formulas,
    and templates for personalization and analytics.
    """
    
    __tablename__ = "user_behaviors"
    
    # Override soft delete - behaviors are permanent records
    deleted_at = None
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Item being interacted with
    item_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Interaction details
    interaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: shown, viewed, used, accepted, rejected, rated"
    )
    
    # Context when interaction occurred
    context: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Context data: project_type, phase, tags, etc."
    )
    
    # Engagement metrics
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Time spent on item in milliseconds"
    )
    
    # Feedback
    rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User rating (1-5)"
    )
    
    # Session tracking
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", backref="behaviors")
    
    def __repr__(self) -> str:
        return f"<UserBehavior(user={self.user_id}, item={self.item_id}, type={self.interaction_type})>"


class Recommendation(BaseModel):
    """
    Recommendation record model.
    
    Stores generated recommendations for analytics and
    feedback tracking.
    """
    
    __tablename__ = "recommendations"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Recommendation details
    recommendation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type: formula, workflow, template, shortcut"
    )
    
    item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Recommendation metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Scoring
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )
    context_match: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    
    # Generation context
    generation_context: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Context used to generate this recommendation"
    )
    
    # Reason for recommendation
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Why this was recommended"
    )
    
    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="engine",
        comment="Source: template, rule, personalized, collaborative"
    )
    
    # Whether user acted on it
    was_accepted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationship
    user: Mapped["User"] = relationship("User", backref="recommendations")
    
    def __repr__(self) -> str:
        return f"<Recommendation(user={self.user_id}, item={self.item_id}, confidence={self.confidence})>"


class RecommendationFeedback(BaseModel):
    """
    User feedback on recommendations.
    
    Explicit feedback for recommendation quality improvement.
    """
    
    __tablename__ = "recommendation_feedbacks"
    
    # Override soft delete
    deleted_at = None
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    recommendation_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    # Feedback details
    feedback_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type: helpful, not_helpful, irrelevant, accepted, rejected"
    )
    
    # Optional comment
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Additional data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relationship
    user: Mapped["User"] = relationship("User", backref="recommendation_feedbacks")
    
    def __repr__(self) -> str:
        return f"<RecommendationFeedback(user={self.user_id}, type={self.feedback_type})>"


class UserSimilarity(BaseModel):
    """
    User similarity scores for collaborative filtering.
    
    Pre-calculated similarity between user pairs based on
    behavior patterns.
    """
    
    __tablename__ = "user_similarities"
    
    # Override soft delete and timestamps
    deleted_at = None
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    similar_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Similarity score (0-1)
    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
    )
    
    # Calculation method
    calculation_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="jaccard_cosine",
        comment="Method used to calculate similarity"
    )
    
    # Common items count
    common_items: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of items both users interacted with"
    )
    
    # Last recalculation
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    def __repr__(self) -> str:
        return f"<UserSimilarity({self.user_id} ~ {self.similar_user_id}: {self.similarity_score:.2f})>"


class TemplateUsage(BaseModel):
    """
    Aggregated template usage statistics.
    
    Pre-aggregated usage data for performance optimization.
    """
    
    __tablename__ = "template_usage_stats"
    
    # Override soft delete
    deleted_at = None
    
    template_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Usage counts
    total_uses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    unique_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Category for grouping
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Time-based stats
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Daily usage for trend analysis
    daily_stats: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Daily usage counts for last 30 days"
    )
    
    def __repr__(self) -> str:
        return f"<TemplateUsage({self.template_id}: {self.total_uses} uses)>"


# Import here to avoid circular imports
def get_db():
    """Get database session."""
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
