"""
Self-Healing System API Endpoints

FastAPI endpoints for error detection, incident management, and
automatic healing operations.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.healing.circuit_breaker_auto import get_circuit_breaker
from app.healing.error_detection import (
    ErrorDetector,
    ErrorIncident,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    get_error_detector,
)
from app.healing.patch_generation import get_patch_generator
from app.healing.root_cause import get_root_cause_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/healing", tags=["Self-Healing System"])


# ============== Request/Response Models ==============

class CreateIncidentRequest(BaseModel):
    """Request to create a manual incident."""
    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=10)
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    capability_id: Optional[UUID] = None


class IncidentResponse(BaseModel):
    """Response for an incident."""
    id: UUID
    title: str
    description: str
    severity: str
    status: str
    source: str
    error_type: str
    error_message: str
    capability_id: Optional[UUID]
    endpoint: Optional[str]
    occurrence_count: int
    first_seen_at: str
    last_seen_at: str


class UpdateIncidentRequest(BaseModel):
    """Request to update incident status."""
    status: IncidentStatus
    notes: Optional[str] = None


class AnalyzeIncidentResponse(BaseModel):
    """Response for incident analysis."""
    incident_id: UUID
    analysis_summary: str
    hypotheses: List[Dict[str, Any]]
    primary_hypothesis: Optional[Dict[str, Any]]
    suggested_tests: List[str]
    analysis_time_ms: float


class GeneratePatchRequest(BaseModel):
    """Request to generate a patch."""
    file_path: str
    original_code: str


class PatchResponse(BaseModel):
    """Response for a patch."""
    id: UUID
    incident_id: UUID
    file_path: str
    description: str
    confidence: float
    fix_type: str
    diff: str
    status: str
    sandbox_tested: bool
    sandbox_passed: bool


class CircuitStatusResponse(BaseModel):
    """Response for circuit status."""
    endpoint: str
    state: str
    failure_count: int
    success_count: int


class MetricsResponse(BaseModel):
    """Response for endpoint metrics."""
    endpoint: str
    total_requests: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    error_rate: float
    slow_request_count: int


# ============== Endpoints ==============

@router.get(
    "/incidents",
    response_model=List[IncidentResponse],
    summary="List incidents",
    description="Get all error incidents with optional filtering."
)
async def list_incidents(
    status: Optional[IncidentStatus] = Query(None, description="Filter by status"),
    severity: Optional[IncidentSeverity] = Query(None, description="Filter by severity"),
    capability_id: Optional[UUID] = Query(None, description="Filter by capability"),
    detector: ErrorDetector = Depends(get_error_detector),
):
    """
    List error incidents with filtering.
    """
    incidents = detector.get_incidents(
        status=status,
        severity=severity,
        capability_id=capability_id,
    )
    
    return [
        IncidentResponse(
            id=i.id,
            title=i.title,
            description=i.description,
            severity=i.severity.value,
            status=i.status.value,
            source=i.source.value,
            error_type=i.error_type,
            error_message=i.error_message,
            capability_id=i.capability_id,
            endpoint=i.endpoint,
            occurrence_count=i.occurrence_count,
            first_seen_at=i.first_seen_at.isoformat(),
            last_seen_at=i.last_seen_at.isoformat(),
        )
        for i in incidents
    ]


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details",
    description="Get detailed information about a specific incident."
)
async def get_incident(
    incident_id: UUID,
    detector: ErrorDetector = Depends(get_error_detector),
):
    """
    Get details of a specific incident.
    """
    incident = detector.get_incident(incident_id)
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    
    return IncidentResponse(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity.value,
        status=incident.status.value,
        source=incident.source.value,
        error_type=incident.error_type,
        error_message=incident.error_message,
        capability_id=incident.capability_id,
        endpoint=incident.endpoint,
        occurrence_count=incident.occurrence_count,
        first_seen_at=incident.first_seen_at.isoformat(),
        last_seen_at=incident.last_seen_at.isoformat(),
    )


@router.post(
    "/incidents",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create manual incident",
    description="Create a manually reported incident."
)
async def create_incident(
    request: CreateIncidentRequest,
    created_by: str = "manual",
    detector: ErrorDetector = Depends(get_error_detector),
):
    """
    Create a manually reported incident.
    """
    incident = await detector.create_manual_incident(
        title=request.title,
        description=request.description,
        severity=request.severity,
        created_by=created_by,
        capability_id=request.capability_id,
    )
    
    return IncidentResponse(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity.value,
        status=incident.status.value,
        source=incident.source.value,
        error_type=incident.error_type,
        error_message=incident.error_message,
        capability_id=incident.capability_id,
        endpoint=incident.endpoint,
        occurrence_count=incident.occurrence_count,
        first_seen_at=incident.first_seen_at.isoformat(),
        last_seen_at=incident.last_seen_at.isoformat(),
    )


@router.patch(
    "/incidents/{incident_id}",
    response_model=IncidentResponse,
    summary="Update incident status",
    description="Update the status of an incident."
)
async def update_incident(
    incident_id: UUID,
    request: UpdateIncidentRequest,
    updated_by: str = "manual",
    detector: ErrorDetector = Depends(get_error_detector),
):
    """
    Update incident status.
    """
    incident = await detector.update_incident_status(
        incident_id=incident_id,
        status=request.status,
        updated_by=updated_by,
        notes=request.notes,
    )
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    
    return IncidentResponse(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity.value,
        status=incident.status.value,
        source=incident.source.value,
        error_type=incident.error_type,
        error_message=incident.error_message,
        capability_id=incident.capability_id,
        endpoint=incident.endpoint,
        occurrence_count=incident.occurrence_count,
        first_seen_at=incident.first_seen_at.isoformat(),
        last_seen_at=incident.last_seen_at.isoformat(),
    )


@router.post(
    "/incidents/{incident_id}/analyze",
    response_model=AnalyzeIncidentResponse,
    summary="Analyze incident",
    description="Trigger AI root cause analysis for an incident."
)
async def analyze_incident(
    incident_id: UUID,
    code_context: Optional[Dict[str, str]] = None,
    detector: ErrorDetector = Depends(get_error_detector),
):
    """
    Analyze an incident to identify root cause.
    
    This uses GPT-4 to analyze the error and generate hypotheses
    about the root cause with confidence scores.
    """
    # Get incident
    incident = detector.get_incident(incident_id)
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    
    # Get analyzer
    analyzer = get_root_cause_analyzer()
    
    try:
        analysis = await analyzer.analyze(incident, code_context)
        
        return AnalyzeIncidentResponse(
            incident_id=incident_id,
            analysis_summary=analysis.analysis_summary,
            hypotheses=[
                {
                    "description": h.description,
                    "confidence": h.confidence,
                    "affected_files": h.affected_files,
                    "suggested_fix_type": h.suggested_fix_type,
                    "supporting_evidence": h.supporting_evidence,
                }
                for h in analysis.hypotheses
            ],
            primary_hypothesis={
                "description": analysis.primary_hypothesis.description,
                "confidence": analysis.primary_hypothesis.confidence,
                "affected_files": analysis.primary_hypothesis.affected_files,
                "suggested_fix_type": analysis.primary_hypothesis.suggested_fix_type,
            } if analysis.primary_hypothesis else None,
            suggested_tests=analysis.suggested_tests,
            analysis_time_ms=analysis.ai_analysis_time_ms,
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post(
    "/incidents/{incident_id}/patches",
    response_model=List[PatchResponse],
    summary="Generate patches",
    description="Generate code patches to fix the incident."
)
async def generate_patches(
    incident_id: UUID,
    request: GeneratePatchRequest,
    detector: ErrorDetector = Depends(get_error_detector),
):
    """
    Generate code patches to fix an incident.
    
    This uses AI to generate code patches based on the root cause
    analysis. Patches are tested in sandbox before being returned.
    """
    # Get incident
    incident = detector.get_incident(incident_id)
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found"
        )
    
    # Get root cause analysis first
    analyzer = get_root_cause_analyzer()
    analysis = await analyzer.analyze(incident)
    
    # Generate patch
    generator = get_patch_generator()
    
    try:
        result = await generator.generate_patch(
            incident_id=incident_id,
            file_path=request.file_path,
            original_code=request.original_code,
            root_cause=analysis,
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Patch generation failed: {result.errors}"
            )
        
        # Test patch in sandbox
        for patch in result.patches:
            await generator.test_patch_in_sandbox(patch)
        
        return [
            PatchResponse(
                id=p.id,
                incident_id=p.incident_id,
                file_path=p.file_path,
                description=p.description,
                confidence=p.confidence,
                fix_type=p.fix_type,
                diff=p.diff,
                status=p.status,
                sandbox_tested=p.sandbox_tested,
                sandbox_passed=p.sandbox_passed,
            )
            for p in result.patches
        ]
        
    except Exception as e:
        logger.error(f"Patch generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Patch generation failed: {str(e)}"
        )


@router.get(
    "/patches",
    response_model=List[PatchResponse],
    summary="List patches",
    description="Get all generated patches with optional filtering."
)
async def list_patches(
    incident_id: Optional[UUID] = Query(None, description="Filter by incident"),
):
    """
    List generated patches.
    """
    generator = get_patch_generator()
    
    if incident_id:
        patches = generator.get_patches_for_incident(incident_id)
    else:
        # Get all patches
        patches = []
        # Would need to add method to get all patches
    
    return [
        PatchResponse(
            id=p.id,
            incident_id=p.incident_id,
            file_path=p.file_path,
            description=p.description,
            confidence=p.confidence,
            fix_type=p.fix_type,
            diff=p.diff,
            status=p.status,
            sandbox_tested=p.sandbox_tested,
            sandbox_passed=p.sandbox_passed,
        )
        for p in patches
    ]


@router.get(
    "/patches/{patch_id}",
    response_model=PatchResponse,
    summary="Get patch details",
    description="Get detailed information about a specific patch."
)
async def get_patch(
    patch_id: UUID,
):
    """
    Get details of a specific patch.
    """
    generator = get_patch_generator()
    patch = generator.get_patch(patch_id)
    
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch {patch_id} not found"
        )
    
    return PatchResponse(
        id=patch.id,
        incident_id=patch.incident_id,
        file_path=patch.file_path,
        description=patch.description,
        confidence=patch.confidence,
        fix_type=patch.fix_type,
        diff=patch.diff,
        status=patch.status,
        sandbox_tested=patch.sandbox_tested,
        sandbox_passed=patch.sandbox_passed,
    )


@router.get(
    "/circuit-breaker/status",
    response_model=List[CircuitStatusResponse],
    summary="Get circuit breaker status",
    description="Get circuit breaker status for all endpoints."
)
async def get_circuit_status(
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
):
    """
    Get circuit breaker status.
    """
    circuit_breaker = get_circuit_breaker()
    
    if endpoint:
        status = circuit_breaker.get_circuit_status(endpoint)
        if status:
            return [CircuitStatusResponse(
                endpoint=status["endpoint"],
                state=status["state"],
                failure_count=status["failure_count"],
                success_count=status.get("success_count", 0),
            )]
        return []
    
    all_status = circuit_breaker.get_circuit_status()
    return [
        CircuitStatusResponse(
            endpoint=path,
            state=data["state"],
            failure_count=data["failure_count"],
            success_count=data.get("success_count", 0),
        )
        for path, data in all_status.items()
    ]


@router.get(
    "/circuit-breaker/metrics",
    response_model=List[MetricsResponse],
    summary="Get endpoint metrics",
    description="Get performance metrics for all endpoints."
)
async def get_endpoint_metrics(
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
):
    """
    Get endpoint performance metrics.
    """
    circuit_breaker = get_circuit_breaker()
    
    metrics = circuit_breaker.get_metrics(endpoint)
    
    if endpoint:
        if metrics:
            return [MetricsResponse(
                endpoint=metrics["endpoint"],
                total_requests=metrics["total_requests"],
                avg_response_time_ms=metrics["avg_response_time_ms"],
                p95_response_time_ms=metrics["p95_response_time_ms"],
                error_rate=metrics["error_rate"],
                slow_request_count=metrics["slow_request_count"],
            )]
        return []
    
    return [
        MetricsResponse(
            endpoint=path,
            total_requests=data["total_requests"],
            avg_response_time_ms=data["avg_response_time_ms"],
            p95_response_time_ms=data["p95_response_time_ms"],
            error_rate=data["error_rate"],
            slow_request_count=data["slow_request_count"],
        )
        for path, data in metrics.items()
    ]


@router.get(
    "/circuit-breaker/optimizations",
    summary="Get auto-optimizations",
    description="Get all automatically applied optimizations."
)
async def get_optimizations(
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
):
    """
    Get automatically applied optimizations.
    """
    circuit_breaker = get_circuit_breaker()
    
    return circuit_breaker.get_optimizations(endpoint)


@router.post(
    "/webhooks/sentry",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sentry webhook",
    description="Receive Sentry webhook for error events."
)
async def sentry_webhook(
    payload: Dict[str, Any],
    detector: ErrorDetector = Depends(get_error_detector),
):
    """
    Receive Sentry webhook events.
    
    This endpoint receives error events from Sentry and creates
    incidents for processing by the self-healing system.
    """
    try:
        incident = await detector.process_sentry_webhook(payload)
        
        if incident:
            return {
                "received": True,
                "incident_id": str(incident.id),
                "status": "processed",
            }
        
        return {
            "received": True,
            "status": "no_incident_created",
        }
        
    except Exception as e:
        logger.error(f"Sentry webhook processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )
