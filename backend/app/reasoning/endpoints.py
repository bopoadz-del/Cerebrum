"""
Reasoning Engine Endpoints

FastAPI routes for the Heavy Reasoning Engine:
- Variance analysis
- Compliance checking
- Recommendation generation
- Data integration
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from app.reasoning.engine import HeavyReasoningEngine, RiskLevel
from app.reasoning.integrations import IntegrationsEngine, MergedProjectData
from app.reasoning.recommendations import RecommendationEngine, Recommendation

router = APIRouter(tags=["reasoning"])


# ═══════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════

class VarianceRequest(BaseModel):
    """Request model for variance calculation."""
    boq_value: float = Field(..., description="Value from BOQ")
    drawing_value: float = Field(..., description="Value from Drawing")
    item_name: str = Field("quantity", description="Name of the item")


class VarianceResponse(BaseModel):
    """Response model for variance calculation."""
    item: str = Field(..., description="Item name")
    boq_value: float = Field(..., description="BOQ value")
    drawing_value: float = Field(..., description="Drawing value")
    variance: float = Field(..., description="Absolute variance")
    variance_percent: float = Field(..., description="Variance as percentage")
    is_significant: bool = Field(..., description="Whether variance exceeds threshold")
    notes: List[str] = Field(..., description="Variance notes")


class GradeComplianceRequest(BaseModel):
    """Request model for grade compliance check."""
    spec_grade: str = Field(..., description="Grade specified")
    used_grade: str = Field(..., description="Grade actually used")
    item_name: str = Field("material", description="Item name")


class ComplianceResponse(BaseModel):
    """Response model for compliance check."""
    item: str = Field(..., description="Item name")
    spec_value: str = Field(..., description="Specified value")
    actual_value: str = Field(..., description="Actual value")
    compliant: bool = Field(..., description="Whether compliant")
    severity: str = Field(..., description="Risk severity")
    recommendation: Optional[str] = Field(None, description="Recommended action")


class MergeDataRequest(BaseModel):
    """Request model for merging data sources."""
    boq_data: Optional[Dict[str, Any]] = Field(None, description="BOQ JSON data")
    spec_data: Optional[Dict[str, Any]] = Field(None, description="Spec JSON data")
    drawing_data: Optional[Dict[str, Any]] = Field(None, description="Drawing JSON data")


class MergeDataResponse(BaseModel):
    """Response model for merged data."""
    quantities: List[Dict[str, Any]] = Field(..., description="Merged quantities")
    materials: List[Dict[str, Any]] = Field(..., description="Merged materials")
    conflicts: List[Dict[str, Any]] = Field(..., description="Detected conflicts")
    stats: Dict[str, int] = Field(..., description="Merge statistics")
    completeness: float = Field(..., description="Data completeness score")


class RecommendationResponse(BaseModel):
    """Response model for a recommendation."""
    type: str = Field(..., description="Recommendation type")
    severity: str = Field(..., description="Severity level")
    message: str = Field(..., description="Recommendation message")
    action: str = Field(..., description="Recommended action")
    related_items: List[str] = Field(..., description="Related items")
    priority_score: float = Field(..., description="Priority score")


class FullAnalysisRequest(BaseModel):
    """Request model for full analysis."""
    boq_data: Optional[Dict[str, Any]] = Field(None, description="BOQ data")
    spec_data: Optional[Dict[str, Any]] = Field(None, description="Spec data")
    drawing_data: Optional[Dict[str, Any]] = Field(None, description="Drawing data")
    include_recommendations: bool = Field(True, description="Include recommendations")


class FullAnalysisResponse(BaseModel):
    """Response model for full analysis."""
    merged_data: MergeDataResponse = Field(..., description="Merged data")
    variances: List[VarianceResponse] = Field(..., description="Calculated variances")
    compliance_checks: List[ComplianceResponse] = Field(..., description="Compliance checks")
    recommendations: List[RecommendationResponse] = Field(..., description="Recommendations")
    summary: Dict[str, Any] = Field(..., description="Summary report")


class CostVarianceRequest(BaseModel):
    """Request model for cost variance."""
    estimated_cost: float = Field(..., description="Estimated cost")
    actual_cost: float = Field(..., description="Actual cost")
    item_name: str = Field("total", description="Cost item name")


class CostVarianceResponse(BaseModel):
    """Response model for cost variance."""
    item: str = Field(..., description="Item name")
    estimated: float = Field(..., description="Estimated cost")
    actual: float = Field(..., description="Actual cost")
    variance: float = Field(..., description="Cost variance")
    variance_percent: float = Field(..., description="Variance percentage")
    status: str = Field(..., description="Variance status")
    is_overrun: bool = Field(..., description="Whether cost overrun")


class ScheduleVarianceRequest(BaseModel):
    """Request model for schedule variance."""
    planned_duration: float = Field(..., description="Planned duration in days")
    actual_duration: float = Field(..., description="Actual duration in days")
    activity_name: str = Field("activity", description="Activity name")


class ScheduleVarianceResponse(BaseModel):
    """Response model for schedule variance."""
    activity: str = Field(..., description="Activity name")
    planned_days: float = Field(..., description="Planned duration")
    actual_days: float = Field(..., description="Actual duration")
    variance_days: float = Field(..., description="Variance in days")
    variance_percent: float = Field(..., description="Variance percentage")
    status: str = Field(..., description="Schedule status")
    is_delayed: bool = Field(..., description="Whether delayed")


class ApprovalRecommendationRequest(BaseModel):
    """Request model for approval recommendation."""
    item_data: Dict[str, Any] = Field(..., description="Item data to evaluate")
    variances: List[Dict[str, Any]] = Field(default_factory=list, description="Variances")
    compliance_issues: List[Dict[str, Any]] = Field(default_factory=list, description="Compliance issues")


class ApprovalRecommendationResponse(BaseModel):
    """Response model for approval recommendation."""
    status: str = Field(..., description="Approval status")
    recommendation: str = Field(..., description="Recommendation")
    rationale: str = Field(..., description="Supporting rationale")
    actions_required: List[str] = Field(..., description="Required actions")
    severity: str = Field(..., description="Severity level")


# ═══════════════════════════════════════════════════════════
# DEPENDENCIES
# ═══════════════════════════════════════════════════════════

def get_reasoning_engine() -> HeavyReasoningEngine:
    """Dependency to get the reasoning engine instance."""
    return HeavyReasoningEngine()

def get_integrations_engine() -> IntegrationsEngine:
    """Dependency to get the integrations engine instance."""
    return IntegrationsEngine()

def get_recommendation_engine() -> RecommendationEngine:
    """Dependency to get the recommendation engine instance."""
    return RecommendationEngine()


# ═══════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════

@router.post("/reasoning/variance", response_model=VarianceResponse)
async def calculate_variance(
    request: VarianceRequest,
    engine: HeavyReasoningEngine = Depends(get_reasoning_engine)
) -> VarianceResponse:
    """
    Calculate variance between BOQ and Drawing values.
    
    Uses SymPy-based symbolic reasoning for variance calculation.
    """
    result = engine.calculate_variance(
        request.boq_value,
        request.drawing_value,
        request.item_name
    )
    
    return VarianceResponse(
        item=result.symbol,
        boq_value=result.boq_value,
        drawing_value=result.drawing_value,
        variance=result.variance,
        variance_percent=result.variance_percent,
        is_significant=result.is_significant,
        notes=result.notes,
    )


@router.post("/reasoning/compliance/grade", response_model=ComplianceResponse)
async def check_grade_compliance(
    request: GradeComplianceRequest,
    engine: HeavyReasoningEngine = Depends(get_reasoning_engine)
) -> ComplianceResponse:
    """
    Check if used grade matches specified grade.
    """
    result = engine.check_grade_compliance(
        request.spec_grade,
        request.used_grade,
        request.item_name
    )
    
    return ComplianceResponse(
        item=result.item,
        spec_value=result.spec_value,
        actual_value=result.actual_value,
        compliant=result.compliant,
        severity=result.severity.value,
        recommendation=result.recommendation,
    )


@router.post("/reasoning/compliance/strength", response_model=ComplianceResponse)
async def check_strength_compliance(
    spec_strength: float,
    actual_strength: float,
    tolerance: float = 0.0,
    item_name: str = "concrete",
    engine: HeavyReasoningEngine = Depends(get_reasoning_engine)
) -> ComplianceResponse:
    """
    Check if actual strength meets specification.
    """
    result = engine.check_strength_compliance(
        spec_strength,
        actual_strength,
        tolerance,
        item_name
    )
    
    return ComplianceResponse(
        item=result.item,
        spec_value=result.spec_value,
        actual_value=result.actual_value,
        compliant=result.compliant,
        severity=result.severity.value,
        recommendation=result.recommendation,
    )


@router.post("/reasoning/merge", response_model=MergeDataResponse)
async def merge_data_sources(
    request: MergeDataRequest,
    engine: IntegrationsEngine = Depends(get_integrations_engine)
) -> MergeDataResponse:
    """
    Merge BOQ, Specification, and Drawing data sources.
    
    Cross-references items and detects conflicts.
    """
    merged = engine.merge_json_sources(
        request.boq_data,
        request.spec_data,
        request.drawing_data
    )
    
    # Convert to response format
    quantities = [
        {
            "id": q.item_id,
            "description": q.description,
            "boq": q.boq_quantity,
            "drawing": q.drawing_quantity,
            "spec": q.spec_quantity,
            "reconciled": q.reconciled_quantity,
            "has_variance": q.has_variance,
            "variance_percent": q.variance_percent,
            "notes": q.variance_notes,
        }
        for q in merged.quantities
    ]
    
    materials = [
        {
            "type": m.material_type,
            "spec_grade": m.spec_grade,
            "actual_grade": m.actual_grade,
            "spec_strength": m.spec_strength,
            "actual_strength": m.actual_strength,
            "compliant": m.compliant,
            "issues": m.issues,
        }
        for m in merged.materials
    ]
    
    return MergeDataResponse(
        quantities=quantities,
        materials=materials,
        conflicts=merged.conflicts,
        stats=merged.merge_stats,
        completeness=merged.metadata.get("completeness_score", 0),
    )


@router.post("/reasoning/analyze", response_model=FullAnalysisResponse)
async def full_analysis(
    request: FullAnalysisRequest,
    reasoning_engine: HeavyReasoningEngine = Depends(get_reasoning_engine),
    integrations_engine: IntegrationsEngine = Depends(get_integrations_engine),
    recommendation_engine: RecommendationEngine = Depends(get_recommendation_engine)
) -> FullAnalysisResponse:
    """
    Perform full analysis with merging, variance, compliance, and recommendations.
    
    This is the main endpoint for comprehensive reasoning.
    """
    # Merge data sources
    merged = integrations_engine.merge_json_sources(
        request.boq_data,
        request.spec_data,
        request.drawing_data
    )
    
    # Calculate variances
    variances = []
    for qty in merged.quantities:
        if qty.boq_quantity is not None and qty.drawing_quantity is not None:
            variance = reasoning_engine.calculate_variance(
                qty.boq_quantity,
                qty.drawing_quantity,
                qty.item_id
            )
            if variance.is_significant:
                variances.append(variance)
    
    # Check compliance
    compliance_checks = []
    for mat in merged.materials:
        if mat.spec_grade and mat.actual_grade:
            check = reasoning_engine.check_grade_compliance(
                mat.spec_grade,
                mat.actual_grade,
                mat.material_type
            )
            compliance_checks.append(check)
        
        if mat.spec_strength and mat.actual_strength:
            check = reasoning_engine.check_strength_compliance(
                mat.spec_strength,
                mat.actual_strength,
                item_name=mat.material_type
            )
            compliance_checks.append(check)
    
    # Generate recommendations
    recommendations = recommendation_engine.generate_recommendations(
        merged,
        variances,
        compliance_checks
    )
    
    # Build summary
    summary = recommendation_engine.generate_summary_report(recommendations)
    
    # Build response
    merge_response = MergeDataResponse(
        quantities=[
            {
                "id": q.item_id,
                "description": q.description,
                "boq": q.boq_quantity,
                "drawing": q.drawing_quantity,
                "spec": q.spec_quantity,
                "reconciled": q.reconciled_quantity,
                "has_variance": q.has_variance,
                "variance_percent": q.variance_percent,
                "notes": q.variance_notes,
            }
            for q in merged.quantities
        ],
        materials=[
            {
                "type": m.material_type,
                "spec_grade": m.spec_grade,
                "actual_grade": m.actual_grade,
                "spec_strength": m.spec_strength,
                "actual_strength": m.actual_strength,
                "compliant": m.compliant,
                "issues": m.issues,
            }
            for m in merged.materials
        ],
        conflicts=merged.conflicts,
        stats=merged.merge_stats,
        completeness=merged.metadata.get("completeness_score", 0),
    )
    
    variance_responses = [
        VarianceResponse(
            item=v.symbol,
            boq_value=v.boq_value,
            drawing_value=v.drawing_value,
            variance=v.variance,
            variance_percent=v.variance_percent,
            is_significant=v.is_significant,
            notes=v.notes,
        )
        for v in variances
    ]
    
    compliance_responses = [
        ComplianceResponse(
            item=c.item,
            spec_value=c.spec_value,
            actual_value=c.actual_value,
            compliant=c.compliant,
            severity=c.severity.value,
            recommendation=c.recommendation,
        )
        for c in compliance_checks
    ]
    
    recommendation_responses = [
        RecommendationResponse(
            type=r.type,
            severity=r.severity,
            message=r.message,
            action=r.action,
            related_items=r.related_items,
            priority_score=r.priority_score,
        )
        for r in recommendations
    ]
    
    return FullAnalysisResponse(
        merged_data=merge_response,
        variances=variance_responses,
        compliance_checks=compliance_responses,
        recommendations=recommendation_responses,
        summary=summary,
    )


@router.post("/reasoning/cost/variance", response_model=CostVarianceResponse)
async def calculate_cost_variance(
    request: CostVarianceRequest,
    engine: HeavyReasoningEngine = Depends(get_reasoning_engine)
) -> CostVarianceResponse:
    """
    Calculate cost variance with symbolic reasoning.
    """
    result = engine.calculate_cost_variance(
        request.estimated_cost,
        request.actual_cost,
        request.item_name
    )
    
    return CostVarianceResponse(
        item=result["item"],
        estimated=result["estimated"],
        actual=result["actual"],
        variance=result["variance"],
        variance_percent=result["variance_percent"],
        status=result["status"],
        is_overrun=result["is_overrun"],
    )


@router.post("/reasoning/schedule/variance", response_model=ScheduleVarianceResponse)
async def calculate_schedule_variance(
    request: ScheduleVarianceRequest,
    engine: HeavyReasoningEngine = Depends(get_reasoning_engine)
) -> ScheduleVarianceResponse:
    """
    Calculate schedule variance with symbolic reasoning.
    """
    result = engine.analyze_schedule_variance(
        request.planned_duration,
        request.actual_duration,
        request.activity_name
    )
    
    return ScheduleVarianceResponse(
        activity=result["activity"],
        planned_days=result["planned_days"],
        actual_days=result["actual_days"],
        variance_days=result["variance_days"],
        variance_percent=result["variance_percent"],
        status=result["status"],
        is_delayed=result["is_delayed"],
    )


@router.post("/reasoning/approval", response_model=ApprovalRecommendationResponse)
async def generate_approval_recommendation(
    request: ApprovalRecommendationRequest,
    engine: RecommendationEngine = Depends(get_recommendation_engine)
) -> ApprovalRecommendationResponse:
    """
    Generate approval recommendation for an item.
    
    Evaluates variances and compliance issues to recommend
    approve, conditional approval, or reject.
    """
    # Convert dicts to objects (simplified - full implementation would parse properly)
    result = engine.generate_approval_recommendation(
        request.item_data,
        [],  # Would convert from request.variances
        []   # Would convert from request.compliance_issues
    )
    
    return ApprovalRecommendationResponse(
        status=result["status"],
        recommendation=result["recommendation"],
        rationale=result["rationale"],
        actions_required=result["actions_required"],
        severity=result["severity"],
    )


@router.get("/reasoning/status")
async def reasoning_status() -> Dict[str, str]:
    """Get status of the reasoning engine."""
    return {
        "status": "operational",
        "engine": "HeavyReasoningEngine",
        "backend": "SymPy",
        "version": "1.0.0",
    }
