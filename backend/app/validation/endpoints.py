"""
Validation Pipeline API Endpoints

FastAPI endpoints for running and monitoring code validation.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.registry.crud import CapabilityCRUD
from app.registry.models import CapabilityStatus
from app.validation.pipeline import (
    ValidationPipeline,
    ValidationPipelineConfig,
    ValidationStageStatus,
    get_validation_pipeline,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validation", tags=["Validation Pipeline"])


# ============== Request/Response Models ==============

class RunValidationRequest(BaseModel):
    """Request to run validation."""
    run_syntax_check: bool = True
    run_security_scan: bool = True
    run_sandbox_test: bool = True
    run_integration_tests: bool = True
    require_human_review: bool = True
    sandbox_timeout_seconds: int = 300
    sandbox_memory_limit_mb: int = 512
    test_timeout_seconds: int = 60


class ValidationStageResponse(BaseModel):
    """Response for a validation stage."""
    stage: str
    status: str
    duration_ms: float
    details: Dict[str, Any]
    errors: List[str]
    warnings: List[str]


class ValidationReportResponse(BaseModel):
    """Response for validation report."""
    id: UUID
    capability_id: UUID
    overall_status: str
    stages: List[ValidationStageResponse]
    total_stages: int
    passed_stages: int
    failed_stages: int
    skipped_stages: int
    duration_ms: float
    started_at: str
    completed_at: Optional[str]
    metadata: Dict[str, Any]


class ValidationStatusResponse(BaseModel):
    """Response for validation status."""
    capability_id: UUID
    status: str
    current_stage: Optional[str]
    progress_percent: float
    estimated_completion: Optional[str]


# ============== Endpoints ==============

@router.post(
    "/{capability_id}/run",
    response_model=ValidationReportResponse,
    summary="Run validation pipeline",
    description="Run the complete validation pipeline for a capability."
)
async def run_validation(
    capability_id: UUID,
    request: RunValidationRequest,
    db: AsyncSession = Depends(get_db),
    pipeline: ValidationPipeline = Depends(get_validation_pipeline),
):
    """
    Run the validation pipeline for a capability.
    
    This runs all validation stages:
    1. Syntax Check
    2. Security Scan
    3. Sandbox Test
    4. Integration Test
    5. Human Review (if enabled)
    
    The capability must be in DRAFT or VALIDATING status.
    """
    # Get capability
    crud = CapabilityCRUD(db)
    capability = await crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found"
        )
    
    # Check status
    if capability.status not in [CapabilityStatus.DRAFT, CapabilityStatus.VALIDATING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot validate capability in '{capability.status}' status"
        )
    
    # Update status to validating
    if capability.status == CapabilityStatus.DRAFT:
        await crud.update_status(capability_id, CapabilityStatus.VALIDATING)
    
    # Create pipeline config
    config = ValidationPipelineConfig(
        run_syntax_check=request.run_syntax_check,
        run_security_scan=request.run_security_scan,
        run_sandbox_test=request.run_sandbox_test,
        run_integration_tests=request.run_integration_tests,
        require_human_review=request.require_human_review,
        sandbox_timeout_seconds=request.sandbox_timeout_seconds,
        sandbox_memory_limit_mb=request.sandbox_memory_limit_mb,
        test_timeout_seconds=request.test_timeout_seconds,
    )
    
    try:
        # Run validation
        report = await pipeline.run_validation(capability, config)
        
        # Update capability status based on results
        if report.overall_status == ValidationStageStatus.PASSED:
            await crud.update_status(capability_id, CapabilityStatus.VALIDATED)
        elif report.overall_status == ValidationStageStatus.FAILED:
            await crud.update_status(capability_id, CapabilityStatus.FAILED)
        
        # Convert to response
        return _report_to_response(report)
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get(
    "/{capability_id}/status",
    response_model=ValidationStatusResponse,
    summary="Get validation status",
    description="Get the current validation status for a capability."
)
async def get_validation_status(
    capability_id: UUID,
    db: AsyncSession = Depends(get_db),
    pipeline: ValidationPipeline = Depends(get_validation_pipeline),
):
    """
    Get the validation status for a capability.
    
    Returns the current status, progress, and estimated completion time.
    """
    # Get capability
    crud = CapabilityCRUD(db)
    capability = await crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found"
        )
    
    # Get latest report
    reports = pipeline.get_reports_for_capability(capability_id)
    
    if not reports:
        return ValidationStatusResponse(
            capability_id=capability_id,
            status=capability.status.value,
            current_stage=None,
            progress_percent=0.0,
            estimated_completion=None,
        )
    
    latest_report = max(reports, key=lambda r: r.started_at)
    
    # Calculate progress
    total_stages = latest_report.total_stages
    completed_stages = latest_report.passed_stages + latest_report.failed_stages + latest_report.skipped_stages
    progress = (completed_stages / total_stages * 100) if total_stages > 0 else 0
    
    # Find current stage
    current_stage = None
    for stage_name, stage_result in latest_report.stages.items():
        if stage_result.status == ValidationStageStatus.RUNNING:
            current_stage = stage_name.value
            break
    
    return ValidationStatusResponse(
        capability_id=capability_id,
        status=latest_report.overall_status.value,
        current_stage=current_stage,
        progress_percent=progress,
        estimated_completion=None,  # Could calculate based on average stage duration
    )


@router.get(
    "/{capability_id}/report",
    response_model=ValidationReportResponse,
    summary="Get validation report",
    description="Get the detailed validation report for a capability."
)
async def get_validation_report(
    capability_id: UUID,
    report_id: Optional[UUID] = Query(None, description="Specific report ID (latest if not provided)"),
    db: AsyncSession = Depends(get_db),
    pipeline: ValidationPipeline = Depends(get_validation_pipeline),
):
    """
    Get the validation report for a capability.
    
    Returns detailed results for all validation stages including:
    - Syntax check results
    - Security scan findings
    - Sandbox test output
    - Integration test results
    - Human review status
    """
    # Get capability
    crud = CapabilityCRUD(db)
    capability = await crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found"
        )
    
    # Get report
    if report_id:
        report = pipeline.get_report(report_id)
    else:
        reports = pipeline.get_reports_for_capability(capability_id)
        report = max(reports, key=lambda r: r.started_at) if reports else None
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No validation report found for capability {capability_id}"
        )
    
    return _report_to_response(report)


@router.get(
    "/{capability_id}/reports",
    response_model=List[ValidationReportResponse],
    summary="Get all validation reports",
    description="Get all validation reports for a capability."
)
async def get_all_validation_reports(
    capability_id: UUID,
    db: AsyncSession = Depends(get_db),
    pipeline: ValidationPipeline = Depends(get_validation_pipeline),
):
    """
    Get all validation reports for a capability.
    
    Useful for tracking validation history and improvements over time.
    """
    # Get capability
    crud = CapabilityCRUD(db)
    capability = await crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found"
        )
    
    reports = pipeline.get_reports_for_capability(capability_id)
    
    return [_report_to_response(r) for r in sorted(reports, key=lambda r: r.started_at, reverse=True)]


@router.post(
    "/{capability_id}/retry",
    response_model=ValidationReportResponse,
    summary="Retry failed validation",
    description="Retry validation for a capability that previously failed."
)
async def retry_validation(
    capability_id: UUID,
    request: RunValidationRequest,
    db: AsyncSession = Depends(get_db),
    pipeline: ValidationPipeline = Depends(get_validation_pipeline),
):
    """
    Retry validation for a capability.
    
    This resets the capability to VALIDATING status and re-runs all
    validation stages.
    """
    # Get capability
    crud = CapabilityCRUD(db)
    capability = await crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found"
        )
    
    # Can only retry failed capabilities
    if capability.status != CapabilityStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry validation for capability in '{capability.status}' status"
        )
    
    # Reset to validating
    await crud.update_status(capability_id, CapabilityStatus.VALIDATING, reason="Retry validation")
    
    # Run validation
    config = ValidationPipelineConfig(
        run_syntax_check=request.run_syntax_check,
        run_security_scan=request.run_security_scan,
        run_sandbox_test=request.run_sandbox_test,
        run_integration_tests=request.run_integration_tests,
        require_human_review=request.require_human_review,
    )
    
    try:
        report = await pipeline.run_validation(capability, config)
        
        # Update status
        if report.overall_status == ValidationStageStatus.PASSED:
            await crud.update_status(capability_id, CapabilityStatus.VALIDATED)
        elif report.overall_status == ValidationStageStatus.FAILED:
            await crud.update_status(capability_id, CapabilityStatus.FAILED)
        
        return _report_to_response(report)
        
    except Exception as e:
        logger.error(f"Validation retry failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation retry failed: {str(e)}"
        )


@router.get(
    "/reports/{report_id}/security",
    summary="Get security scan details",
    description="Get detailed security scan results from a validation report."
)
async def get_security_details(
    report_id: UUID,
    pipeline: ValidationPipeline = Depends(get_validation_pipeline),
):
    """
    Get detailed security scan results.
    
    Returns all security issues found including:
    - Issue severity and confidence
    - Affected lines of code
    - Remediation suggestions
    """
    report = pipeline.get_report(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found"
        )
    
    security_stage = report.stages.get("security_scan")
    
    if not security_stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No security scan in this report"
        )
    
    return {
        "status": security_stage.status.value,
        "issues": security_stage.details.get("issues", []),
        "summary": security_stage.details,
        "errors": security_stage.errors,
        "warnings": security_stage.warnings,
    }


@router.get(
    "/reports/{report_id}/sandbox",
    summary="Get sandbox test details",
    description="Get detailed sandbox test results from a validation report."
)
async def get_sandbox_details(
    report_id: UUID,
    pipeline: ValidationPipeline = Depends(get_validation_pipeline),
):
    """
    Get detailed sandbox test results.
    
    Returns sandbox execution output including:
    - Execution logs
    - Resource usage
    - Security violations
    """
    report = pipeline.get_report(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found"
        )
    
    sandbox_stage = report.stages.get("sandbox_test")
    
    if not sandbox_stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sandbox test in this report"
        )
    
    return {
        "status": sandbox_stage.status.value,
        "details": sandbox_stage.details,
        "errors": sandbox_stage.errors,
        "output": report.sandbox_output,
    }


# ============== Helper Functions ==============

def _report_to_response(report) -> ValidationReportResponse:
    """Convert ValidationReport to response model."""
    stages = []
    for stage_name, stage_result in report.stages.items():
        stages.append(ValidationStageResponse(
            stage=stage_name.value,
            status=stage_result.status.value,
            duration_ms=stage_result.duration_ms,
            details=stage_result.details,
            errors=stage_result.errors,
            warnings=stage_result.warnings,
        ))
    
    return ValidationReportResponse(
        id=report.id,
        capability_id=report.capability_id,
        overall_status=report.overall_status.value,
        stages=stages,
        total_stages=report.total_stages,
        passed_stages=report.passed_stages,
        failed_stages=report.failed_stages,
        skipped_stages=report.skipped_stages,
        duration_ms=report.duration_ms,
        started_at=report.started_at.isoformat(),
        completed_at=report.completed_at.isoformat() if report.completed_at else None,
        metadata=report.metadata,
    )
