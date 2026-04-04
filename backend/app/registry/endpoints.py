"""
Capability Registry Endpoints

FastAPI endpoints for capability lifecycle management.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .models import Capability, CapabilityCreate, CapabilityUpdate, CapabilityStatus, DependencyGraph
from .crud import CapabilityCRUD
from app.errors import format_error_response, get_user_friendly_error

try:
    from app.db.session import get_db
except ImportError:
    # Fallback - create stub
    from typing import Generator
    def get_db() -> Generator:
        yield None

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


# ============ Response Models ============

class CapabilityResponse(BaseModel):
    success: bool
    data: Optional[Capability] = None
    message: str = ""


class CapabilityListResponse(BaseModel):
    success: bool
    data: List[Capability]
    total: int


class DependencyResolutionResponse(BaseModel):
    success: bool
    capability_id: str
    resolved_order: List[str]
    unresolved: List[str]
    circular_dependencies: List[List[str]]
    install_order: List[str]


class StatisticsResponse(BaseModel):
    success: bool
    statistics: dict


# ============ Endpoints ============

@router.post("", response_model=CapabilityResponse)
async def create_capability(
    data: CapabilityCreate,
    db: Session = Depends(get_db)
):
    """Create a new capability."""
    crud = CapabilityCRUD(db)
    
    # Check if name already exists
    existing = crud.get_latest_by_name(data.name)
    if existing and existing.version == data.version:
        raise HTTPException(
            status_code=400, 
            detail={
                "message": f"That capability already exists.",
                "suggestion": f"'{data.name}' version {data.version} already exists. Try creating a new version or updating the existing one.",
                "category": "validation",
                "retry_allowed": True,
            }
        )
    
    try:
        db_capability = crud.create(data)
        return CapabilityResponse(
            success=True,
            data=Capability.model_validate(db_capability),
            message="Capability created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="creating the capability")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.get("", response_model=CapabilityListResponse)
async def list_capabilities(
    status: Optional[CapabilityStatus] = None,
    capability_type: Optional[str] = None,
    author: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List capabilities with optional filters."""
    try:
        crud = CapabilityCRUD(db)
        capabilities = crud.list_capabilities(
            status=status,
            capability_type=capability_type,
            author=author,
            skip=skip,
            limit=limit
        )
        
        return CapabilityListResponse(
            success=True,
            data=[Capability.model_validate(c) for c in capabilities],
            total=len(capabilities)
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="listing capabilities")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.get("/{capability_id}", response_model=CapabilityResponse)
async def get_capability(
    capability_id: str,
    db: Session = Depends(get_db)
):
    """Get a capability by ID."""
    crud = CapabilityCRUD(db)
    capability = crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that capability.",
                "suggestion": "The capability may have been deleted or the ID is incorrect. Check the capabilities list.",
                "category": "not_found",
                "retry_allowed": True,
                "actions": [{"label": "View All Capabilities", "action": "navigate:/api/v1/capabilities"}],
            }
        )
    
    return CapabilityResponse(
        success=True,
        data=Capability.model_validate(capability)
    )


@router.put("/{capability_id}", response_model=CapabilityResponse)
async def update_capability(
    capability_id: str,
    data: CapabilityUpdate,
    db: Session = Depends(get_db)
):
    """Update a capability."""
    crud = CapabilityCRUD(db)
    
    existing = crud.get_by_id(capability_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that capability.",
                "suggestion": "The capability may have been deleted or the ID is incorrect.",
                "category": "not_found",
                "retry_allowed": True,
            }
        )
    
    # Prevent updates to deployed capabilities
    if existing.status == CapabilityStatus.DEPLOYED:
        raise HTTPException(
            status_code=400, 
            detail={
                "message": "Cannot update a deployed capability.",
                "suggestion": "Deployed capabilities can't be modified. Create a new version instead to make your changes.",
                "category": "validation",
                "retry_allowed": True,
                "actions": [{"label": "Create New Version", "action": "navigate:/api/v1/capabilities/create"}],
            }
        )
    
    try:
        updated = crud.update(capability_id, data)
        return CapabilityResponse(
            success=True,
            data=Capability.model_validate(updated),
            message="Capability updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="updating the capability")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.delete("/{capability_id}")
async def delete_capability(
    capability_id: str,
    hard: bool = Query(False, description="Permanently delete"),
    db: Session = Depends(get_db)
):
    """Delete (or deprecate) a capability."""
    crud = CapabilityCRUD(db)
    
    existing = crud.get_by_id(capability_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that capability.",
                "suggestion": "The capability may have already been deleted or the ID is incorrect.",
                "category": "not_found",
                "retry_allowed": True,
            }
        )
    
    # Check for dependents
    dependents = crud.get_dependents(capability_id)
    deployed_dependents = [d for d in dependents if d.status == CapabilityStatus.DEPLOYED]
    
    if deployed_dependents:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Cannot delete: {len(deployed_dependents)} feature{'s' if len(deployed_dependents) > 1 else ''} depend on this.",
                "suggestion": "Other deployed capabilities rely on this one. You'll need to update or remove those dependencies first.",
                "category": "validation",
                "retry_allowed": True,
                "actions": [{"label": "View Dependents", "action": f"navigate:/api/v1/capabilities/{capability_id}/dependents"}],
            }
        )
    
    try:
        if hard:
            crud.hard_delete(capability_id)
        else:
            crud.delete(capability_id)
        
        return {"success": True, "message": "Capability deleted"}
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="deleting the capability")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/{capability_id}/deploy", response_model=CapabilityResponse)
async def deploy_capability(
    capability_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Deploy a capability."""
    crud = CapabilityCRUD(db)
    
    capability = crud.get_by_id(capability_id)
    if not capability:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that capability.",
                "suggestion": "The capability may have been deleted or the ID is incorrect.",
                "category": "not_found",
                "retry_allowed": True,
            }
        )
    
    if capability.status not in [CapabilityStatus.VALIDATED, CapabilityStatus.ROLLED_BACK]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This capability isn't ready to deploy.",
                "suggestion": f"The capability must be validated first before it can be deployed. Current status: {capability.status}.",
                "category": "validation",
                "retry_allowed": True,
                "actions": [{"label": "Validate First", "action": f"navigate:/api/v1/capabilities/{capability_id}/validate"}],
            }
        )
    
    try:
        # Set rollback point if there's a previous deployed version
        previous = crud.get_latest_by_name(capability.name)
        if previous and previous.id != capability_id and previous.status == CapabilityStatus.DEPLOYED:
            crud.set_rollback_point(capability_id, previous.id)
        
        # Update status
        deployed = crud.update_status(capability_id, CapabilityStatus.DEPLOYED)
        
        return CapabilityResponse(
            success=True,
            data=Capability.model_validate(deployed),
            message="Capability deployed successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="deploying the capability")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/{capability_id}/rollback", response_model=CapabilityResponse)
async def rollback_capability(
    capability_id: str,
    db: Session = Depends(get_db)
):
    """Rollback to previous version."""
    crud = CapabilityCRUD(db)
    
    capability = crud.get_by_id(capability_id)
    if not capability:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that capability.",
                "suggestion": "The capability may have been deleted or the ID is incorrect.",
                "category": "not_found",
                "retry_allowed": True,
            }
        )
    
    if not capability.rollback_available or not capability.previous_version_id:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No rollback point available.",
                "suggestion": "This capability doesn't have a previous version to roll back to. Rollback is only available after deploying an update.",
                "category": "validation",
                "retry_allowed": False,
            }
        )
    
    try:
        # Mark current as rolled back
        crud.update_status(capability_id, CapabilityStatus.ROLLED_BACK)
        
        # Deploy previous version
        previous = crud.get_by_id(capability.previous_version_id)
        if previous:
            crud.update_status(previous.id, CapabilityStatus.DEPLOYED)
        
        return CapabilityResponse(
            success=True,
            data=Capability.model_validate(previous) if previous else None,
            message="Rolled back to previous version"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="rolling back the capability")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.get("/{capability_id}/dependencies", response_model=DependencyResolutionResponse)
async def get_dependencies(
    capability_id: str,
    db: Session = Depends(get_db)
):
    """Get resolved dependencies for a capability."""
    crud = CapabilityCRUD(db)
    
    capability = crud.get_by_id(capability_id)
    if not capability:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that capability.",
                "suggestion": "The capability may have been deleted or the ID is incorrect.",
                "category": "not_found",
                "retry_allowed": True,
            }
        )
    
    result = crud.resolve_dependencies(capability_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Could not resolve dependencies.",
                "suggestion": result.get("error", "There was an issue resolving the dependency tree. Please check your dependency declarations."),
                "category": "validation",
                "retry_allowed": True,
            }
        )
    
    return DependencyResolutionResponse(
        success=True,
        capability_id=capability_id,
        resolved_order=result["resolved_order"],
        unresolved=result["unresolved"],
        circular_dependencies=result["circular_dependencies"],
        install_order=result["install_order"]
    )


@router.get("/{capability_id}/dependents")
async def get_dependents(
    capability_id: str,
    db: Session = Depends(get_db)
):
    """Get capabilities that depend on this one."""
    crud = CapabilityCRUD(db)
    
    capability = crud.get_by_id(capability_id)
    if not capability:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that capability.",
                "suggestion": "The capability may have been deleted or the ID is incorrect.",
                "category": "not_found",
                "retry_allowed": True,
            }
        )
    
    try:
        dependents = crud.get_dependents(capability_id)
        
        return {
            "success": True,
            "capability_id": capability_id,
            "dependents": [Capability.model_validate(d) for d in dependents]
        }
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="getting dependents")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.get("/stats/overview", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get capability statistics."""
    try:
        crud = CapabilityCRUD(db)
        stats = crud.get_statistics()
        
        return StatisticsResponse(success=True, statistics=stats)
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="getting statistics")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/{capability_id}/validate")
async def submit_for_validation(
    capability_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Submit capability for validation."""
    crud = CapabilityCRUD(db)
    
    capability = crud.get_by_id(capability_id)
    if not capability:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that capability.",
                "suggestion": "The capability may have been deleted or the ID is incorrect.",
                "category": "not_found",
                "retry_allowed": True,
            }
        )
    
    if capability.status != CapabilityStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This capability can't be submitted for validation.",
                "suggestion": f"Only capabilities in DRAFT status can be submitted. Current status: {capability.status}.",
                "category": "validation",
                "retry_allowed": False,
            }
        )
    
    try:
        # Update status to pending validation
        crud.update_status(capability_id, CapabilityStatus.PENDING_VALIDATION)
        
        # Trigger validation pipeline (would be async task)
        # background_tasks.add_task(run_validation_pipeline, capability_id)
        
        return {
            "success": True,
            "message": "Capability submitted for validation",
            "capability_id": capability_id
        }
    except HTTPException:
        raise
    except Exception as e:
        error_response = format_error_response(e, operation="submitting for validation")
        raise HTTPException(status_code=500, detail=error_response["error"])
