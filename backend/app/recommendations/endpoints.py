"""
Recommendation API Endpoints

FastAPI routes for the recommendation engine:
- Get personalized recommendations
- Record feedback
- View trending templates
- User preference insights
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_current_active_user
from app.models.user import User
from app.core.logging import get_logger

from app.recommendations.engine import (
    get_recommendation_engine,
    RecommendationEngine,
    RecommendationType,
    RecommendationResult,
)
from app.recommendations.personalization import get_behavior_tracker
from app.recommendations.templates import TemplateManager

logger = get_logger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class RecommendationContext(BaseModel):
    """Context for recommendation request."""
    project_type: Optional[str] = Field(None, description="Type of project (concrete, structural, etc.)")
    phase: Optional[str] = Field(None, description="Current workflow phase")
    tags: List[str] = Field(default_factory=list, description="Relevant tags")
    elements: List[str] = Field(default_factory=list, description="Detected construction elements")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")


class FeedbackRequest(BaseModel):
    """Request to record feedback on a recommendation."""
    recommendation_id: str = Field(..., description="ID of the recommendation")
    feedback_type: str = Field(..., description="Type: accepted, rejected, helpful, not_helpful")
    comment: Optional[str] = Field(None, description="Optional feedback comment")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RecommendationResponse(BaseModel):
    """Single recommendation in response."""
    id: str
    type: str
    title: str
    description: str
    content: Dict[str, Any]
    priority: int
    confidence: float
    reason: str
    tags: List[str]


class RecommendationsListResponse(BaseModel):
    """Response containing multiple recommendations."""
    recommendations: List[RecommendationResponse]
    total: int
    context_analysis: Dict[str, Any]


class TrendingTemplateResponse(BaseModel):
    """Trending template information."""
    item_id: str
    usage_count: int
    unique_users: int
    trending_score: float


class UserPreferencesResponse(BaseModel):
    """User preference insights."""
    favorite_categories: List[tuple]
    favorite_templates: List[tuple]
    activity_patterns: Dict[str, Any]
    similar_users_count: int


class TemplateInputSchema(BaseModel):
    """Template input parameter."""
    name: str
    type: str
    unit: str
    required: bool
    description: str
    default_value: Optional[Any] = None


class TemplateOutputSchema(BaseModel):
    """Template output parameter."""
    name: str
    type: str
    unit: str
    description: str


class TemplateDetailResponse(BaseModel):
    """Detailed template information."""
    id: str
    name: str
    description: str
    category: str
    formula: str
    inputs: List[TemplateInputSchema]
    outputs: List[TemplateOutputSchema]
    tags: List[str]
    usage_count: int
    version: str
    references: List[str]


class TemplatesListResponse(BaseModel):
    """Response for listing templates."""
    templates: List[TemplateDetailResponse]
    categories: List[str]
    total: int


# =============================================================================
# API Endpoints
# =============================================================================

@router.get(
    "",
    response_model=RecommendationsListResponse,
    summary="Get personalized recommendations",
    description="Get recommendations based on user profile and current context.",
)
async def get_recommendations(
    project_type: Optional[str] = Query(None, description="Project type filter"),
    phase: Optional[str] = Query(None, description="Workflow phase"),
    limit: int = Query(10, ge=1, le=50, description="Maximum recommendations to return"),
    rec_type: Optional[str] = Query(None, alias="type", description="Filter by recommendation type"),
    current_user: User = Depends(get_current_active_user),
) -> RecommendationsListResponse:
    """
    Get personalized recommendations for the current user.
    
    Recommendations are generated based on:
    - User's past behavior and preferences
    - Current project context
    - Trending templates among similar users
    - Rule-based contextual suggestions
    """
    try:
        engine = await get_recommendation_engine()
        
        # Build context
        context = {
            "project_type": project_type,
            "phase": phase,
            "user_id": str(current_user.id),
        }
        
        # Determine recommendation type
        recommendation_type = None
        if rec_type:
            try:
                recommendation_type = RecommendationType(rec_type)
            except ValueError:
                pass
        
        # Get recommendations
        recommendations = await engine.get_recommendations(
            user_id=current_user.id,
            context=context,
            limit=limit,
            recommendation_type=recommendation_type,
        )
        
        # Analyze context
        from app.recommendations.context import get_context_analyzer
        analyzer = get_context_analyzer()
        analyzed_context = analyzer.analyze(context)
        
        return RecommendationsListResponse(
            recommendations=[_to_recommendation_response(r) for r in recommendations],
            total=len(recommendations),
            context_analysis=analyzed_context.to_dict(),
        )
    
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations",
        )


@router.post(
    "/context",
    response_model=RecommendationsListResponse,
    summary="Get recommendations with full context",
    description="Provide detailed context for more accurate recommendations.",
)
async def get_recommendations_with_context(
    context: RecommendationContext,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
) -> RecommendationsListResponse:
    """
    Get recommendations with detailed context.
    
    Use this endpoint when you have rich context data about the user's
    current project and workflow state.
    """
    try:
        engine = await get_recommendation_engine()
        
        # Build full context
        full_context = {
            "project_type": context.project_type,
            "phase": context.phase,
            "tags": context.tags,
            "elements": context.elements,
            **context.metadata,
        }
        
        recommendations = await engine.get_recommendations(
            user_id=current_user.id,
            context=full_context,
            limit=limit,
        )
        
        # Analyze context
        from app.recommendations.context import get_context_analyzer
        analyzer = get_context_analyzer()
        analyzed_context = analyzer.analyze(full_context)
        
        return RecommendationsListResponse(
            recommendations=[_to_recommendation_response(r) for r in recommendations],
            total=len(recommendations),
            context_analysis=analyzed_context.to_dict(),
        )
    
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations",
        )


@router.post(
    "/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record recommendation feedback",
    description="Provide feedback on a recommendation to improve future suggestions.",
)
async def record_feedback(
    feedback: FeedbackRequest,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """
    Record user feedback on a recommendation.
    
    Feedback types:
    - accepted: User accepted/used the recommendation
    - rejected: User dismissed the recommendation
    - helpful: User found it helpful
    - not_helpful: User didn't find it useful
    """
    try:
        engine = await get_recommendation_engine()
        
        await engine.record_feedback(
            user_id=current_user.id,
            recommendation_id=feedback.recommendation_id,
            feedback_type=feedback.feedback_type,
            metadata={
                "comment": feedback.comment,
                **feedback.metadata,
            },
        )
    
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feedback",
        )


@router.get(
    "/trending",
    response_model=List[TrendingTemplateResponse],
    summary="Get trending templates",
    description="Get templates that are currently popular among users.",
)
async def get_trending(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_active_user),
) -> List[TrendingTemplateResponse]:
    """
    Get trending templates based on recent usage.
    
    This endpoint uses collaborative filtering to show templates
    that are popular among users with similar patterns.
    """
    try:
        engine = await get_recommendation_engine()
        trending = await engine.get_trending_templates(limit=limit, days=days)
        
        return [
            TrendingTemplateResponse(
                item_id=t["item_id"],
                usage_count=t["usage_count"],
                unique_users=t["unique_users"],
                trending_score=t["trending_score"],
            )
            for t in trending
        ]
    
    except Exception as e:
        logger.error(f"Failed to get trending: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trending templates",
        )


@router.get(
    "/preferences",
    response_model=UserPreferencesResponse,
    summary="Get user preferences",
    description="Get insights into user's preferences and behavior patterns.",
)
async def get_user_preferences(
    current_user: User = Depends(get_current_active_user),
) -> UserPreferencesResponse:
    """
    Get user's preference insights.
    
    Returns aggregated data about:
    - Most used categories
    - Frequently used templates
    - Activity patterns
    - Similar users count
    """
    try:
        engine = await get_recommendation_engine()
        preferences = await engine.get_user_preferences(current_user.id)
        
        return UserPreferencesResponse(
            favorite_categories=preferences["favorite_categories"],
            favorite_templates=preferences["favorite_templates"],
            activity_patterns=preferences["activity_patterns"],
            similar_users_count=preferences["similar_users_count"],
        )
    
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user preferences",
        )


@router.get(
    "/templates",
    response_model=TemplatesListResponse,
    summary="List available templates",
    description="Get all available formula templates organized by category.",
)
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search query"),
    current_user: User = Depends(get_current_active_user),
) -> TemplatesListResponse:
    """
    List available formula templates.
    
    Can be filtered by category, tag, or search query.
    """
    try:
        manager = TemplateManager()
        await manager.load_templates()
        
        # Get templates
        if search:
            templates = manager.search_templates(search)
        elif category:
            templates = manager.get_templates_by_category(category)
        elif tag:
            templates = manager.get_templates_by_tag(tag)
        else:
            templates = manager.get_all_templates()
        
        return TemplatesListResponse(
            templates=[_to_template_response(t) for t in templates],
            categories=manager.get_categories(),
            total=len(templates),
        )
    
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list templates",
        )


@router.get(
    "/templates/{template_id}",
    response_model=TemplateDetailResponse,
    summary="Get template details",
    description="Get detailed information about a specific template.",
)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
) -> TemplateDetailResponse:
    """Get detailed information about a specific formula template."""
    try:
        manager = TemplateManager()
        await manager.load_templates()
        
        template = manager.get_template(template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template not found: {template_id}",
            )
        
        return _to_template_response(template)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get template",
        )


@router.post(
    "/templates/{template_id}/use",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record template usage",
    description="Record that user used a specific template.",
)
async def record_template_usage(
    template_id: str,
    context: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Record that user used a template (for usage tracking and trending)."""
    try:
        tracker = await get_behavior_tracker()
        
        await tracker.record_interaction(
            user_id=current_user.id,
            item_id=f"template:{template_id}",
            interaction_type="used",
            metadata={
                "item_type": "template",
                "context": context or {},
            },
        )
    
    except Exception as e:
        logger.error(f"Failed to record template usage: {e}")
        # Don't fail the request for tracking errors


# =============================================================================
# Helper Functions
# =============================================================================

def _to_recommendation_response(rec: RecommendationResult) -> RecommendationResponse:
    """Convert RecommendationResult to API response."""
    return RecommendationResponse(
        id=rec.id,
        type=rec.type.value if isinstance(rec.type, RecommendationType) else rec.type,
        title=rec.title,
        description=rec.description,
        content=rec.content,
        priority=rec.priority.value if hasattr(rec.priority, 'value') else rec.priority,
        confidence=rec.confidence,
        reason=rec.reason,
        tags=rec.tags,
    )


def _to_template_response(template) -> TemplateDetailResponse:
    """Convert FormulaTemplate to API response."""
    return TemplateDetailResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        formula=template.formula,
        inputs=[
            TemplateInputSchema(
                name=inp.name,
                type=inp.type,
                unit=inp.unit,
                required=inp.required,
                description=inp.description,
                default_value=inp.default_value,
            )
            for inp in template.inputs
        ],
        outputs=[
            TemplateOutputSchema(
                name=out.name,
                type=out.type,
                unit=out.unit,
                description=out.description,
            )
            for out in template.outputs
        ],
        tags=template.tags,
        usage_count=template.usage_count,
        version=template.version,
        references=template.references,
    )
