"""
Learning Engine API Endpoints

REST API for:
- Learning cycle management
- Tier management (promotion/demotion)
- Coefficient tuning
- Model management
- Feedback loop inspection
- Reinforcement learning episodes
- Learning statistics
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.core.security import require_role, require_permission
from app.api.deps import get_current_user
from app.models.user import User
from app.core.logging import get_logger
from app.core.credibility import CredibilityTier

from app.learning.engine import LearningEngine, get_learning_engine, LearningResult
from app.learning.tier_manager import TierManager, get_tier_manager, TierDecision
from app.learning.coefficient_tuner import (
    CoefficientTuner,
    get_coefficient_tuner,
    CoefficientSuggestion,
    TuningMethod,
)
from app.learning.models import (
    LearningModel,
    FormulaPerformance,
    TierHistory,
    CoefficientAdjustment,
    FeedbackLoop,
    ReinforcementEpisode,
    SourceReputation,
    FeedbackType,
    PerformanceOutcome,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/learning", tags=["Learning Engine"])


# Create optional version of get_current_user
async def get_current_user_optional(
    token: Optional[str] = None
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    try:
        return await get_current_user()
    except Exception:
        return None


# =============================================================================
# Request/Response Schemas
# =============================================================================

class FeedbackCreateRequest(BaseModel):
    """Create feedback from execution result."""
    execution_id: str = Field(..., description="Formula execution ID")
    actual_value: Optional[float] = Field(None, description="Real-world actual value")
    user_rating: Optional[int] = Field(None, ge=1, le=5, description="User rating 1-5")
    feedback_type: FeedbackType = Field(default=FeedbackType.USER_RATING)
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback loop entry response."""
    id: str
    execution_id: str
    formula_id: str
    formula_type: str
    feedback_type: str
    outcome: str
    reward_signal: float
    processed: bool
    created_at: str


class ProcessFeedbackResponse(BaseModel):
    """Response from processing pending feedback."""
    success: bool
    message: str
    processed: int
    formulas_updated: int
    sources_updated: int


class TierDecisionResponse(BaseModel):
    """Tier change decision response."""
    source_id: str
    current_tier: int
    proposed_tier: int
    change_type: str
    confidence: float
    reason: str
    should_change: bool


class TierChangeRequest(BaseModel):
    """Request for manual tier change."""
    new_tier: int = Field(..., ge=1, le=5, description="New tier level (1-5)")
    reason: str = Field(..., min_length=10, max_length=1000)


class TierHistoryResponse(BaseModel):
    """Tier change history response."""
    id: str
    source_id: str
    source_name: Optional[str]
    previous_tier: int
    new_tier: int
    change_type: str
    change_reason: str
    triggered_by: str
    created_at: str


class SourceReputationResponse(BaseModel):
    """Source reputation response."""
    id: str
    source_id: str
    source_name: str
    source_type: str
    current_tier: int
    reputation_score: float
    formulas_submitted: int
    formulas_accepted: int
    acceptance_rate: float
    total_executions: int
    tier_since: str
    under_review: bool


class CoefficientAnalysisResponse(BaseModel):
    """Coefficient performance analysis."""
    formula_id: str
    coefficient_name: str
    sufficient_data: bool
    sample_count: int
    avg_error: Optional[float]
    rmse: Optional[float]
    error_trend: Optional[str]
    good_outcome_rate: Optional[float]


class CoefficientAdjustmentRequest(BaseModel):
    """Request coefficient adjustment."""
    coefficient_name: str
    current_value: float
    method: TuningMethod = TuningMethod.GRADIENT_DESCENT


class CoefficientAdjustmentResponse(BaseModel):
    """Coefficient adjustment response."""
    id: str
    formula_id: str
    coefficient_name: str
    previous_value: float
    new_value: float
    adjustment_method: str
    confidence: float
    validated: bool
    created_at: str


class ModelRegisterRequest(BaseModel):
    """Register a new ML model."""
    model_name: str = Field(..., min_length=1, max_length=100)
    model_version: str = Field(..., min_length=1, max_length=50)
    model_type: str = Field(..., min_length=1, max_length=50)
    architecture: str = Field(..., min_length=1, max_length=100)
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class ModelResponse(BaseModel):
    """ML model response."""
    id: str
    model_name: str
    model_version: str
    model_type: str
    architecture: str
    training_data_size: int
    accuracy: Optional[float]
    is_deployed: bool
    deployed_at: Optional[str]
    created_at: str


class EpisodeStartRequest(BaseModel):
    """Start RL episode request."""
    state: Dict[str, Any] = Field(..., description="Episode state/context")
    model_id: Optional[str] = None


class EpisodeStartResponse(BaseModel):
    """Episode start response."""
    episode_id: str
    model_id: Optional[str]
    created_at: str


class FormulaSuggestionResponse(BaseModel):
    """Formula suggestion from RL."""
    episode_id: str
    formula_id: str
    formula_type: str
    confidence: float
    reason: str
    inputs_needed: List[str]
    estimated_accuracy: float


class EpisodeCompleteRequest(BaseModel):
    """Complete episode request."""
    execution_success: bool
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_outcome: Optional[PerformanceOutcome] = None


class EpisodeCompleteResponse(BaseModel):
    """Episode complete response."""
    episode_id: str
    final_reward: float
    immediate_reward: float
    completed: bool


class LearningCycleResponse(BaseModel):
    """Learning cycle execution response."""
    success: bool
    message: str
    feedback_processed: int
    tier_evaluations: int
    tier_promotions: int
    coefficient_adjustments: int
    rl_episodes_processed: int


class LearningStatsResponse(BaseModel):
    """Learning system statistics."""
    period_days: int
    feedback: Dict[str, Any]
    tiers: Dict[str, Any]
    models: Dict[str, Any]
    reinforcement_learning: Dict[str, Any]


# =============================================================================
# Dependencies
# =============================================================================

async def get_learning_engine_dep(
    db: AsyncSession = Depends(get_db_session)
) -> LearningEngine:
    """Get learning engine with dependencies."""
    return get_learning_engine()


async def get_tier_manager_dep() -> TierManager:
    """Get tier manager singleton."""
    return get_tier_manager()


async def get_coefficient_tuner_dep() -> CoefficientTuner:
    """Get coefficient tuner singleton."""
    return get_coefficient_tuner()


# =============================================================================
# Feedback Loop Endpoints
# =============================================================================

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Create feedback from execution",
    description="Submit feedback for a formula execution result.",
)
async def create_feedback(
    request: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user_optional),
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    """
    Create a feedback loop entry from an execution result.
    
    This connects execution results with real-world outcomes
    to improve future predictions.
    """
    # Get execution log
    from app.executor.models import FormulaExecutionLog
    
    query = select(FormulaExecutionLog).where(
        FormulaExecutionLog.execution_id == request.execution_id
    )
    
    result = await db.execute(query)
    execution_log = result.scalar_one_or_none()
    
    if not execution_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {request.execution_id} not found"
        )
    
    # Process feedback
    feedback = await engine.process_execution_result(
        execution_log=execution_log,
        db_session=db,
        actual_value=request.actual_value,
        user_rating=request.user_rating,
        feedback_type=request.feedback_type,
    )
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create feedback entry"
        )
    
    await db.commit()
    
    return FeedbackResponse(
        id=str(feedback.id),
        execution_id=feedback.execution_id,
        formula_id=feedback.formula_id,
        formula_type=feedback.formula_type,
        feedback_type=feedback.feedback_type.value,
        outcome=feedback.outcome.value,
        reward_signal=feedback.reward_signal,
        processed=feedback.processed,
        created_at=feedback.created_at.isoformat() if feedback.created_at else "",
    )


@router.post(
    "/feedback/process",
    response_model=ProcessFeedbackResponse,
    summary="Process pending feedback",
    description="Process all pending feedback loop entries.",
)
async def process_pending_feedback(
    batch_size: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> ProcessFeedbackResponse:
    """
    Process pending feedback loop entries.
    
    Updates formula performance, source reputation, and triggers
    coefficient tuning if needed.
    """
    result = await engine.process_pending_feedback(db, batch_size=batch_size)
    await db.commit()
    
    return ProcessFeedbackResponse(
        success=result.success,
        message=result.message,
        processed=result.data.get("processed", 0),
        formulas_updated=result.data.get("formulas_updated", 0),
        sources_updated=result.data.get("sources_updated", 0),
    )


@router.get(
    "/feedback",
    response_model=List[FeedbackResponse],
    summary="Get feedback entries",
    description="Get feedback loop entries with optional filters.",
)
async def get_feedback_entries(
    formula_id: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    processed: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[FeedbackResponse]:
    """Get feedback loop entries with optional filters."""
    query = select(FeedbackLoop)
    
    if formula_id:
        query = query.where(FeedbackLoop.formula_id == formula_id)
    if source_id:
        query = query.where(FeedbackLoop.source_id == source_id)
    if processed is not None:
        query = query.where(FeedbackLoop.processed == processed)
    
    query = query.order_by(FeedbackLoop.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return [
        FeedbackResponse(
            id=str(entry.id),
            execution_id=entry.execution_id,
            formula_id=entry.formula_id,
            formula_type=entry.formula_type,
            feedback_type=entry.feedback_type.value,
            outcome=entry.outcome.value,
            reward_signal=entry.reward_signal,
            processed=entry.processed,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
        )
        for entry in entries
    ]


# =============================================================================
# Tier Management Endpoints
# =============================================================================

@router.get(
    "/tiers/sources",
    response_model=List[SourceReputationResponse],
    summary="Get sources by tier",
    description="Get all sources in a specific credibility tier.",
)
async def get_sources_by_tier(
    tier: int = Query(..., ge=1, le=5, description="Tier level (1-5)"),
    include_under_review: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    tier_manager: TierManager = Depends(get_tier_manager_dep),
    db: AsyncSession = Depends(get_db_session),
) -> List[SourceReputationResponse]:
    """Get all sources in a specific credibility tier."""
    sources = await tier_manager.get_sources_by_tier(
        CredibilityTier(tier),
        db,
        include_under_review=include_under_review,
        limit=limit
    )
    
    return [
        SourceReputationResponse(
            id=str(source.id),
            source_id=source.source_id,
            source_name=source.source_name,
            source_type=source.source_type,
            current_tier=source.current_tier,
            reputation_score=source.reputation_score,
            formulas_submitted=source.formulas_submitted,
            formulas_accepted=source.formulas_accepted,
            acceptance_rate=source.acceptance_rate,
            total_executions=source.total_executions,
            tier_since=source.tier_since.isoformat() if source.tier_since else "",
            under_review=source.under_review,
        )
        for source in sources
    ]


@router.get(
    "/tiers/sources/{source_id}/evaluate",
    response_model=TierDecisionResponse,
    summary="Evaluate source for tier change",
    description="Evaluate if a source should be promoted or demoted.",
)
async def evaluate_source_tier(
    source_id: str,
    force: bool = Query(False, description="Force evaluation even if criteria not met"),
    tier_manager: TierManager = Depends(get_tier_manager_dep),
    db: AsyncSession = Depends(get_db_session),
) -> TierDecisionResponse:
    """Evaluate a source for potential tier change."""
    decision = await tier_manager.evaluate_source(source_id, db, force=force)
    
    return TierDecisionResponse(
        source_id=decision.source_id,
        current_tier=decision.current_tier,
        proposed_tier=decision.proposed_tier,
        change_type=decision.change_type.value,
        confidence=decision.confidence,
        reason=decision.reason,
        should_change=decision.should_change,
    )


@router.post(
    "/tiers/sources/{source_id}/change",
    response_model=TierHistoryResponse,
    summary="Manual tier change",
    description="Manually change a source's credibility tier (admin only).",
)
async def manual_tier_change(
    source_id: str,
    request: TierChangeRequest,
    current_user: User = Depends(require_role("admin")),
    tier_manager: TierManager = Depends(get_tier_manager_dep),
    db: AsyncSession = Depends(get_db_session),
) -> TierHistoryResponse:
    """
    Manually change a source's credibility tier.
    
    Requires admin privileges. Creates an audit trail entry.
    """
    history = await tier_manager.manual_tier_change(
        source_id=source_id,
        new_tier=request.new_tier,
        reason=request.reason,
        admin_id=str(current_user.id),
        db_session=db
    )
    
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source {source_id} not found"
        )
    
    await db.commit()
    
    return TierHistoryResponse(
        id=str(history.id),
        source_id=history.source_id,
        source_name=history.source_name,
        previous_tier=history.previous_tier,
        new_tier=history.new_tier,
        change_type=history.change_type.value,
        change_reason=history.change_reason,
        triggered_by=history.triggered_by,
        created_at=history.created_at.isoformat() if history.created_at else "",
    )


@router.get(
    "/tiers/sources/{source_id}/history",
    response_model=List[TierHistoryResponse],
    summary="Get tier change history",
    description="Get tier change history for a source.",
)
async def get_tier_history(
    source_id: str,
    limit: int = Query(50, ge=1, le=100),
    tier_manager: TierManager = Depends(get_tier_manager_dep),
    db: AsyncSession = Depends(get_db_session),
) -> List[TierHistoryResponse]:
    """Get tier change history for a source."""
    history = await tier_manager.get_tier_history(source_id, db, limit=limit)
    
    return [
        TierHistoryResponse(
            id=str(entry.id),
            source_id=entry.source_id,
            source_name=entry.source_name,
            previous_tier=entry.previous_tier,
            new_tier=entry.new_tier,
            change_type=entry.change_type.value,
            change_reason=entry.change_reason,
            triggered_by=entry.triggered_by,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
        )
        for entry in history
    ]


@router.get(
    "/tiers/statistics",
    response_model=Dict[str, Any],
    summary="Get tier statistics",
    description="Get statistics about tier distribution and changes.",
)
async def get_tier_statistics(
    tier_manager: TierManager = Depends(get_tier_manager_dep),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get tier statistics across the system."""
    return await tier_manager.get_tier_statistics(db)


# =============================================================================
# Coefficient Tuning Endpoints
# =============================================================================

@router.get(
    "/coefficients/{formula_id}/{coefficient_name}/analyze",
    response_model=CoefficientAnalysisResponse,
    summary="Analyze coefficient performance",
    description="Get performance analysis for a specific coefficient.",
)
async def analyze_coefficient(
    formula_id: str,
    coefficient_name: str,
    lookback_days: int = Query(30, ge=7, le=365),
    tuner: CoefficientTuner = Depends(get_coefficient_tuner_dep),
    db: AsyncSession = Depends(get_db_session),
) -> CoefficientAnalysisResponse:
    """Analyze performance of a specific coefficient."""
    analysis = await tuner.analyze_coefficient_performance(
        formula_id, coefficient_name, db, lookback_days
    )
    
    return CoefficientAnalysisResponse(
        formula_id=analysis["formula_id"],
        coefficient_name=analysis["coefficient_name"],
        sufficient_data=analysis["sufficient_data"],
        sample_count=analysis["sample_count"],
        avg_error=analysis.get("avg_error"),
        rmse=analysis.get("rmse"),
        error_trend=analysis.get("error_trend_direction"),
        good_outcome_rate=analysis.get("good_outcome_rate"),
    )


@router.post(
    "/coefficients/{formula_id}/suggest",
    response_model=Dict[str, Any],
    summary="Suggest coefficient adjustment",
    description="Get AI-suggested coefficient adjustment.",
)
async def suggest_coefficient(
    formula_id: str,
    request: CoefficientAdjustmentRequest,
    tuner: CoefficientTuner = Depends(get_coefficient_tuner_dep),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get AI-suggested coefficient adjustment."""
    suggestion = await tuner.suggest_coefficient_adjustment(
        formula_id,
        request.coefficient_name,
        request.current_value,
        db,
        request.method
    )
    
    if not suggestion:
        return {
            "has_suggestion": False,
            "reason": "Insufficient data or no improvement possible"
        }
    
    return {
        "has_suggestion": True,
        "coefficient_name": suggestion.coefficient_name,
        "current_value": suggestion.current_value,
        "suggested_value": suggestion.suggested_value,
        "confidence": suggestion.confidence,
        "method": suggestion.method.value,
        "reason": suggestion.reason,
        "expected_error_reduction": suggestion.expected_error_reduction,
    }


@router.post(
    "/coefficients/{formula_id}/apply",
    response_model=CoefficientAdjustmentResponse,
    summary="Apply coefficient adjustment",
    description="Apply a coefficient adjustment (auto-validate if confidence high).",
)
async def apply_coefficient_adjustment(
    formula_id: str,
    formula_type: str = Query(..., description="Formula type (concrete, rebar, etc.)"),
    request: Dict[str, Any] = {},
    tuner: CoefficientTuner = Depends(get_coefficient_tuner_dep),
    db: AsyncSession = Depends(get_db_session),
) -> CoefficientAdjustmentResponse:
    """Apply a coefficient adjustment."""
    from app.learning.coefficient_tuner import CoefficientSuggestion, TuningMethod
    
    suggestion = CoefficientSuggestion(
        coefficient_name=request.get("coefficient_name", ""),
        current_value=request.get("current_value", 0.0),
        suggested_value=request.get("suggested_value", 0.0),
        confidence=request.get("confidence", 0.0),
        method=TuningMethod(request.get("method", "gradient_descent")),
        reason=request.get("reason", ""),
        expected_error_reduction=request.get("expected_error_reduction", 0.0),
    )
    
    result = await tuner.apply_coefficient_adjustment(
        suggestion, formula_id, formula_type, db,
        auto_validate=request.get("auto_validate", False)
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to apply adjustment"
        )
    
    await db.commit()
    
    # Get the created adjustment
    from uuid import UUID
    adj_query = select(CoefficientAdjustment).where(
        CoefficientAdjustment.id == UUID(result.adjustment_id)
    )
    adj_result = await db.execute(adj_query)
    adjustment = adj_result.scalar_one()
    
    return CoefficientAdjustmentResponse(
        id=str(adjustment.id),
        formula_id=adjustment.formula_id,
        coefficient_name=adjustment.coefficient_name,
        previous_value=adjustment.previous_value,
        new_value=adjustment.new_value,
        adjustment_method=adjustment.adjustment_method,
        confidence=adjustment.confidence,
        validated=adjustment.validated,
        created_at=adjustment.created_at.isoformat() if adjustment.created_at else "",
    )


@router.get(
    "/coefficients/pending",
    response_model=List[CoefficientAdjustmentResponse],
    summary="Get pending adjustments",
    description="Get pending (unvalidated) coefficient adjustments.",
)
async def get_pending_adjustments(
    formula_id: Optional[str] = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
    tuner: CoefficientTuner = Depends(get_coefficient_tuner_dep),
    db: AsyncSession = Depends(get_db_session),
) -> List[CoefficientAdjustmentResponse]:
    """Get pending coefficient adjustments."""
    adjustments = await tuner.get_pending_adjustments(db, formula_id, min_confidence, limit)
    
    return [
        CoefficientAdjustmentResponse(
            id=str(adj.id),
            formula_id=adj.formula_id,
            coefficient_name=adj.coefficient_name,
            previous_value=adj.previous_value,
            new_value=adj.new_value,
            adjustment_method=adj.adjustment_method,
            confidence=adj.confidence,
            validated=adj.validated,
            created_at=adj.created_at.isoformat() if adj.created_at else "",
        )
        for adj in adjustments
    ]


@router.post(
    "/coefficients/{adjustment_id}/validate",
    response_model=Dict[str, bool],
    summary="Validate adjustment",
    description="Approve/validate a coefficient adjustment.",
)
async def validate_adjustment(
    adjustment_id: str,
    current_user: User = Depends(get_current_user),
    tuner: CoefficientTuner = Depends(get_coefficient_tuner_dep),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, bool]:
    """Validate (approve) a coefficient adjustment."""
    success = await tuner.validate_adjustment(
        adjustment_id, str(current_user.id), db
    )
    
    if success:
        await db.commit()
    
    return {"success": success}


@router.post(
    "/coefficients/{adjustment_id}/rollback",
    response_model=Dict[str, bool],
    summary="Rollback adjustment",
    description="Rollback a coefficient adjustment.",
)
async def rollback_adjustment(
    adjustment_id: str,
    reason: str = Query(..., min_length=5, description="Reason for rollback"),
    current_user: User = Depends(get_current_user),
    tuner: CoefficientTuner = Depends(get_coefficient_tuner_dep),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, bool]:
    """Rollback a coefficient adjustment."""
    success = await tuner.rollback_adjustment(adjustment_id, reason, db)
    
    if success:
        await db.commit()
    
    return {"success": success}


# =============================================================================
# Model Management Endpoints
# =============================================================================

@router.post(
    "/models",
    response_model=ModelResponse,
    summary="Register model",
    description="Register a new ML model.",
)
async def register_model(
    request: ModelRegisterRequest,
    current_user: User = Depends(get_current_user),
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> ModelResponse:
    """Register a new ML model."""
    model = await engine.register_model(
        model_name=request.model_name,
        model_version=request.model_version,
        model_type=request.model_type,
        architecture=request.architecture,
        hyperparameters=request.hyperparameters,
        db_session=db,
        description=request.description,
    )
    
    await db.commit()
    
    return ModelResponse(
        id=str(model.id),
        model_name=model.model_name,
        model_version=model.model_version,
        model_type=model.model_type,
        architecture=model.architecture,
        training_data_size=model.training_data_size,
        accuracy=model.accuracy,
        is_deployed=model.is_deployed,
        deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
        created_at=model.created_at.isoformat() if model.created_at else "",
    )


@router.get(
    "/models",
    response_model=List[ModelResponse],
    summary="List models",
    description="List all ML models.",
)
async def list_models(
    model_type: Optional[str] = Query(None),
    deployed_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[ModelResponse]:
    """List ML models."""
    query = select(LearningModel)
    
    if model_type:
        query = query.where(LearningModel.model_type == model_type)
    if deployed_only:
        query = query.where(LearningModel.is_deployed == True)
    
    query = query.order_by(LearningModel.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    models = result.scalars().all()
    
    return [
        ModelResponse(
            id=str(model.id),
            model_name=model.model_name,
            model_version=model.model_version,
            model_type=model.model_type,
            architecture=model.architecture,
            training_data_size=model.training_data_size,
            accuracy=model.accuracy,
            is_deployed=model.is_deployed,
            deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
            created_at=model.created_at.isoformat() if model.created_at else "",
        )
        for model in models
    ]


@router.post(
    "/models/{model_id}/deploy",
    response_model=Dict[str, Any],
    summary="Deploy model",
    description="Deploy a model to production.",
)
async def deploy_model(
    model_id: str,
    current_user: User = Depends(require_role("admin")),
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Deploy a model to production."""
    result = await engine.deploy_model(model_id, db)
    await db.commit()
    
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data,
    }


# =============================================================================
# Reinforcement Learning Endpoints
# =============================================================================

@router.post(
    "/rl/episodes",
    response_model=EpisodeStartResponse,
    summary="Start RL episode",
    description="Start a new reinforcement learning episode.",
)
async def start_episode(
    request: EpisodeStartRequest,
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> EpisodeStartResponse:
    """Start a new reinforcement learning episode."""
    from uuid import UUID
    
    episode = await engine.start_episode(
        state=request.state,
        model_id=request.model_id,
        db_session=db,
    )
    
    await db.commit()
    
    return EpisodeStartResponse(
        episode_id=episode.episode_id,
        model_id=str(episode.model_id) if episode.model_id else None,
        created_at=episode.created_at.isoformat() if episode.created_at else "",
    )


@router.post(
    "/rl/episodes/{episode_id}/suggest",
    response_model=FormulaSuggestionResponse,
    summary="Get formula suggestion",
    description="Get a formula suggestion from the RL system.",
)
async def get_formula_suggestion(
    episode_id: str,
    context: Dict[str, Any],
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> FormulaSuggestionResponse:
    """Get a formula suggestion using reinforcement learning."""
    suggestion = await engine.make_formula_suggestion(episode_id, context, db)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not generate formula suggestion"
        )
    
    return FormulaSuggestionResponse(
        episode_id=episode_id,
        formula_id=suggestion.formula_id,
        formula_type=suggestion.formula_type,
        confidence=suggestion.confidence,
        reason=suggestion.reason,
        inputs_needed=suggestion.inputs_needed,
        estimated_accuracy=suggestion.estimated_accuracy,
    )


@router.post(
    "/rl/episodes/{episode_id}/select",
    response_model=Dict[str, bool],
    summary="Record selection",
    description="Record user selection of a formula suggestion.",
)
async def record_episode_selection(
    episode_id: str,
    selected: bool = Query(..., description="Whether the suggestion was selected"),
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, bool]:
    """Record user selection of a formula suggestion."""
    success = await engine.record_episode_selection(episode_id, selected, db)
    
    if success:
        await db.commit()
    
    return {"success": success}


@router.post(
    "/rl/episodes/{episode_id}/complete",
    response_model=EpisodeCompleteResponse,
    summary="Complete episode",
    description="Complete an RL episode with outcome.",
)
async def complete_episode(
    episode_id: str,
    request: EpisodeCompleteRequest,
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> EpisodeCompleteResponse:
    """Complete a reinforcement learning episode."""
    result = await engine.complete_episode(
        episode_id=episode_id,
        execution_success=request.execution_success,
        user_rating=request.user_rating,
        feedback_outcome=request.feedback_outcome,
        db_session=db,
    )
    
    await db.commit()
    
    return EpisodeCompleteResponse(
        episode_id=episode_id,
        final_reward=result.data.get("final_reward", 0.0),
        immediate_reward=result.data.get("immediate_reward", 0.0),
        completed=result.success,
    )


# =============================================================================
# Learning Cycle & Statistics
# =============================================================================

@router.post(
    "/cycle",
    response_model=LearningCycleResponse,
    summary="Run learning cycle",
    description="Run a complete learning cycle (feedback, tiers, coefficients, RL).",
)
async def run_learning_cycle(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("admin")),
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> LearningCycleResponse:
    """
    Run a complete learning cycle.
    
    This processes feedback, evaluates sources for tier changes,
    applies coefficient tuning, and trains RL models.
    """
    result = await engine.run_learning_cycle(db)
    
    await db.commit()
    
    return LearningCycleResponse(
        success=result.success,
        message=result.message,
        feedback_processed=result.data.get("feedback_processed", 0),
        tier_evaluations=result.data.get("tier_evaluations", 0),
        tier_promotions=result.data.get("tier_promotions", 0),
        coefficient_adjustments=result.data.get("coefficient_adjustments", 0),
        rl_episodes_processed=result.data.get("rl_episodes_processed", 0),
    )


@router.get(
    "/statistics",
    response_model=LearningStatsResponse,
    summary="Get learning statistics",
    description="Get comprehensive learning system statistics.",
)
async def get_learning_statistics(
    days: int = Query(30, ge=1, le=365),
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> LearningStatsResponse:
    """Get comprehensive learning system statistics."""
    stats = await engine.get_learning_stats(db, days)
    
    return LearningStatsResponse(
        period_days=stats["period_days"],
        feedback=stats["feedback"],
        tiers=stats["tiers"],
        models=stats["models"],
        reinforcement_learning=stats["reinforcement_learning"],
    )


@router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Learning system health",
    description="Get health status of the learning system.",
)
async def get_learning_health(
    engine: LearningEngine = Depends(get_learning_engine_dep),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get health status of the learning system."""
    # Check pending feedback
    pending_feedback_query = select(FeedbackLoop).where(FeedbackLoop.processed == False)
    pending_result = await db.execute(pending_feedback_query)
    pending_count = len(pending_result.scalars().all())
    
    # Check pending coefficient adjustments
    pending_adj_query = select(CoefficientAdjustment).where(
        CoefficientAdjustment.validated == False,
        CoefficientAdjustment.rolled_back == False
    )
    pending_adj_result = await db.execute(pending_adj_query)
    pending_adj_count = len(pending_adj_result.scalars().all())
    
    # Check deployed models
    deployed_models_query = select(LearningModel).where(LearningModel.is_deployed == True)
    deployed_result = await db.execute(deployed_models_query)
    deployed_count = len(deployed_result.scalars().all())
    
    # Check sources under review
    under_review_query = select(SourceReputation).where(SourceReputation.under_review == True)
    under_review_result = await db.execute(under_review_query)
    under_review_count = len(under_review_result.scalars().all())
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "pending_feedback": pending_count,
        "pending_coefficient_adjustments": pending_adj_count,
        "deployed_models": deployed_count,
        "sources_under_review": under_review_count,
        "needs_attention": pending_count > 100 or under_review_count > 10,
    }
