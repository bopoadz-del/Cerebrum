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
from ..database import get_db  # Assumed to exist

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
            detail=f"Capability {data.name} v{data.version} already exists"
        )
    
    db_capability = crud.create(data)
    return CapabilityResponse(
        success=True,
        data=Capability.model_validate(db_capability),
        message="Capability created successfully"
    )


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
    crud = CapabilityCRUD(db)
    capabilities = crud.list_capabilities(
        status=status,
        capability_type=capability_type,
        author=author,
        skip=skip,
        limit=limit
    )
    
    total = db.query(crud.get_by_id).count()  # Simplified
    
    return CapabilityListResponse(
        success=True,
        data=[Capability.model_validate(c) for c in capabilities],
        total=len(capabilities)
    )


@router.get("/{capability_id}", response_model=CapabilityResponse)
async def get_capability(
    capability_id: str,
    db: Session = Depends(get_db)
):
    """Get a capability by ID."""
    crud = CapabilityCRUD(db)
    capability = crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
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
        raise HTTPException(status_code=404, detail="Capability not found")
    
    # Prevent updates to deployed capabilities
    if existing.status == CapabilityStatus.DEPLOYED:
        raise HTTPException(
            status_code=400, 
            detail="Cannot update deployed capability. Create new version instead."
        )
    
    updated = crud.update(capability_id, data)
    return CapabilityResponse(
        success=True,
        data=Capability.model_validate(updated),
        message="Capability updated successfully"
    )


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
        raise HTTPException(status_code=404, detail="Capability not found")
    
    # Check for dependents
    dependents = crud.get_dependents(capability_id)
    deployed_dependents = [d for d in dependents if d.status == CapabilityStatus.DEPLOYED]
    
    if deployed_dependents:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: has {len(deployed_dependents)} deployed dependents"
        )
    
    if hard:
        crud.hard_delete(capability_id)
    else:
        crud.delete(capability_id)
    
    return {"success": True, "message": "Capability deleted"}


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
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if capability.status not in [CapabilityStatus.VALIDATED, CapabilityStatus.ROLLED_BACK]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot deploy capability with status: {capability.status}"
        )
    
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


@router.post("/{capability_id}/rollback", response_model=CapabilityResponse)
async def rollback_capability(
    capability_id: str,
    db: Session = Depends(get_db)
):
    """Rollback to previous version."""
    crud = CapabilityCRUD(db)
    
    capability = crud.get_by_id(capability_id)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if not capability.rollback_available or not capability.previous_version_id:
        raise HTTPException(status_code=400, detail="No rollback point available")
    
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


@router.get("/{capability_id}/dependencies", response_model=DependencyResolutionResponse)
async def get_dependencies(
    capability_id: str,
    db: Session = Depends(get_db)
):
    """Get resolved dependencies for a capability."""
    crud = CapabilityCRUD(db)
    
    capability = crud.get_by_id(capability_id)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    result = crud.resolve_dependencies(capability_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
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
        raise HTTPException(status_code=404, detail="Capability not found")
    
    dependents = crud.get_dependents(capability_id)
    
    return {
        "success": True,
        "capability_id": capability_id,
        "dependents": [Capability.model_validate(d) for d in dependents]
    }


@router.get("/stats/overview", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get capability statistics."""
    crud = CapabilityCRUD(db)
    stats = crud.get_statistics()
    
    return StatisticsResponse(success=True, statistics=stats)


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
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if capability.status != CapabilityStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit capability with status: {capability.status}"
        )
    
    # Update status to pending validation
    crud.update_status(capability_id, CapabilityStatus.PENDING_VALIDATION)
    
    # Trigger validation pipeline (would be async task)
    # background_tasks.add_task(run_validation_pipeline, capability_id)
    
    return {
        "success": True,
        "message": "Capability submitted for validation",
        "capability_id": capability_id
    }
