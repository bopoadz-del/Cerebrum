"""
Learning Engine - Main ML Learning System

Core learning engine that orchestrates:
- Feedback loop processing
- Model performance tracking
- Reinforcement learning for formula suggestions
- Integration with tier manager and coefficient tuner
"""

import uuid
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.credibility import CredibilityTier, get_credibility_system
from app.executor.models import FormulaExecutionLog
from app.learning.models import (
    LearningModel,
    ModelPerformance,
    FormulaPerformance,
    FeedbackLoop,
    FeedbackType,
    PerformanceOutcome,
    ReinforcementEpisode,
    SourceReputation,
)
from app.learning.tier_manager import TierManager, get_tier_manager, TierDecision
from app.learning.coefficient_tuner import CoefficientTuner, get_coefficient_tuner

logger = get_logger(__name__)


@dataclass
class LearningResult:
    """Result of a learning operation."""
    success: bool
    message: str
    data: Dict[str, Any]


@dataclass
class FormulaSuggestion:
    """Formula suggestion with confidence."""
    formula_id: str
    formula_type: str
    confidence: float
    reason: str
    inputs_needed: List[str]
    estimated_accuracy: float


class LearningEngine:
    """
    Main learning engine for the Cerebrum platform.
    
    Coordinates:
    - Processing execution results into feedback loops
    - Training and evaluating ML models
    - Reinforcement learning for formula suggestions
    - Source reputation tracking
    - Tier promotion/demotion
    - Coefficient auto-tuning
    """
    
    def __init__(
        self,
        tier_manager: Optional[TierManager] = None,
        coefficient_tuner: Optional[CoefficientTuner] = None
    ):
        self.tier_manager = tier_manager or get_tier_manager()
        self.coefficient_tuner = coefficient_tuner or get_coefficient_tuner()
        self._model_cache: Dict[str, LearningModel] = {}
    
    # ========================================================================
    # Feedback Loop Processing
    # ========================================================================
    
    async def process_execution_result(
        self,
        execution_log: FormulaExecutionLog,
        db_session: AsyncSession,
        actual_value: Optional[float] = None,
        user_rating: Optional[int] = None,
        feedback_type: FeedbackType = FeedbackType.AUTOMATED_CHECK
    ) -> Optional[FeedbackLoop]:
        """
        Process an execution result into the feedback loop.
        
        Args:
            execution_log: The formula execution log entry
            db_session: Database session
            actual_value: Real-world actual value (if available)
            user_rating: User rating 1-5 (if available)
            feedback_type: Type of feedback
            
        Returns:
            Created FeedbackLoop entry
        """
        try:
            # Calculate prediction error if actual value available
            predicted_value = self._extract_predicted_value(execution_log)
            prediction_error = None
            error_percentage = None
            
            if actual_value is not None and predicted_value is not None:
                prediction_error = predicted_value - actual_value
                if actual_value != 0:
                    error_percentage = abs(prediction_error / actual_value) * 100
            
            # Determine outcome
            outcome = self._determine_outcome(
                execution_log=execution_log,
                error_percentage=error_percentage,
                user_rating=user_rating
            )
            
            # Create feedback loop entry
            feedback = FeedbackLoop(
                execution_id=execution_log.execution_id,
                formula_id=execution_log.formula_id,
                formula_type=execution_log.formula_type,
                source_id=execution_log.user_id or "anonymous",
                user_id=execution_log.user_id,
                feedback_type=feedback_type,
                predicted_value=predicted_value or 0.0,
                actual_value=actual_value,
                prediction_error=prediction_error,
                error_percentage=error_percentage,
                feedback_data={
                    "user_rating": user_rating,
                    "execution_outputs": execution_log.outputs,
                    "credibility_factors": execution_log.credibility_factors,
                },
                outcome=outcome,
                processed=False,
            )
            
            # Calculate and store reward
            feedback.reward_signal = feedback.calculate_reward()
            
            db_session.add(feedback)
            await db_session.flush()
            
            logger.info(
                f"Feedback loop entry created: execution={execution_log.execution_id}, "
                f"outcome={outcome.value}, reward={feedback.reward_signal:.2f}"
            )
            
            return feedback
            
        except Exception as e:
            logger.error(f"Failed to process execution result: {e}", exc_info=True)
            return None
    
    async def process_pending_feedback(
        self,
        db_session: AsyncSession,
        batch_size: int = 100
    ) -> LearningResult:
        """
        Process pending feedback loop entries.
        
        Updates:
        - Formula performance metrics
        - Source reputation
        - Triggers coefficient tuning if needed
        
        Args:
            db_session: Database session
            batch_size: Maximum entries to process
            
        Returns:
            LearningResult with processing summary
        """
        # Get pending feedback
        query = select(FeedbackLoop).where(
            FeedbackLoop.processed == False
        ).order_by(FeedbackLoop.created_at).limit(batch_size)
        
        result = await db_session.execute(query)
        pending_feedback = result.scalars().all()
        
        if not pending_feedback:
            return LearningResult(
                success=True,
                message="No pending feedback to process",
                data={"processed": 0}
            )
        
        processed = 0
        formula_updates: Dict[str, Dict[str, Any]] = {}
        source_updates: Dict[str, Dict[str, Any]] = {}
        
        for feedback in pending_feedback:
            try:
                # Mark as processed
                feedback.process()
                
                # Track formula updates
                if feedback.formula_id not in formula_updates:
                    formula_updates[feedback.formula_id] = {
                        "total": 0,
                        "outcomes": {o: 0 for o in PerformanceOutcome},
                        "errors": [],
                        "source_ids": set(),
                    }
                
                formula_updates[feedback.formula_id]["total"] += 1
                formula_updates[feedback.formula_id]["outcomes"][feedback.outcome] += 1
                if feedback.prediction_error is not None:
                    formula_updates[feedback.formula_id]["errors"].append(feedback.prediction_error)
                formula_updates[feedback.formula_id]["source_ids"].add(feedback.source_id)
                
                # Track source updates
                if feedback.source_id not in source_updates:
                    source_updates[feedback.source_id] = {
                        "executions": 0,
                        "good_outcomes": 0,
                    }
                
                source_updates[feedback.source_id]["executions"] += 1
                if feedback.outcome in (PerformanceOutcome.EXCELLENT, PerformanceOutcome.GOOD):
                    source_updates[feedback.source_id]["good_outcomes"] += 1
                
                processed += 1
                
            except Exception as e:
                logger.warning(f"Failed to process feedback {feedback.id}: {e}")
                continue
        
        # Update formula performance records
        for formula_id, data in formula_updates.items():
            await self._update_formula_performance(formula_id, data, db_session)
        
        # Update source reputation
        for source_id, data in source_updates.items():
            await self._update_source_reputation(source_id, data, db_session)
        
        await db_session.flush()
        
        return LearningResult(
            success=True,
            message=f"Processed {processed} feedback entries",
            data={
                "processed": processed,
                "formulas_updated": len(formula_updates),
                "sources_updated": len(source_updates),
            }
        )
    
    # ========================================================================
    # Model Management
    # ========================================================================
    
    async def register_model(
        self,
        model_name: str,
        model_version: str,
        model_type: str,
        architecture: str,
        hyperparameters: Dict[str, Any],
        db_session: AsyncSession,
        description: Optional[str] = None,
    ) -> LearningModel:
        """
        Register a new ML model.
        
        Args:
            model_name: Model name
            model_version: Version string
            model_type: Type of model
            architecture: Model architecture
            hyperparameters: Training hyperparameters
            db_session: Database session
            description: Model description
            
        Returns:
            Created LearningModel
        """
        model = LearningModel(
            model_name=model_name,
            model_version=model_version,
            model_type=model_type,
            architecture=architecture,
            hyperparameters=hyperparameters,
            description=description,
            is_deployed=False,
        )
        
        db_session.add(model)
        await db_session.flush()
        
        self._model_cache[f"{model_name}:{model_version}"] = model
        
        logger.info(f"Registered model: {model_name} v{model_version}")
        
        return model
    
    async def record_model_performance(
        self,
        model_id: str,
        period_start: datetime,
        period_end: datetime,
        metrics: Dict[str, Any],
        db_session: AsyncSession,
    ) -> ModelPerformance:
        """
        Record performance metrics for a model.
        
        Args:
            model_id: Model ID
            period_start: Period start
            period_end: Period end
            metrics: Performance metrics
            db_session: Database session
            
        Returns:
            Created ModelPerformance record
        """
        from uuid import UUID
        
        perf = ModelPerformance(
            model_id=UUID(model_id),
            period_start=period_start,
            period_end=period_end,
            total_predictions=metrics.get("total_predictions", 0),
            correct_predictions=metrics.get("correct_predictions", 0),
            accuracy=metrics.get("accuracy", 0.0),
            avg_latency_ms=metrics.get("avg_latency_ms", 0.0),
            p95_latency_ms=metrics.get("p95_latency_ms", 0.0),
            p99_latency_ms=metrics.get("p99_latency_ms", 0.0),
            false_positives=metrics.get("false_positives", 0),
            false_negatives=metrics.get("false_negatives", 0),
            excellent_count=metrics.get("excellent_count", 0),
            good_count=metrics.get("good_count", 0),
            acceptable_count=metrics.get("acceptable_count", 0),
            poor_count=metrics.get("poor_count", 0),
            failed_count=metrics.get("failed_count", 0),
        )
        
        db_session.add(perf)
        await db_session.flush()
        
        return perf
    
    async def evaluate_model_for_deployment(
        self,
        model_id: str,
        db_session: AsyncSession,
    ) -> LearningResult:
        """
        Evaluate if a model should be deployed.
        
        Args:
            model_id: Model ID
            db_session: Database session
            
        Returns:
            LearningResult with deployment recommendation
        """
        from uuid import UUID
        
        query = select(LearningModel).where(LearningModel.id == UUID(model_id))
        result = await db_session.execute(query)
        model = result.scalar_one_or_none()
        
        if not model:
            return LearningResult(
                success=False,
                message=f"Model {model_id} not found",
                data={}
            )
        
        # Get recent performance
        perf_query = select(ModelPerformance).where(
            ModelPerformance.model_id == UUID(model_id)
        ).order_by(desc(ModelPerformance.period_end)).limit(3)
        
        perf_result = await db_session.execute(perf_query)
        performances = perf_result.scalars().all()
        
        if not performances:
            return LearningResult(
                success=False,
                message="No performance data available",
                data={"model_id": model_id}
            )
        
        # Calculate average accuracy
        avg_accuracy = sum(p.accuracy for p in performances) / len(performances)
        
        # Check deployment threshold
        should_deploy = avg_accuracy >= model.deployment_threshold
        
        return LearningResult(
            success=True,
            message=(
                f"Model {model.model_name} v{model.model_version} "
                f"{'meets' if should_deploy else 'below'} deployment threshold"
            ),
            data={
                "model_id": model_id,
                "average_accuracy": avg_accuracy,
                "deployment_threshold": model.deployment_threshold,
                "should_deploy": should_deploy,
                "current_deployed": model.is_deployed,
            }
        )
    
    async def deploy_model(
        self,
        model_id: str,
        db_session: AsyncSession,
    ) -> LearningResult:
        """
        Deploy a model to production.
        
        Args:
            model_id: Model ID
            db_session: Database session
            
        Returns:
            LearningResult with deployment status
        """
        from uuid import UUID
        
        query = select(LearningModel).where(LearningModel.id == UUID(model_id))
        result = await db_session.execute(query)
        model = result.scalar_one_or_none()
        
        if not model:
            return LearningResult(
                success=False,
                message=f"Model {model_id} not found",
                data={}
            )
        
        # Undeploy other models of same type
        if model.model_type:
            undeploy_query = select(LearningModel).where(
                and_(
                    LearningModel.model_type == model.model_type,
                    LearningModel.is_deployed == True,
                    LearningModel.id != UUID(model_id)
                )
            )
            
            undeploy_result = await db_session.execute(undeploy_query)
            other_models = undeploy_result.scalars().all()
            
            for other in other_models:
                other.is_deployed = False
                logger.info(f"Undeployed model: {other.model_name} v{other.model_version}")
        
        # Deploy this model
        model.is_deployed = True
        model.deployed_at = datetime.utcnow()
        
        await db_session.flush()
        
        logger.info(f"Deployed model: {model.model_name} v{model.model_version}")
        
        return LearningResult(
            success=True,
            message=f"Model {model.model_name} v{model.model_version} deployed",
            data={
                "model_id": model_id,
                "deployed_at": model.deployed_at.isoformat(),
            }
        )
    
    async def get_deployed_model(
        self,
        model_type: str,
        db_session: AsyncSession,
    ) -> Optional[LearningModel]:
        """
        Get the currently deployed model of a given type.
        
        Args:
            model_type: Type of model
            db_session: Database session
            
        Returns:
            Deployed LearningModel or None
        """
        query = select(LearningModel).where(
            and_(
                LearningModel.model_type == model_type,
                LearningModel.is_deployed == True
            )
        )
        
        result = await db_session.execute(query)
        return result.scalar_one_or_none()
    
    # ========================================================================
    # Reinforcement Learning - Formula Suggestion
    # ========================================================================
    
    async def start_episode(
        self,
        state: Dict[str, Any],
        model_id: Optional[str] = None,
        db_session: AsyncSession = None,
    ) -> ReinforcementEpisode:
        """
        Start a reinforcement learning episode.
        
        Args:
            state: Episode state (user query, context, constraints)
            model_id: Model to use (optional)
            db_session: Database session
            
        Returns:
            Created ReinforcementEpisode
        """
        episode = ReinforcementEpisode(
            episode_id=str(uuid.uuid4()),
            model_id=uuid.UUID(model_id) if model_id else None,
            state=state,
            suggested_formula_id="",  # To be filled when suggestion made
            suggested_formula_type="",
            confidence=0.0,
            alternatives=[],
            selected=False,
            executed=False,
        )
        
        if db_session:
            db_session.add(episode)
            await db_session.flush()
        
        return episode
    
    async def make_formula_suggestion(
        self,
        episode_id: str,
        context: Dict[str, Any],
        db_session: AsyncSession,
    ) -> Optional[FormulaSuggestion]:
        """
        Make a formula suggestion using reinforcement learning.
        
        Args:
            episode_id: Episode ID
            context: User context (query, project type, etc.)
            db_session: Database session
            
        Returns:
            FormulaSuggestion or None
        """
        # Get episode
        query = select(ReinforcementEpisode).where(
            ReinforcementEpisode.episode_id == episode_id
        )
        
        result = await db_session.execute(query)
        episode = result.scalar_one_or_none()
        
        if not episode:
            return None
        
        # Get deployed suggestion model
        model = await self.get_deployed_model("formula_suggester", db_session)
        
        # Simple rule-based suggestion (production would use actual ML model)
        suggestion = self._rule_based_suggestion(context)
        
        if suggestion:
            # Update episode
            episode.suggested_formula_id = suggestion.formula_id
            episode.suggested_formula_type = suggestion.formula_type
            episode.confidence = suggestion.confidence
            episode.model_id = model.id if model else None
            
            await db_session.flush()
        
        return suggestion
    
    async def record_episode_selection(
        self,
        episode_id: str,
        selected: bool,
        db_session: AsyncSession,
    ) -> bool:
        """
        Record user selection of a formula suggestion.
        
        Args:
            episode_id: Episode ID
            selected: Whether the suggestion was selected
            db_session: Database session
            
        Returns:
            True if recorded successfully
        """
        query = select(ReinforcementEpisode).where(
            ReinforcementEpisode.episode_id == episode_id
        )
        
        result = await db_session.execute(query)
        episode = result.scalar_one_or_none()
        
        if not episode:
            return False
        
        episode.selected = selected
        
        if selected:
            episode.immediate_reward = 0.3
        else:
            episode.immediate_reward = -0.1
        
        await db_session.flush()
        
        return True
    
    async def complete_episode(
        self,
        episode_id: str,
        execution_success: bool,
        user_rating: Optional[int],
        feedback_outcome: Optional[PerformanceOutcome],
        db_session: AsyncSession,
    ) -> LearningResult:
        """
        Complete an RL episode with outcome.
        
        Args:
            episode_id: Episode ID
            execution_success: Whether execution succeeded
            user_rating: User rating 1-5
            feedback_outcome: Final outcome from feedback loop
            db_session: Database session
            
        Returns:
            LearningResult with final reward
        """
        query = select(ReinforcementEpisode).where(
            ReinforcementEpisode.episode_id == episode_id
        )
        
        result = await db_session.execute(query)
        episode = result.scalar_one_or_none()
        
        if not episode:
            return LearningResult(
                success=False,
                message=f"Episode {episode_id} not found",
                data={}
            )
        
        # Complete the episode
        episode.complete(execution_success, user_rating)
        
        # Calculate final reward if feedback available
        if feedback_outcome:
            final_reward = episode.calculate_final_reward(feedback_outcome)
        else:
            final_reward = episode.immediate_reward
            episode.final_reward = final_reward
        
        episode.completed_at = datetime.utcnow()
        
        await db_session.flush()
        
        return LearningResult(
            success=True,
            message=f"Episode completed with reward {final_reward:.2f}",
            data={
                "episode_id": episode_id,
                "final_reward": final_reward,
                "immediate_reward": episode.immediate_reward,
                "delayed_reward": episode.delayed_reward,
                "execution_success": execution_success,
            }
        )
    
    async def get_episodes_for_training(
        self,
        db_session: AsyncSession,
        min_completed: int = 10,
        limit: int = 1000,
    ) -> List[ReinforcementEpisode]:
        """
        Get completed episodes ready for model training.
        
        Args:
            db_session: Database session
            min_completed: Minimum completions required
            limit: Maximum episodes to return
            
        Returns:
            List of episodes for training
        """
        # Check if enough completed episodes
        count_query = select(func.count()).where(
            and_(
                ReinforcementEpisode.completed_at.isnot(None),
                ReinforcementEpisode.processed_for_training == False
            )
        )
        
        count_result = await db_session.execute(count_query)
        completed_count = count_result.scalar()
        
        if completed_count < min_completed:
            return []
        
        # Get episodes
        query = select(ReinforcementEpisode).where(
            and_(
                ReinforcementEpisode.completed_at.isnot(None),
                ReinforcementEpisode.processed_for_training == False
            )
        ).limit(limit)
        
        result = await db_session.execute(query)
        episodes = result.scalars().all()
        
        return list(episodes)
    
    async def mark_episodes_trained(
        self,
        episode_ids: List[str],
        db_session: AsyncSession,
    ) -> int:
        """
        Mark episodes as processed for training.
        
        Args:
            episode_ids: List of episode IDs
            db_session: Database session
            
        Returns:
            Number of episodes marked
        """
        marked = 0
        for ep_id in episode_ids:
            query = select(ReinforcementEpisode).where(
                ReinforcementEpisode.episode_id == ep_id
            )
            result = await db_session.execute(query)
            episode = result.scalar_one_or_none()
            
            if episode:
                episode.processed_for_training = True
                episode.processed_at = datetime.utcnow()
                marked += 1
        
        await db_session.flush()
        return marked
    
    # ========================================================================
    # Learning Orchestration
    # ========================================================================
    
    async def run_learning_cycle(
        self,
        db_session: AsyncSession,
    ) -> LearningResult:
        """
        Run a complete learning cycle.
        
        1. Process pending feedback
        2. Evaluate sources for tier changes
        3. Apply auto-promotions
        4. Process coefficient tuning suggestions
        5. Train RL models if enough data
        
        Args:
            db_session: Database session
            
        Returns:
            LearningResult with cycle summary
        """
        results = {
            "feedback_processed": 0,
            "tier_evaluations": 0,
            "tier_promotions": 0,
            "coefficient_adjustments": 0,
            "rl_episodes_processed": 0,
        }
        
        try:
            # 1. Process pending feedback
            feedback_result = await self.process_pending_feedback(db_session)
            if feedback_result.success:
                results["feedback_processed"] = feedback_result.data.get("processed", 0)
            
            # 2. Evaluate sources for tier changes
            tier_decisions = await self.tier_manager.batch_evaluate(db_session)
            results["tier_evaluations"] = len(tier_decisions)
            
            # 3. Apply auto-promotions for high-confidence promotions
            promotions = await self.tier_manager.auto_promote_eligible(
                db_session, confidence_threshold=0.85
            )
            results["tier_promotions"] = len(promotions)
            
            # 4. Get pending coefficient adjustments
            pending_adjustments = await self.coefficient_tuner.get_pending_adjustments(
                db_session, min_confidence=0.75
            )
            results["coefficient_adjustments"] = len(pending_adjustments)
            
            # 5. Process RL episodes
            episodes = await self.get_episodes_for_training(db_session, min_completed=50)
            if episodes:
                episode_ids = [ep.episode_id for ep in episodes]
                # In production, this would trigger actual model training
                # For now, just mark them as processed
                processed = await self.mark_episodes_trained(episode_ids, db_session)
                results["rl_episodes_processed"] = processed
            
            await db_session.commit()
            
            return LearningResult(
                success=True,
                message="Learning cycle completed successfully",
                data=results
            )
            
        except Exception as e:
            logger.error(f"Learning cycle failed: {e}", exc_info=True)
            await db_session.rollback()
            
            return LearningResult(
                success=False,
                message=f"Learning cycle failed: {str(e)}",
                data=results
            )
    
    async def get_learning_stats(
        self,
        db_session: AsyncSession,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get comprehensive learning system statistics.
        
        Args:
            db_session: Database session
            days: Days of history to include
            
        Returns:
            Statistics dictionary
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Feedback loop stats
        feedback_query = select(func.count()).where(
            FeedbackLoop.created_at >= start_date
        )
        feedback_result = await db_session.execute(feedback_query)
        total_feedback = feedback_result.scalar()
        
        processed_feedback_query = select(func.count()).where(
            and_(
                FeedbackLoop.created_at >= start_date,
                FeedbackLoop.processed == True
            )
        )
        processed_result = await db_session.execute(processed_feedback_query)
        processed_feedback = processed_result.scalar()
        
        # Outcome distribution
        outcome_query = select(
            FeedbackLoop.outcome,
            func.count()
        ).where(
            FeedbackLoop.created_at >= start_date
        ).group_by(FeedbackLoop.outcome)
        
        outcome_result = await db_session.execute(outcome_query)
        outcomes = {row[0].value: row[1] for row in outcome_result.all()}
        
        # Tier statistics
        tier_stats = await self.tier_manager.get_tier_statistics(db_session)
        
        # Model statistics
        models_query = select(func.count()).where(LearningModel.is_deployed == True)
        models_result = await db_session.execute(models_query)
        deployed_models = models_result.scalar()
        
        # RL episodes
        episodes_query = select(func.count()).where(
            ReinforcementEpisode.completed_at >= start_date
        )
        episodes_result = await db_session.execute(episodes_query)
        completed_episodes = episodes_result.scalar()
        
        return {
            "period_days": days,
            "feedback": {
                "total": total_feedback,
                "processed": processed_feedback,
                "pending": total_feedback - processed_feedback,
                "outcomes": outcomes,
            },
            "tiers": tier_stats,
            "models": {
                "deployed": deployed_models,
            },
            "reinforcement_learning": {
                "completed_episodes": completed_episodes,
            },
        }
    
    # ========================================================================
    # Internal Helpers
    # ========================================================================
    
    def _extract_predicted_value(self, execution_log: FormulaExecutionLog) -> Optional[float]:
        """Extract predicted value from execution outputs."""
        try:
            outputs = execution_log.outputs
            if isinstance(outputs, dict):
                # Try common output keys
                for key in ["result", "value", "output", "prediction"]:
                    if key in outputs:
                        return float(outputs[key])
            return None
        except (ValueError, TypeError):
            return None
    
    def _determine_outcome(
        self,
        execution_log: FormulaExecutionLog,
        error_percentage: Optional[float],
        user_rating: Optional[int]
    ) -> PerformanceOutcome:
        """Determine performance outcome."""
        # Priority: user rating > error percentage > execution status
        
        if user_rating is not None:
            if user_rating >= 5:
                return PerformanceOutcome.EXCELLENT
            elif user_rating >= 4:
                return PerformanceOutcome.GOOD
            elif user_rating >= 3:
                return PerformanceOutcome.ACCEPTABLE
            elif user_rating >= 2:
                return PerformanceOutcome.POOR
            else:
                return PerformanceOutcome.FAILED
        
        if error_percentage is not None:
            if error_percentage < 5:
                return PerformanceOutcome.EXCELLENT
            elif error_percentage < 15:
                return PerformanceOutcome.GOOD
            elif error_percentage < 30:
                return PerformanceOutcome.ACCEPTABLE
            elif error_percentage < 50:
                return PerformanceOutcome.POOR
            else:
                return PerformanceOutcome.FAILED
        
        # Fallback to execution status
        if execution_log.status == "success":
            if execution_log.credibility_score > 0.8:
                return PerformanceOutcome.GOOD
            else:
                return PerformanceOutcome.ACCEPTABLE
        else:
            return PerformanceOutcome.FAILED
    
    async def _update_formula_performance(
        self,
        formula_id: str,
        data: Dict[str, Any],
        db_session: AsyncSession,
    ) -> None:
        """Update formula performance metrics."""
        # Get or create performance record
        query = select(FormulaPerformance).where(
            FormulaPerformance.formula_id == formula_id
        )
        
        result = await db_session.execute(query)
        perf = result.scalar_one_or_none()
        
        if not perf:
            # Need source_id and formula_type - get from first execution
            exec_query = select(FormulaExecutionLog).where(
                FormulaExecutionLog.formula_id == formula_id
            ).limit(1)
            
            exec_result = await db_session.execute(exec_query)
            exec_log = exec_result.scalar_one_or_none()
            
            if not exec_log:
                return
            
            perf = FormulaPerformance(
                formula_id=formula_id,
                formula_type=exec_log.formula_type,
                source_id=str(exec_log.user_id) if exec_log.user_id else "unknown",
                current_tier=5,  # Unknown tier
            )
            db_session.add(perf)
        
        # Update metrics
        perf.total_executions += data["total"]
        
        # Update outcome distribution
        for outcome, count in data["outcomes"].items():
            perf.outcome_distribution[outcome.value] += count
        
        # Calculate good outcomes
        good_count = (
            perf.outcome_distribution[PerformanceOutcome.EXCELLENT.value] +
            perf.outcome_distribution[PerformanceOutcome.GOOD.value]
        )
        perf.successful_executions = int(perf.total_executions * (good_count / max(1, perf.total_executions)))
        
        # Update error metrics
        if data["errors"]:
            avg_error = sum(abs(e) for e in data["errors"]) / len(data["errors"])
            # Convert error to approximate credibility
            perf.avg_credibility_score = max(0, 1.0 - (avg_error / 100))
        
        # Update performance score
        perf.update_performance_score()
    
    async def _update_source_reputation(
        self,
        source_id: str,
        data: Dict[str, Any],
        db_session: AsyncSession,
    ) -> None:
        """Update source reputation metrics."""
        # Get or create reputation record
        query = select(SourceReputation).where(
            SourceReputation.source_id == source_id
        )
        
        result = await db_session.execute(query)
        rep = result.scalar_one_or_none()
        
        if not rep:
            rep = SourceReputation(
                source_id=source_id,
                source_name=source_id,  # Will be updated with real name
                source_type="unknown",
                current_tier=5,
            )
            db_session.add(rep)
        
        # Update metrics
        rep.total_executions += data["executions"]
        
        # Recalculate reputation
        rep.calculate_reputation()
    
    def _rule_based_suggestion(self, context: Dict[str, Any]) -> Optional[FormulaSuggestion]:
        """Generate rule-based formula suggestion."""
        query = context.get("query", "").lower()
        
        # Simple keyword matching (production would use trained model)
        keyword_mapping = {
            "concrete": ("concrete_volume", "concrete", 0.85),
            "cement": ("concrete_volume", "concrete", 0.85),
            "slab": ("concrete_volume", "concrete", 0.80),
            "rebar": ("rebar_weight", "rebar", 0.85),
            "steel": ("rebar_weight", "rebar", 0.80),
            "cost": ("concrete_cost", "cost", 0.75),
            "price": ("concrete_cost", "cost", 0.75),
            "brick": ("brick_quantity", "masonry", 0.80),
            "mortar": ("mortar_volume", "masonry", 0.75),
            "excavation": ("excavation_volume", "earthwork", 0.80),
            "fill": ("fill_volume", "earthwork", 0.75),
        }
        
        for keyword, (formula_id, formula_type, confidence) in keyword_mapping.items():
            if keyword in query:
                return FormulaSuggestion(
                    formula_id=formula_id,
                    formula_type=formula_type,
                    confidence=confidence,
                    reason=f"Keyword match: '{keyword}'",
                    inputs_needed=["length", "width", "depth"],
                    estimated_accuracy=0.8,
                )
        
        return None


# Singleton instance
_learning_engine: Optional[LearningEngine] = None


def get_learning_engine(
    tier_manager: Optional[TierManager] = None,
    coefficient_tuner: Optional[CoefficientTuner] = None,
) -> LearningEngine:
    """Get or create learning engine singleton."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine(
            tier_manager=tier_manager,
            coefficient_tuner=coefficient_tuner,
        )
    return _learning_engine
