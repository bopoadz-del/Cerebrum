"""
Prompt Registry API Endpoints

FastAPI endpoints for managing versioned prompts and A/B testing.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.prompts.ab_testing import ABTestConfig, get_ab_testing_framework
from app.prompts.dynamic_loading import get_prompt_loader
from app.prompts.models import (
    ModelProvider,
    PromptCreate,
    PromptDB,
    PromptResponse,
    PromptStatus,
    PromptUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompts", tags=["Prompt Registry"])


# ============== Request/Response Models ==============

class CreatePromptRequest(BaseModel):
    """Request to create a prompt."""
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$")
    system_prompt: str = Field(..., min_length=10)
    user_prompt_template: Optional[str] = None
    model_provider: ModelProvider = ModelProvider.OPENAI
    model_name: str = "gpt-4"
    temperature: float = 0.7
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ActivatePromptRequest(BaseModel):
    """Request to activate a prompt for A/B testing."""
    ab_test: bool = False
    control_prompt_id: Optional[UUID] = None
    traffic_split: Dict[str, float] = Field(default_factory=lambda: {"control": 0.5, "treatment": 0.5})


class PromptMetricsResponse(BaseModel):
    """Response for prompt metrics."""
    prompt_id: UUID
    name: str
    version: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    avg_latency_ms: Optional[float]
    user_satisfaction_score: Optional[float]
    accuracy_score: Optional[float]


class ABTestCreateRequest(BaseModel):
    """Request to create A/B test."""
    control_prompt_id: UUID
    treatment_prompt_id: UUID
    traffic_split: Dict[str, float] = Field(default_factory=lambda: {"control": 0.5, "treatment": 0.5})
    success_metric: str = "accuracy"
    min_samples: int = 100
    max_duration_days: int = 7


class ABTestResponse(BaseModel):
    """Response for A/B test."""
    test_id: UUID
    status: str
    control_prompt_id: UUID
    treatment_prompt_id: UUID
    control_metrics: Dict[str, Any]
    treatment_metrics: Dict[str, Any]
    winner: Optional[str]
    sample_size: int


# ============== Endpoints ==============

@router.get(
    "",
    response_model=List[PromptResponse],
    summary="List prompts",
    description="Get all prompts with optional filtering."
)
async def list_prompts(
    name: Optional[str] = Query(None, description="Filter by name"),
    status: Optional[PromptStatus] = Query(None, description="Filter by status"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all prompts with filtering.
    """
    query = select(PromptDB)
    
    if name:
        query = query.where(PromptDB.name.ilike(f"%{name}%"))
    
    if status:
        query = query.where(PromptDB.status == status.value)
    
    if tag:
        query = query.where(PromptDB.tags.contains([tag]))
    
    query = query.order_by(PromptDB.created_at.desc())
    
    result = await db.execute(query)
    prompts = result.scalars().all()
    
    return [
        PromptResponse(
            id=p.id,
            name=p.name,
            version=p.version,
            status=p.status,
            system_prompt=p.system_prompt,
            user_prompt_template=p.user_prompt_template,
            model_provider=p.model_provider,
            model_name=p.model_name,
            temperature=p.temperature,
            max_tokens=p.max_tokens,
            description=p.description,
            tags=p.tags or [],
            use_case=p.use_case,
            total_calls=p.total_calls,
            successful_calls=p.successful_calls,
            avg_latency_ms=p.avg_latency_ms,
            accuracy_score=p.accuracy_score,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in prompts
    ]


@router.get(
    "/{prompt_id}",
    response_model=PromptResponse,
    summary="Get prompt details",
    description="Get detailed information about a specific prompt."
)
async def get_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific prompt by ID.
    """
    result = await db.execute(
        select(PromptDB).where(PromptDB.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    return PromptResponse(
        id=prompt.id,
        name=prompt.name,
        version=prompt.version,
        status=prompt.status,
        system_prompt=prompt.system_prompt,
        user_prompt_template=prompt.user_prompt_template,
        model_provider=prompt.model_provider,
        model_name=prompt.model_name,
        temperature=prompt.temperature,
        max_tokens=prompt.max_tokens,
        description=prompt.description,
        tags=prompt.tags or [],
        use_case=prompt.use_case,
        total_calls=prompt.total_calls,
        successful_calls=prompt.successful_calls,
        avg_latency_ms=prompt.avg_latency_ms,
        accuracy_score=prompt.accuracy_score,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.post(
    "",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create prompt",
    description="Create a new prompt version."
)
async def create_prompt(
    request: CreatePromptRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new prompt version.
    
    The prompt starts in DRAFT status and must be activated before use.
    """
    # Check if version already exists
    existing = await db.execute(
        select(PromptDB)
        .where(PromptDB.name == request.name)
        .where(PromptDB.version == request.version)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Prompt {request.name} version {request.version} already exists"
        )
    
    # Create prompt
    prompt = PromptDB(
        name=request.name,
        version=request.version,
        status=PromptStatus.DRAFT.value,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        model_provider=request.model_provider.value,
        model_name=request.model_name,
        temperature=request.temperature,
        description=request.description,
        tags=request.tags,
    )
    
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    
    logger.info(f"Created prompt {prompt.id}: {request.name}@{request.version}")
    
    return PromptResponse(
        id=prompt.id,
        name=prompt.name,
        version=prompt.version,
        status=prompt.status,
        system_prompt=prompt.system_prompt,
        user_prompt_template=prompt.user_prompt_template,
        model_provider=prompt.model_provider,
        model_name=prompt.model_name,
        temperature=prompt.temperature,
        max_tokens=prompt.max_tokens,
        description=prompt.description,
        tags=prompt.tags or [],
        use_case=prompt.use_case,
        total_calls=prompt.total_calls,
        successful_calls=prompt.successful_calls,
        avg_latency_ms=prompt.avg_latency_ms,
        accuracy_score=prompt.accuracy_score,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.patch(
    "/{prompt_id}",
    response_model=PromptResponse,
    summary="Update prompt",
    description="Update a prompt (only allowed for DRAFT prompts)."
)
async def update_prompt(
    prompt_id: UUID,
    request: PromptUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a prompt.
    
    Only DRAFT prompts can be updated. For active prompts,
    create a new version instead.
    """
    result = await db.execute(
        select(PromptDB).where(PromptDB.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    if prompt.status != PromptStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update prompt in '{prompt.status}' status. Create a new version instead."
        )
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)
    
    await db.commit()
    await db.refresh(prompt)
    
    return PromptResponse(
        id=prompt.id,
        name=prompt.name,
        version=prompt.version,
        status=prompt.status,
        system_prompt=prompt.system_prompt,
        user_prompt_template=prompt.user_prompt_template,
        model_provider=prompt.model_provider,
        model_name=prompt.model_name,
        temperature=prompt.temperature,
        max_tokens=prompt.max_tokens,
        description=prompt.description,
        tags=prompt.tags or [],
        use_case=prompt.use_case,
        total_calls=prompt.total_calls,
        successful_calls=prompt.successful_calls,
        avg_latency_ms=prompt.avg_latency_ms,
        accuracy_score=prompt.accuracy_score,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.patch(
    "/{prompt_id}/activate",
    response_model=PromptResponse,
    summary="Activate prompt",
    description="Activate a prompt for use, optionally starting A/B test."
)
async def activate_prompt(
    prompt_id: UUID,
    request: ActivatePromptRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a prompt.
    
    If A/B testing is enabled, starts an A/B test against the control prompt.
    """
    result = await db.execute(
        select(PromptDB).where(PromptDB.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    if prompt.status not in [PromptStatus.DRAFT.value, PromptStatus.IN_TEST.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot activate prompt in '{prompt.status}' status"
        )
    
    if request.ab_test:
        if not request.control_prompt_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="control_prompt_id required for A/B test"
            )
        
        # Create A/B test
        ab_framework = get_ab_testing_framework()
        test = ab_framework.create_test(ABTestConfig(
            control_prompt_id=request.control_prompt_id,
            treatment_prompt_id=prompt_id,
            traffic_split=request.traffic_split,
        ))
        
        prompt.status = PromptStatus.IN_TEST.value
        prompt.ab_test_group = "treatment"
        
        logger.info(f"Started A/B test {test.id} for prompt {prompt_id}")
    else:
        # Deactivate other versions
        await db.execute(
            select(PromptDB)
            .where(PromptDB.name == prompt.name)
            .where(PromptDB.status == PromptStatus.ACTIVE.value)
        )
        
        prompt.status = PromptStatus.ACTIVE.value
        prompt.activated_at = datetime.utcnow()
        
        logger.info(f"Activated prompt {prompt_id}")
    
    await db.commit()
    await db.refresh(prompt)
    
    # Invalidate cache
    loader = get_prompt_loader()
    loader.invalidate_cache(prompt.name)
    
    return PromptResponse(
        id=prompt.id,
        name=prompt.name,
        version=prompt.version,
        status=prompt.status,
        system_prompt=prompt.system_prompt,
        user_prompt_template=prompt.user_prompt_template,
        model_provider=prompt.model_provider,
        model_name=prompt.model_name,
        temperature=prompt.temperature,
        max_tokens=prompt.max_tokens,
        description=prompt.description,
        tags=prompt.tags or [],
        use_case=prompt.use_case,
        total_calls=prompt.total_calls,
        successful_calls=prompt.successful_calls,
        avg_latency_ms=prompt.avg_latency_ms,
        accuracy_score=prompt.accuracy_score,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
    )


@router.get(
    "/{prompt_id}/metrics",
    response_model=PromptMetricsResponse,
    summary="Get prompt metrics",
    description="Get performance metrics for a prompt."
)
async def get_prompt_metrics(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get performance metrics for a prompt.
    """
    result = await db.execute(
        select(PromptDB).where(PromptDB.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt {prompt_id} not found"
        )
    
    success_rate = (
        prompt.successful_calls / prompt.total_calls * 100
        if prompt.total_calls > 0 else 0
    )
    
    return PromptMetricsResponse(
        prompt_id=prompt.id,
        name=prompt.name,
        version=prompt.version,
        total_calls=prompt.total_calls,
        successful_calls=prompt.successful_calls,
        failed_calls=prompt.failed_calls,
        success_rate=round(success_rate, 2),
        avg_latency_ms=prompt.avg_latency_ms,
        user_satisfaction_score=prompt.user_satisfaction_score,
        accuracy_score=prompt.accuracy_score,
    )


@router.post(
    "/ab-tests",
    response_model=ABTestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create A/B test",
    description="Create a new A/B test between two prompt versions."
)
async def create_ab_test(
    request: ABTestCreateRequest,
):
    """
    Create an A/B test between two prompt versions.
    """
    ab_framework = get_ab_testing_framework()
    
    config = ABTestConfig(
        control_prompt_id=request.control_prompt_id,
        treatment_prompt_id=request.treatment_prompt_id,
        traffic_split=request.traffic_split,
        success_metric=request.success_metric,
        min_samples=request.min_samples,
        max_duration_days=request.max_duration_days,
    )
    
    test = ab_framework.create_test(config)
    
    return ABTestResponse(
        test_id=test.id,
        status=test.status,
        control_prompt_id=config.control_prompt_id,
        treatment_prompt_id=config.treatment_prompt_id,
        control_metrics=test.get_control_metrics(),
        treatment_metrics=test.get_treatment_metrics(),
        winner=None,
        sample_size=0,
    )


@router.get(
    "/ab-tests/active",
    response_model=List[ABTestResponse],
    summary="Get active A/B tests",
    description="Get all currently running A/B tests."
)
async def get_active_ab_tests():
    """
    Get all active A/B tests.
    """
    ab_framework = get_ab_testing_framework()
    tests = ab_framework.get_active_tests()
    
    return [
        ABTestResponse(
            test_id=t.id,
            status=t.status,
            control_prompt_id=t.config.control_prompt_id,
            treatment_prompt_id=t.config.treatment_prompt_id,
            control_metrics=t.get_control_metrics(),
            treatment_metrics=t.get_treatment_metrics(),
            winner=None,
            sample_size=t.control_calls + t.treatment_calls,
        )
        for t in tests
    ]


@router.post(
    "/ab-tests/{test_id}/stop",
    response_model=ABTestResponse,
    summary="Stop A/B test",
    description="Stop an A/B test manually."
)
async def stop_ab_test(
    test_id: UUID,
    reason: str = Query("manual", description="Reason for stopping"),
):
    """
    Stop an A/B test.
    """
    ab_framework = get_ab_testing_framework()
    
    try:
        result = ab_framework.stop_test(test_id, reason)
        
        return ABTestResponse(
            test_id=result.test_id,
            status=result.status,
            control_prompt_id=result.control_prompt_id,
            treatment_prompt_id=result.treatment_prompt_id,
            control_metrics=result.control_metrics,
            treatment_metrics=result.treatment_metrics,
            winner=result.winner,
            sample_size=result.sample_size,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/ab-tests/completed",
    response_model=List[ABTestResponse],
    summary="Get completed A/B tests",
    description="Get all completed A/B tests with results."
)
async def get_completed_ab_tests():
    """
    Get completed A/B tests.
    """
    ab_framework = get_ab_testing_framework()
    tests = ab_framework.get_completed_tests()
    
    return [
        ABTestResponse(
            test_id=t.test_id,
            status=t.status,
            control_prompt_id=t.control_prompt_id,
            treatment_prompt_id=t.treatment_prompt_id,
            control_metrics=t.control_metrics,
            treatment_metrics=t.treatment_metrics,
            winner=t.winner,
            sample_size=t.sample_size,
        )
        for t in tests
    ]


@router.post(
    "/cache/invalidate",
    summary="Invalidate prompt cache",
    description="Invalidate cached prompts to force reload from database."
)
async def invalidate_cache(
    name: Optional[str] = Query(None, description="Specific prompt name"),
    version: Optional[str] = Query(None, description="Specific version"),
):
    """
    Invalidate prompt cache.
    
    This forces prompts to be reloaded from the database on next use.
    """
    loader = get_prompt_loader()
    count = loader.invalidate_cache(name, version)
    
    return {
        "invalidated": count,
        "name": name,
        "version": version,
    }


# Import datetime
from datetime import datetime
