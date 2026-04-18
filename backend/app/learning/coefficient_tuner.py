"""
Coefficient Tuner - Auto-Tuning for Formula Parameters

Intelligent auto-tuning system for formula coefficients based on:
- Feedback loop results
- Real-world performance data
- Bayesian optimization
- Gradient-based adjustments
"""

import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from app.core.logging import get_logger
from app.learning.models import (
    CoefficientAdjustment,
    FeedbackLoop,
    FormulaPerformance,
    PerformanceOutcome,
)
from app.executor.models import FormulaExecutionLog

logger = get_logger(__name__)


class TuningMethod(str, Enum):
    """Coefficient tuning methods."""
    GRADIENT_DESCENT = "gradient_descent"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"
    EXPERT_SUGGESTION = "expert_suggestion"
    MOVING_AVERAGE = "moving_average"
    LINEAR_REGRESSION = "linear_regression"


@dataclass
class CoefficientSuggestion:
    """Suggested coefficient adjustment."""
    coefficient_name: str
    current_value: float
    suggested_value: float
    confidence: float
    method: TuningMethod
    reason: str
    expected_error_reduction: float


@dataclass
class TuningResult:
    """Result of coefficient tuning process."""
    formula_id: str
    coefficient_name: str
    old_value: float
    new_value: float
    method: TuningMethod
    confidence: float
    adjustment_id: Optional[str] = None


class CoefficientTuner:
    """
    Auto-tunes formula coefficients based on performance data.
    
    Supports multiple tuning methods:
    - Gradient descent for continuous optimization
    - Bayesian optimization for exploration/exploitation
    - Moving average for stability
    - Linear regression for trend-based prediction
    """
    
    # Tuning hyperparameters
    DEFAULT_LEARNING_RATE = 0.01
    MIN_SAMPLES_FOR_TUNING = 20
    MAX_ADJUSTMENT_PCT = 0.15  # Max 15% change per adjustment
    CONFIDENCE_THRESHOLD = 0.70
    
    # Moving average window sizes
    MA_SHORT_WINDOW = 10
    MA_LONG_WINDOW = 30
    
    def __init__(self, learning_rate: float = DEFAULT_LEARNING_RATE):
        self.learning_rate = learning_rate
        self._adjustment_cache: Dict[str, List[CoefficientAdjustment]] = {}
    
    async def analyze_coefficient_performance(
        self,
        formula_id: str,
        coefficient_name: str,
        db_session: AsyncSession,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze performance of a specific coefficient.
        
        Args:
            formula_id: Formula identifier
            coefficient_name: Coefficient to analyze
            db_session: Database session
            lookback_days: Days of history to analyze
            
        Returns:
            Performance analysis dictionary
        """
        start_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get feedback loop entries for this formula
        query = select(FeedbackLoop).where(
            and_(
                FeedbackLoop.formula_id == formula_id,
                FeedbackLoop.created_at >= start_date,
                FeedbackLoop.processed == True
            )
        ).order_by(desc(FeedbackLoop.created_at))
        
        result = await db_session.execute(query)
        feedbacks = result.scalars().all()
        
        if len(feedbacks) < self.MIN_SAMPLES_FOR_TUNING:
            return {
                "formula_id": formula_id,
                "coefficient_name": coefficient_name,
                "sufficient_data": False,
                "sample_count": len(feedbacks),
                "min_required": self.MIN_SAMPLES_FOR_TUNING,
            }
        
        # Calculate statistics
        errors = [f.prediction_error for f in feedbacks if f.prediction_error is not None]
        
        if not errors:
            return {
                "formula_id": formula_id,
                "coefficient_name": coefficient_name,
                "sufficient_data": True,
                "sample_count": len(feedbacks),
                "has_error_data": False,
            }
        
        avg_error = sum(errors) / len(errors)
        mse = sum(e ** 2 for e in errors) / len(errors)
        rmse = math.sqrt(mse)
        
        # Error trend (recent vs older)
        mid = len(errors) // 2
        recent_avg = sum(errors[:mid]) / max(1, mid)
        older_avg = sum(errors[mid:]) / max(1, len(errors) - mid)
        error_trend = recent_avg - older_avg
        
        # Outcome distribution
        outcomes = {outcome: 0 for outcome in PerformanceOutcome}
        for f in feedbacks:
            outcomes[f.outcome] += 1
        
        return {
            "formula_id": formula_id,
            "coefficient_name": coefficient_name,
            "sufficient_data": True,
            "sample_count": len(feedbacks),
            "has_error_data": True,
            "avg_error": round(avg_error, 4),
            "rmse": round(rmse, 4),
            "error_trend": round(error_trend, 4),
            "error_trend_direction": "improving" if error_trend < 0 else "degrading" if error_trend > 0 else "stable",
            "outcome_distribution": {k.value: v for k, v in outcomes.items()},
            "good_outcome_rate": round(
                (outcomes[PerformanceOutcome.EXCELLENT] + outcomes[PerformanceOutcome.GOOD]) / len(feedbacks),
                3
            ),
        }
    
    async def suggest_coefficient_adjustment(
        self,
        formula_id: str,
        coefficient_name: str,
        current_value: float,
        db_session: AsyncSession,
        method: TuningMethod = TuningMethod.GRADIENT_DESCENT
    ) -> Optional[CoefficientSuggestion]:
        """
        Suggest a coefficient adjustment.
        
        Args:
            formula_id: Formula identifier
            coefficient_name: Coefficient to analyze
            current_value: Current coefficient value
            db_session: Database session
            method: Tuning method to use
            
        Returns:
            CoefficientSuggestion if adjustment recommended
        """
        # Analyze performance
        analysis = await self.analyze_coefficient_performance(
            formula_id, coefficient_name, db_session
        )
        
        if not analysis.get("sufficient_data"):
            return None
        
        if not analysis.get("has_error_data"):
            return None
        
        # Calculate suggested value based on method
        if method == TuningMethod.GRADIENT_DESCENT:
            suggestion = self._gradient_descent_suggestion(
                formula_id, coefficient_name, current_value, analysis, db_session
            )
        elif method == TuningMethod.MOVING_AVERAGE:
            suggestion = await self._moving_average_suggestion(
                formula_id, coefficient_name, current_value, db_session
            )
        elif method == TuningMethod.BAYESIAN_OPTIMIZATION:
            suggestion = self._bayesian_suggestion(
                formula_id, coefficient_name, current_value, analysis
            )
        elif method == TuningMethod.LINEAR_REGRESSION:
            suggestion = await self._linear_regression_suggestion(
                formula_id, coefficient_name, current_value, db_session
            )
        else:
            return None
        
        return suggestion
    
    async def apply_coefficient_adjustment(
        self,
        suggestion: CoefficientSuggestion,
        formula_id: str,
        formula_type: str,
        db_session: AsyncSession,
        auto_validate: bool = False
    ) -> Optional[TuningResult]:
        """
        Apply a coefficient adjustment.
        
        Args:
            suggestion: CoefficientSuggestion to apply
            formula_id: Formula identifier
            formula_type: Formula type
            db_session: Database session
            auto_validate: Auto-validate if confidence is high
            
        Returns:
            TuningResult if adjustment was applied
        """
        # Validate adjustment size
        change_pct = abs(suggestion.suggested_value - suggestion.current_value) / max(
            abs(suggestion.current_value), 0.001
        )
        
        if change_pct > self.MAX_ADJUSTMENT_PCT:
            # Cap the adjustment
            direction = 1 if suggestion.suggested_value > suggestion.current_value else -1
            max_change = suggestion.current_value * self.MAX_ADJUSTMENT_PCT
            capped_value = suggestion.current_value + (direction * max_change)
            
            logger.warning(
                f"Capping coefficient adjustment for {formula_id}.{suggestion.coefficient_name}: "
                f"{suggestion.suggested_value:.4f} -> {capped_value:.4f}"
            )
            suggested_value = capped_value
        else:
            suggested_value = suggestion.suggested_value
        
        # Create adjustment record
        adjustment = CoefficientAdjustment(
            formula_id=formula_id,
            formula_type=formula_type,
            coefficient_name=suggestion.coefficient_name,
            previous_value=suggestion.current_value,
            new_value=suggested_value,
            adjustment_method=suggestion.method.value,
            confidence=suggestion.confidence,
            adjustment_reason=suggestion.reason,
            training_samples=suggestion.expected_error_reduction,
            validated=auto_validate and suggestion.confidence > 0.9,
            validated_at=datetime.utcnow() if (auto_validate and suggestion.confidence > 0.9) else None,
        )
        
        db_session.add(adjustment)
        await db_session.flush()
        
        logger.info(
            f"Coefficient adjustment created: {formula_id}.{suggestion.coefficient_name} "
            f"({suggestion.current_value:.4f} -> {suggested_value:.4f}, "
            f"confidence={suggestion.confidence:.2f})"
        )
        
        return TuningResult(
            formula_id=formula_id,
            coefficient_name=suggestion.coefficient_name,
            old_value=suggestion.current_value,
            new_value=suggested_value,
            method=suggestion.method,
            confidence=suggestion.confidence,
            adjustment_id=str(adjustment.id)
        )
    
    async def batch_tune_formula(
        self,
        formula_id: str,
        formula_type: str,
        coefficients: Dict[str, float],
        db_session: AsyncSession,
        min_confidence: float = 0.7
    ) -> List[TuningResult]:
        """
        Tune multiple coefficients for a formula.
        
        Args:
            formula_id: Formula identifier
            formula_type: Formula type
            coefficients: Dict of coefficient names and current values
            db_session: Database session
            min_confidence: Minimum confidence to apply adjustment
            
        Returns:
            List of applied TuningResults
        """
        results = []
        
        for coeff_name, current_value in coefficients.items():
            # Try different methods, pick best
            suggestion = None
            
            for method in TuningMethod:
                try:
                    candidate = await self.suggest_coefficient_adjustment(
                        formula_id, coeff_name, current_value, db_session, method
                    )
                    
                    if candidate and (suggestion is None or candidate.confidence > suggestion.confidence):
                        suggestion = candidate
                except Exception as e:
                    logger.warning(f"Method {method.value} failed for {coeff_name}: {e}")
                    continue
            
            if suggestion and suggestion.confidence >= min_confidence:
                result = await self.apply_coefficient_adjustment(
                    suggestion, formula_id, formula_type, db_session
                )
                
                if result:
                    results.append(result)
        
        return results
    
    async def rollback_adjustment(
        self,
        adjustment_id: str,
        reason: str,
        db_session: AsyncSession
    ) -> bool:
        """
        Rollback a coefficient adjustment.
        
        Args:
            adjustment_id: ID of adjustment to rollback
            reason: Reason for rollback
            db_session: Database session
            
        Returns:
            True if rollback was successful
        """
        from uuid import UUID
        
        query = select(CoefficientAdjustment).where(
            CoefficientAdjustment.id == UUID(adjustment_id)
        )
        
        result = await db_session.execute(query)
        adjustment = result.scalar_one_or_none()
        
        if not adjustment:
            return False
        
        adjustment.rolled_back = True
        adjustment.rolled_back_at = datetime.utcnow()
        adjustment.rollback_reason = reason
        
        await db_session.flush()
        
        logger.info(
            f"Rolled back coefficient adjustment: {adjustment.formula_id}.{adjustment.coefficient_name} "
            f"({adjustment.new_value:.4f} -> {adjustment.previous_value:.4f})"
        )
        
        return True
    
    async def validate_adjustment(
        self,
        adjustment_id: str,
        user_id: str,
        db_session: AsyncSession
    ) -> bool:
        """
        Validate (approve) a coefficient adjustment.
        
        Args:
            adjustment_id: ID of adjustment to validate
            user_id: User validating the adjustment
            db_session: Database session
            
        Returns:
            True if validation was successful
        """
        from uuid import UUID
        
        query = select(CoefficientAdjustment).where(
            CoefficientAdjustment.id == UUID(adjustment_id)
        )
        
        result = await db_session.execute(query)
        adjustment = result.scalar_one_or_none()
        
        if not adjustment:
            return False
        
        adjustment.validated = True
        adjustment.validated_at = datetime.utcnow()
        adjustment.validated_by = UUID(user_id)
        
        await db_session.flush()
        
        logger.info(
            f"Validated coefficient adjustment: {adjustment.formula_id}.{adjustment.coefficient_name} "
            f"by user {user_id}"
        )
        
        return True
    
    async def get_pending_adjustments(
        self,
        db_session: AsyncSession,
        formula_id: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> List[CoefficientAdjustment]:
        """
        Get pending (unvalidated) coefficient adjustments.
        
        Args:
            db_session: Database session
            formula_id: Filter by formula
            min_confidence: Minimum confidence threshold
            limit: Maximum results
            
        Returns:
            List of pending adjustments
        """
        query = select(CoefficientAdjustment).where(
            and_(
                CoefficientAdjustment.validated == False,
                CoefficientAdjustment.rolled_back == False,
                CoefficientAdjustment.confidence >= min_confidence
            )
        ).order_by(desc(CoefficientAdjustment.confidence))
        
        if formula_id:
            query = query.where(CoefficientAdjustment.formula_id == formula_id)
        
        query = query.limit(limit)
        
        result = await db_session.execute(query)
        return list(result.scalars().all())
    
    async def get_adjustment_history(
        self,
        formula_id: str,
        coefficient_name: Optional[str],
        db_session: AsyncSession,
        limit: int = 50
    ) -> List[CoefficientAdjustment]:
        """
        Get adjustment history for a formula/coefficient.
        
        Args:
            formula_id: Formula identifier
            coefficient_name: Specific coefficient (optional)
            db_session: Database session
            limit: Maximum results
            
        Returns:
            List of adjustments
        """
        query = select(CoefficientAdjustment).where(
            CoefficientAdjustment.formula_id == formula_id
        )
        
        if coefficient_name:
            query = query.where(CoefficientAdjustment.coefficient_name == coefficient_name)
        
        query = query.order_by(desc(CoefficientAdjustment.created_at)).limit(limit)
        
        result = await db_session.execute(query)
        return list(result.scalars().all())
    
    async def calculate_tuning_effectiveness(
        self,
        formula_id: str,
        db_session: AsyncSession,
        days_after: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate effectiveness of recent tunings.
        
        Args:
            formula_id: Formula to analyze
            db_session: Database session
            days_after: Days after adjustment to measure
            
        Returns:
            Effectiveness metrics
        """
        # Get recent adjustments
        adjustments = await self.get_adjustment_history(formula_id, None, db_session, limit=10)
        
        if not adjustments:
            return {"has_adjustments": False}
        
        effectiveness_scores = []
        
        for adj in adjustments:
            if not adj.validated or adj.rolled_back:
                continue
            
            # Get feedback after adjustment
            start_date = adj.created_at
            end_date = start_date + timedelta(days=days_after)
            
            query = select(FeedbackLoop).where(
                and_(
                    FeedbackLoop.formula_id == formula_id,
                    FeedbackLoop.created_at >= start_date,
                    FeedbackLoop.created_at <= end_date,
                    FeedbackLoop.processed == True
                )
            )
            
            result = await db_session.execute(query)
            feedbacks = result.scalars().all()
            
            if len(feedbacks) >= 5:
                avg_error = sum(
                    f.prediction_error for f in feedbacks if f.prediction_error is not None
                ) / max(1, len([f for f in feedbacks if f.prediction_error is not None]))
                
                effectiveness_scores.append({
                    "adjustment_id": str(adj.id),
                    "coefficient": adj.coefficient_name,
                    "samples": len(feedbacks),
                    "avg_error": avg_error,
                })
        
        return {
            "has_adjustments": True,
            "adjustments_analyzed": len(effectiveness_scores),
            "effectiveness_data": effectiveness_scores,
        }
    
    def _gradient_descent_suggestion(
        self,
        formula_id: str,
        coefficient_name: str,
        current_value: float,
        analysis: Dict[str, Any],
        db_session: AsyncSession
    ) -> Optional[CoefficientSuggestion]:
        """Generate suggestion using gradient descent approach."""
        error_trend = analysis.get("error_trend", 0)
        avg_error = analysis.get("avg_error", 0)
        
        # Calculate gradient direction
        # If error is positive (over-prediction), decrease coefficient
        # If error is negative (under-prediction), increase coefficient
        gradient = -math.copysign(1, avg_error) if avg_error != 0 else 0
        
        # Calculate adjustment size
        adjustment = gradient * self.learning_rate * abs(avg_error)
        suggested_value = current_value + adjustment
        
        # Confidence based on sample size and error magnitude
        sample_count = analysis.get("sample_count", 0)
        confidence = min(0.95, 0.5 + (sample_count / 200) + (abs(avg_error) * 0.1))
        
        return CoefficientSuggestion(
            coefficient_name=coefficient_name,
            current_value=current_value,
            suggested_value=suggested_value,
            confidence=confidence,
            method=TuningMethod.GRADIENT_DESCENT,
            reason=(
                f"Gradient descent based on avg_error={avg_error:.4f}, "
                f"trend={analysis.get('error_trend_direction', 'unknown')}"
            ),
            expected_error_reduction=abs(avg_error) * 0.3  # Estimate 30% improvement
        )
    
    async def _moving_average_suggestion(
        self,
        formula_id: str,
        coefficient_name: str,
        current_value: float,
        db_session: AsyncSession
    ) -> Optional[CoefficientSuggestion]:
        """Generate suggestion using moving average convergence."""
        # Get recent execution logs with coefficient values
        query = select(FormulaExecutionLog).where(
            FormulaExecutionLog.formula_id == formula_id
        ).order_by(desc(FormulaExecutionLog.executed_at)).limit(50)
        
        result = await db_session.execute(query)
        executions = result.scalars().all()
        
        # Extract coefficient values from execution inputs
        values = []
        for exec_log in executions:
            if coefficient_name in exec_log.inputs:
                try:
                    val = float(exec_log.inputs[coefficient_name])
                    values.append(val)
                except (ValueError, TypeError):
                    continue
        
        if len(values) < self.MA_LONG_WINDOW:
            return None
        
        # Calculate moving averages
        short_ma = sum(values[:self.MA_SHORT_WINDOW]) / self.MA_SHORT_WINDOW
        long_ma = sum(values[:self.MA_LONG_WINDOW]) / self.MA_LONG_WINDOW
        
        # Suggest convergence toward mean
        if abs(short_ma - long_ma) / max(abs(long_ma), 0.001) > 0.05:
            # Significant divergence - suggest toward long-term average
            suggested_value = long_ma * 0.7 + current_value * 0.3
            
            return CoefficientSuggestion(
                coefficient_name=coefficient_name,
                current_value=current_value,
                suggested_value=suggested_value,
                confidence=0.65,
                method=TuningMethod.MOVING_AVERAGE,
                reason=f"Moving average convergence: short={short_ma:.4f}, long={long_ma:.4f}",
                expected_error_reduction=0.15
            )
        
        return None
    
    def _bayesian_suggestion(
        self,
        formula_id: str,
        coefficient_name: str,
        current_value: float,
        analysis: Dict[str, Any]
    ) -> Optional[CoefficientSuggestion]:
        """Generate suggestion using Bayesian optimization approach."""
        # Simplified Bayesian suggestion
        # In production, this would use a proper Gaussian Process
        
        good_outcome_rate = analysis.get("good_outcome_rate", 0.5)
        
        if good_outcome_rate > 0.8:
            # Current value is good, small exploration
            exploration_range = current_value * 0.02
            suggested_value = current_value + (exploration_range * (2 * 0.5 - 1))
            confidence = 0.6
        elif good_outcome_rate < 0.5:
            # Poor performance, suggest larger adjustment
            direction = 1 if analysis.get("avg_error", 0) < 0 else -1
            adjustment = current_value * 0.05 * direction
            suggested_value = current_value + adjustment
            confidence = 0.55
        else:
            return None
        
        return CoefficientSuggestion(
            coefficient_name=coefficient_name,
            current_value=current_value,
            suggested_value=suggested_value,
            confidence=confidence,
            method=TuningMethod.BAYESIAN_OPTIMIZATION,
            reason=f"Bayesian exploration based on {good_outcome_rate:.1%} good outcomes",
            expected_error_reduction=0.1
        )
    
    async def _linear_regression_suggestion(
        self,
        formula_id: str,
        coefficient_name: str,
        current_value: float,
        db_session: AsyncSession
    ) -> Optional[CoefficientSuggestion]:
        """Generate suggestion using linear regression on error trend."""
        # Get feedback with errors over time
        query = select(FeedbackLoop).where(
            and_(
                FeedbackLoop.formula_id == formula_id,
                FeedbackLoop.prediction_error.isnot(None)
            )
        ).order_by(desc(FeedbackLoop.created_at)).limit(30)
        
        result = await db_session.execute(query)
        feedbacks = result.scalars().all()
        
        if len(feedbacks) < 10:
            return None
        
        # Simple linear regression on error trend
        n = len(feedbacks)
        sum_x = sum(range(n))
        sum_y = sum(f.prediction_error for f in feedbacks)
        sum_xy = sum(i * f.prediction_error for i, f in enumerate(feedbacks))
        sum_x2 = sum(i ** 2 for i in range(n))
        
        # Calculate slope
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return None
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # If error is trending away from zero, suggest adjustment
        if abs(slope) > 0.01:
            # Suggest adjustment proportional to trend
            adjustment = -slope * 10  # Scale factor
            suggested_value = current_value + adjustment
            
            confidence = min(0.75, 0.5 + abs(slope) * 5)
            
            return CoefficientSuggestion(
                coefficient_name=coefficient_name,
                current_value=current_value,
                suggested_value=suggested_value,
                confidence=confidence,
                method=TuningMethod.LINEAR_REGRESSION,
                reason=f"Linear regression trend: slope={slope:.4f}",
                expected_error_reduction=abs(slope) * 3
            )
        
        return None


# Singleton instance
_coefficient_tuner: Optional[CoefficientTuner] = None


def get_coefficient_tuner(learning_rate: float = 0.01) -> CoefficientTuner:
    """Get or create coefficient tuner singleton."""
    global _coefficient_tuner
    if _coefficient_tuner is None:
        _coefficient_tuner = CoefficientTuner(learning_rate=learning_rate)
    return _coefficient_tuner
