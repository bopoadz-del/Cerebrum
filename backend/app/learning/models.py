"""
Learning Engine Database Models

Models for:
- Formula performance tracking
- Tier history (promotions/demotions)
- Coefficient adjustments
- Feedback loops
- Reinforcement learning episodes
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

from sqlalchemy import (
    Column, String, DateTime, Float, Text, ForeignKey, Index, 
    Integer, Boolean, ARRAY, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, BaseModel, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PerformanceOutcome(str, Enum):
    """Outcome of formula execution for learning purposes."""
    EXCELLENT = "excellent"  # > 95% accuracy
    GOOD = "good"            # 80-95% accuracy
    ACCEPTABLE = "acceptable"  # 60-80% accuracy
    POOR = "poor"            # 40-60% accuracy
    FAILED = "failed"        # < 40% accuracy


class TierChangeType(str, Enum):
    """Type of tier change."""
    PROMOTION = "promotion"
    DEMOTION = "demotion"
    MAINTAINED = "maintained"
    MANUAL_OVERRIDE = "manual_override"


class FeedbackType(str, Enum):
    """Type of feedback for learning."""
    USER_RATING = "user_rating"
    EXPERT_VALIDATION = "expert_validation"
    REAL_WORLD_RESULT = "real_world_result"
    AUTOMATED_CHECK = "automated_check"
    MANUAL_CORRECTION = "manual_correction"


class LearningModel(BaseModel):
    """
    Machine learning models for formula prediction and suggestion.
    
    Tracks model versions, performance metrics, and deployment status.
    """
    
    __tablename__ = "learning_models"
    
    # Model identification
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="Type: formula_suggester, coefficient_predictor, tier_classifier"
    )
    
    # Model metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    architecture: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        comment="Model architecture (e.g., transformer, ensemble, neural_network)"
    )
    hyperparameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=False, 
        default=dict
    )
    
    # Training info
    training_data_size: Mapped[int] = mapped_column(Integer, default=0)
    training_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    training_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    training_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Performance metrics
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mean_squared_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Deployment status
    is_deployed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deployment_threshold: Mapped[float] = mapped_column(
        Float, 
        default=0.75,
        comment="Minimum accuracy threshold for auto-deployment"
    )
    
    # Model weights/artifacts (stored as file reference)
    artifact_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    performance_history: Mapped[List["ModelPerformance"]] = relationship(
        "ModelPerformance",
        back_populates="model",
        lazy="dynamic"
    )
    
    __table_args__ = (
        Index("idx_learning_model_name_version", "model_name", "model_version", unique=True),
        Index("idx_learning_model_type_deployed", "model_type", "is_deployed"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_type": self.model_type,
            "description": self.description,
            "architecture": self.architecture,
            "hyperparameters": self.hyperparameters,
            "training_data_size": self.training_data_size,
            "training_duration": (
                (self.training_end - self.training_start).total_seconds() / 3600
                if self.training_start and self.training_end else None
            ),
            "metrics": {
                "accuracy": self.accuracy,
                "precision": self.precision,
                "recall": self.recall,
                "f1_score": self.f1_score,
                "mean_squared_error": self.mean_squared_error,
            },
            "is_deployed": self.is_deployed,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ModelPerformance(BaseModel):
    """
    Performance metrics for a learning model over time.
    
    Tracks model performance on production data.
    """
    
    __tablename__ = "model_performance"
    
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Time period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Metrics
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    correct_predictions: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Latency
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p99_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Error analysis
    false_positives: Mapped[int] = mapped_column(Integer, default=0)
    false_negatives: Mapped[int] = mapped_column(Integer, default=0)
    
    # Distribution by outcome
    excellent_count: Mapped[int] = mapped_column(Integer, default=0)
    good_count: Mapped[int] = mapped_column(Integer, default=0)
    acceptable_count: Mapped[int] = mapped_column(Integer, default=0)
    poor_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationship
    model: Mapped["LearningModel"] = relationship("LearningModel", back_populates="performance_history")
    
    __table_args__ = (
        Index("idx_model_performance_model_period", "model_id", "period_start", "period_end"),
    )


class FormulaPerformance(BaseModel):
    """
    Performance tracking for individual formulas.
    
    Tracks how well each formula performs based on real-world usage
    and expert validation.
    """
    
    __tablename__ = "formula_performance"
    
    # Formula identification
    formula_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    formula_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Source tracking
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Execution statistics
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    successful_executions: Mapped[int] = mapped_column(Integer, default=0)
    failed_executions: Mapped[int] = mapped_column(Integer, default=0)
    
    # Credibility metrics
    avg_credibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Quality metrics (from expert validation)
    expert_validations: Mapped[int] = mapped_column(Integer, default=0)
    expert_approval_rate: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Real-world accuracy (when actual results are available)
    real_world_tests: Mapped[int] = mapped_column(Integer, default=0)
    real_world_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Calculated performance score (0-1)
    performance_score: Mapped[float] = mapped_column(
        Float, 
        default=0.0,
        comment="Weighted performance score for tier decisions"
    )
    
    # Last evaluation
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Outcome distribution
    outcome_distribution: Mapped[Dict[str, int]] = mapped_column(
        JSONB,
        default=lambda: {
            "excellent": 0,
            "good": 0,
            "acceptable": 0,
            "poor": 0,
            "failed": 0,
        }
    )
    
    __table_args__ = (
        Index("idx_formula_perf_source", "source_id", "current_tier"),
        Index("idx_formula_perf_score", "performance_score"),
        Index("idx_formula_perf_formula", "formula_id", "current_tier"),
    )
    
    def calculate_performance_score(self) -> float:
        """
        Calculate weighted performance score.
        
        Formula considers:
        - Success rate (40%)
        - Credibility score (25%)
        - Expert approval (20%)
        - Real-world accuracy (15%)
        """
        if self.total_executions == 0:
            return 0.0
        
        success_rate = self.successful_executions / self.total_executions
        
        # Weight the components
        score = (
            success_rate * 0.4 +
            self.avg_credibility_score * 0.25 +
            self.expert_approval_rate * 0.2 +
            self.real_world_accuracy * 0.15
        )
        
        return min(1.0, max(0.0, score))
    
    def update_performance_score(self) -> None:
        """Update the performance score based on current metrics."""
        self.performance_score = self.calculate_performance_score()
        self.last_evaluated_at = datetime.utcnow()


class TierHistory(BaseModel):
    """
    History of tier changes for formula sources.
    
    Tracks when sources are promoted or demoted between credibility tiers.
    """
    
    __tablename__ = "tier_history"
    
    # Source identification
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Tier change
    previous_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    new_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[TierChangeType] = mapped_column(
        SQLEnum(TierChangeType),
        nullable=False
    )
    
    # Reasoning
    performance_score: Mapped[float] = mapped_column(Float, nullable=False)
    formulas_submitted: Mapped[int] = mapped_column(Integer, default=0)
    formulas_accepted: Mapped[int] = mapped_column(Integer, default=0)
    
    # Change reason
    change_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Detailed reason for the tier change"
    )
    
    # Who/what triggered the change
    triggered_by: Mapped[str] = mapped_column(
        String(50),
        default="system",
        comment="system, admin, user_id, or model_version"
    )
    
    # Calculated values at time of change
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0)
    acceptance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    
    __table_args__ = (
        Index("idx_tier_history_source", "source_id", "created_at"),
        Index("idx_tier_history_change", "change_type", "created_at"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "previous_tier": self.previous_tier,
            "new_tier": self.new_tier,
            "change_type": self.change_type.value,
            "performance_score": self.performance_score,
            "reputation_score": self.reputation_score,
            "acceptance_rate": self.acceptance_rate,
            "change_reason": self.change_reason,
            "triggered_by": self.triggered_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CoefficientAdjustment(BaseModel):
    """
    Auto-tuning adjustments for formula coefficients.
    
    Tracks changes to formula parameters based on learning from
    execution results and real-world feedback.
    """
    
    __tablename__ = "coefficient_adjustments"
    
    # Formula identification
    formula_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    formula_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Coefficient info
    coefficient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_value: Mapped[float] = mapped_column(Float, nullable=False)
    new_value: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Adjustment metadata
    adjustment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="gradient_descent, bayesian_optimization, expert_suggestion"
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.5,
        comment="Confidence in the adjustment (0-1)"
    )
    
    # Learning context
    training_samples: Mapped[int] = mapped_column(Integer, default=0)
    error_reduction: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="Percentage reduction in prediction error"
    )
    
    # Validation
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Reasoning
    adjustment_reason: Mapped[str] = mapped_column(Text, nullable=False)
    learning_signal: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        comment="Raw learning signal that triggered the adjustment"
    )
    
    # Rollback info
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    __table_args__ = (
        Index("idx_coef_adj_formula", "formula_id", "coefficient_name", "created_at"),
        Index("idx_coef_adj_confidence", "confidence", "validated"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "formula_id": self.formula_id,
            "formula_type": self.formula_type,
            "coefficient_name": self.coefficient_name,
            "previous_value": self.previous_value,
            "new_value": self.new_value,
            "adjustment_method": self.adjustment_method,
            "confidence": self.confidence,
            "training_samples": self.training_samples,
            "error_reduction": self.error_reduction,
            "validated": self.validated,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "rolled_back": self.rolled_back,
            "adjustment_reason": self.adjustment_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FeedbackLoop(BaseModel):
    """
    Feedback loop entries for continuous learning.
    
    Connects formula execution results with real-world outcomes
    to improve future predictions.
    """
    
    __tablename__ = "feedback_loops"
    
    # Execution reference
    execution_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    formula_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    formula_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Source tracking
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Feedback info
    feedback_type: Mapped[FeedbackType] = mapped_column(SQLEnum(FeedbackType), nullable=False)
    
    # Prediction vs actual
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    actual_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prediction_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Feedback data
    feedback_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        comment="Structured feedback data (ratings, comments, etc.)"
    )
    
    # Outcome
    outcome: Mapped[PerformanceOutcome] = mapped_column(
        SQLEnum(PerformanceOutcome),
        nullable=False
    )
    
    # Learning processed
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Model that made the prediction (if applicable)
    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_models.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Reward signal for RL
    reward_signal: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="Calculated reward signal (-1 to 1)"
    )
    
    __table_args__ = (
        Index("idx_feedback_loop_source", "source_id", "processed"),
        Index("idx_feedback_loop_formula", "formula_id", "outcome"),
        Index("idx_feedback_loop_type", "feedback_type", "created_at"),
    )
    
    def calculate_reward(self) -> float:
        """
        Calculate reward signal based on outcome.
        
        Returns:
            Float between -1 (bad) and 1 (excellent)
        """
        reward_map = {
            PerformanceOutcome.EXCELLENT: 1.0,
            PerformanceOutcome.GOOD: 0.6,
            PerformanceOutcome.ACCEPTABLE: 0.2,
            PerformanceOutcome.POOR: -0.4,
            PerformanceOutcome.FAILED: -1.0,
        }
        return reward_map.get(self.outcome, 0.0)
    
    def process(self) -> None:
        """Mark as processed and calculate reward."""
        self.processed = True
        self.processed_at = datetime.utcnow()
        self.reward_signal = self.calculate_reward()


class ReinforcementEpisode(BaseModel):
    """
    Reinforcement learning episodes for formula suggestion.
    
    Tracks state-action-reward sequences for training RL agents.
    """
    
    __tablename__ = "reinforcement_episodes"
    
    # Episode identification
    episode_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    
    # Model reference
    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_models.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # State (context in which formula was suggested)
    state: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="Context: user query, project type, constraints, etc."
    )
    
    # Action (formula suggested)
    suggested_formula_id: Mapped[str] = mapped_column(String(100), nullable=False)
    suggested_formula_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Alternative options (for learning)
    alternatives: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        comment="Alternative formulas that were considered"
    )
    
    # Outcome
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # Reward (calculated from outcome)
    immediate_reward: Mapped[float] = mapped_column(Float, default=0.0)
    delayed_reward: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_reward: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Feedback
    user_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Temporal info
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Learning processed
    processed_for_training: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("idx_rl_episode_model", "model_id", "processed_for_training"),
        Index("idx_rl_episode_formula", "suggested_formula_id", "selected"),
    )
    
    def complete(self, success: bool, user_rating: Optional[int] = None) -> None:
        """Mark episode as complete with outcome."""
        self.executed = True
        self.execution_success = success
        self.completed_at = datetime.utcnow()
        self.user_rating = user_rating
        
        # Calculate immediate reward
        if success:
            self.immediate_reward = 0.5
            if user_rating:
                # Scale user rating (1-5) to reward (-0.5 to 0.5)
                self.immediate_reward += (user_rating - 3) / 10
        else:
            self.immediate_reward = -0.5
    
    def calculate_final_reward(self, feedback_outcome: PerformanceOutcome) -> float:
        """
        Calculate final reward incorporating feedback loop outcome.
        
        Args:
            feedback_outcome: Outcome from feedback loop
            
        Returns:
            Final reward value
        """
        outcome_rewards = {
            PerformanceOutcome.EXCELLENT: 1.0,
            PerformanceOutcome.GOOD: 0.7,
            PerformanceOutcome.ACCEPTABLE: 0.3,
            PerformanceOutcome.POOR: -0.3,
            PerformanceOutcome.FAILED: -0.7,
        }
        
        delayed = outcome_rewards.get(feedback_outcome, 0.0)
        self.delayed_reward = delayed
        
        # Combine immediate and delayed rewards
        # Immediate: 40%, Delayed: 60% (delayed has more info)
        self.final_reward = self.immediate_reward * 0.4 + delayed * 0.6
        
        return self.final_reward


class SourceReputation(BaseModel):
    """
    Aggregated reputation scores for formula sources.
    
    Fast lookup for credibility system decisions.
    """
    
    __tablename__ = "source_reputation"
    
    # Source identification
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Current tier
    current_tier: Mapped[int] = mapped_column(Integer, default=5, index=True)
    
    # Reputation metrics
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Formula counts
    formulas_submitted: Mapped[int] = mapped_column(Integer, default=0)
    formulas_accepted: Mapped[int] = mapped_column(Integer, default=0)
    formulas_rejected: Mapped[int] = mapped_column(Integer, default=0)
    
    # Performance
    avg_performance_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    
    # Tier history
    tier_changes: Mapped[int] = mapped_column(Integer, default=0)
    last_tier_change: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Stability (how long in current tier)
    tier_since: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Flags
    under_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Computed score components
    acceptance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    consistency_score: Mapped[float] = mapped_column(Float, default=0.0)
    longevity_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    __table_args__ = (
        Index("idx_source_rep_tier", "current_tier", "reputation_score"),
        Index("idx_source_rep_score", "reputation_score"),
    )
    
    def calculate_reputation(self) -> float:
        """
        Calculate comprehensive reputation score.
        
        Formula:
        - Acceptance rate: 40%
        - Performance score: 30%
        - Consistency (time in tier): 15%
        - Longevity (total activity): 15%
        """
        if self.formulas_submitted == 0:
            return 0.0
        
        # Acceptance rate
        self.acceptance_rate = (
            self.formulas_accepted / self.formulas_submitted 
            if self.formulas_submitted > 0 else 0.0
        )
        
        # Consistency (normalized time in current tier)
        days_in_tier = (datetime.utcnow() - self.tier_since).days
        self.consistency_score = min(1.0, days_in_tier / 30)  # Max at 30 days
        
        # Longevity (based on total activity)
        activity_score = min(1.0, self.total_executions / 100)  # Max at 100 executions
        self.longevity_score = activity_score
        
        # Weighted combination
        self.reputation_score = (
            self.acceptance_rate * 0.4 +
            self.avg_performance_score * 0.3 +
            self.consistency_score * 0.15 +
            self.longevity_score * 0.15
        )
        
        return self.reputation_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "current_tier": self.current_tier,
            "reputation_score": round(self.reputation_score, 3),
            "formulas_submitted": self.formulas_submitted,
            "formulas_accepted": self.formulas_accepted,
            "acceptance_rate": round(self.acceptance_rate, 3),
            "avg_performance_score": round(self.avg_performance_score, 3),
            "total_executions": self.total_executions,
            "tier_changes": self.tier_changes,
            "tier_since": self.tier_since.isoformat() if self.tier_since else None,
            "under_review": self.under_review,
        }
