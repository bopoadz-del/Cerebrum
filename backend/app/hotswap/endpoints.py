"""
Hot Swap System API Endpoints

FastAPI endpoints for deploying, rolling back, and managing
capabilities at runtime.
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
from app.hotswap.dynamic_import import get_module_loader, get_module_registry
from app.hotswap.migration import get_migration_manager
from app.hotswap.rollback import RollbackReason, get_rollback_manager
from app.hotswap.route_registration import get_route_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hotswap", tags=["Hot Swap System"])


# ============== Request/Response Models ==============

class DeployRequest(BaseModel):
    """Request to deploy a capability."""
    create_snapshot: bool = True
    dry_run: bool = False


class DeployResponse(BaseModel):
    """Response from deployment."""
    success: bool
    capability_id: UUID
    deployed_version: str
    routes_added: List[str]
    database_migrated: bool
    snapshot_id: Optional[UUID]
    errors: List[str]
    warnings: List[str]


class RollbackRequest(BaseModel):
    """Request to rollback a capability."""
    reason: str = Field(..., description="Reason for rollback")
    snapshot_id: Optional[UUID] = None
    notify_users: bool = True


class RollbackResponse(BaseModel):
    """Response from rollback."""
    success: bool
    rollback_id: UUID
    from_version: str
    to_version: str
    code_rolled_back: bool
    database_rolled_back: bool
    routes_rolled_back: bool
    notified_users: List[str]
    errors: List[str]


class ActiveCapabilityResponse(BaseModel):
    """Response for active capability."""
    capability_id: UUID
    name: str
    version: str
    deployed_at: str
    routes: List[str]
    module_name: Optional[str]


class RouteInfoResponse(BaseModel):
    """Response for route info."""
    path: str
    methods: List[str]
    name: str
    capability_id: Optional[UUID]
    tags: List[str]


# ============== Endpoints ==============

@router.post(
    "/{capability_id}/deploy",
    response_model=DeployResponse,
    summary="Deploy a capability",
    description="Deploy a validated capability to production at runtime."
)
async def deploy_capability(
    capability_id: UUID,
    request: DeployRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Deploy a capability to production.
    
    This performs the following steps:
    1. Verify capability is validated
    2. Create pre-deployment snapshot
    3. Apply database migrations
    4. Load code module
    5. Register routes
    6. Update capability status
    """
    # Get capability
    crud = CapabilityCRUD(db)
    capability = await crud.get_by_id_with_relations(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found"
        )
    
    # Check status
    if capability.status != CapabilityStatus.VALIDATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot deploy capability in '{capability.status}' status. Must be VALIDATED."
        )
    
    # Get managers
    module_loader = get_module_loader()
    module_registry = get_module_registry()
    route_registry = get_route_registry()
    migration_manager = get_migration_manager()
    rollback_manager = get_rollback_manager(db)
    
    snapshot_id = None
    routes_added = []
    database_migrated = False
    errors = []
    warnings = []
    
    try:
        # 1. Create snapshot
        if request.create_snapshot:
            current_revision = await migration_manager.get_current_revision(db)
            snapshot = await rollback_manager.create_snapshot(capability, current_revision)
            snapshot_id = snapshot.id
        
        if request.dry_run:
            return DeployResponse(
                success=True,
                capability_id=capability_id,
                deployed_version=capability.version,
                routes_added=[],
                database_migrated=False,
                snapshot_id=snapshot_id,
                errors=[],
                warnings=["Dry run mode - no actual deployment"],
            )
        
        # 2. Apply database migration if present
        if capability.capability_type.value == "migration" and capability.code_content:
            migration_result = await migration_manager.generate_migration_from_code(
                capability.code_content,
                capability_id,
            )
            
            if migration_result.success:
                apply_result = await migration_manager.apply_migration(
                    migration_result.revision_id,
                    db,
                )
                database_migrated = apply_result.success
                
                if not apply_result.success:
                    errors.extend(apply_result.errors)
            else:
                errors.extend(migration_result.errors)
        
        # 3. Load code module
        if capability.code_content:
            module_name = f"capability_{capability.name}_{capability.version.replace('.', '_')}"
            
            import_result = module_loader.load_from_string(
                capability.code_content,
                module_name,
                capability_id,
            )
            
            if not import_result.success:
                errors.extend(import_result.errors)
                
                # Rollback on failure
                if snapshot_id:
                    await rollback_manager.rollback(
                        capability_id,
                        RollbackReason.DEPLOYMENT_FAILURE,
                        "deploy_endpoint",
                        snapshot_id,
                    )
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to load module: {import_result.errors}"
                )
            
            # Register capability module
            module_registry.register_capability(
                capability_id,
                module_name,
                {"exports": list(import_result.exports.keys())},
            )
        
        # 4. Register routes
        if capability.route_path:
            # For endpoints, register the router
            module_info = module_loader.get_capability_modules(capability_id)
            
            for mod_info in module_info:
                # Find router in module exports
                router_export = mod_info.exports.get("router")
                if router_export:
                    route_result = route_registry.register_router(
                        router_export["value"],
                        prefix=capability.route_path,
                        tags=[capability.name],
                        capability_id=capability_id,
                    )
                    
                    if route_result.success:
                        routes_added.append(capability.route_path)
                    else:
                        errors.extend(route_result.errors)
        
        # 5. Update capability status
        await crud.update_status(capability_id, CapabilityStatus.DEPLOYED)
        
        logger.info(f"Successfully deployed capability {capability_id}")
        
        return DeployResponse(
            success=len(errors) == 0,
            capability_id=capability_id,
            deployed_version=capability.version,
            routes_added=routes_added,
            database_migrated=database_migrated,
            snapshot_id=snapshot_id,
            errors=errors,
            warnings=warnings,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        
        # Attempt rollback
        if snapshot_id:
            await rollback_manager.rollback(
                capability_id,
                RollbackReason.DEPLOYMENT_FAILURE,
                "deploy_endpoint",
                snapshot_id,
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )


@router.post(
    "/{capability_id}/rollback",
    response_model=RollbackResponse,
    summary="Rollback a capability",
    description="Rollback a deployed capability to its previous state."
)
async def rollback_capability(
    capability_id: UUID,
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Rollback a deployed capability.
    
    This restores:
    - Code to previous version
    - Database to previous revision
    - Routes to previous state
    """
    # Get capability
    crud = CapabilityCRUD(db)
    capability = await crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found"
        )
    
    # Can only rollback deployed capabilities
    if capability.status != CapabilityStatus.DEPLOYED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot rollback capability in '{capability.status}' status"
        )
    
    # Get rollback manager
    rollback_manager = get_rollback_manager(db)
    
    # Map reason string to enum
    reason_map = {
        "deployment_failure": RollbackReason.DEPLOYMENT_FAILURE,
        "runtime_error": RollbackReason.RUNTIME_ERROR,
        "security_issue": RollbackReason.SECURITY_ISSUE,
        "performance_degradation": RollbackReason.PERFORMANCE_DEGRADATION,
        "user_request": RollbackReason.USER_REQUEST,
        "manual": RollbackReason.MANUAL,
    }
    
    reason = reason_map.get(request.reason.lower(), RollbackReason.MANUAL)
    
    try:
        result = await rollback_manager.rollback(
            capability_id=capability_id,
            reason=reason,
            triggered_by="api_endpoint",
            snapshot_id=request.snapshot_id,
            notify_users=request.notify_users,
        )
        
        return RollbackResponse(
            success=result.success,
            rollback_id=result.rollback_id,
            from_version=result.from_version,
            to_version=result.to_version,
            code_rolled_back=result.code_rolled_back,
            database_rolled_back=result.database_rolled_back,
            routes_rolled_back=result.routes_rolled_back,
            notified_users=result.notified_users,
            errors=result.errors,
        )
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )


@router.get(
    "/active",
    response_model=List[ActiveCapabilityResponse],
    summary="List active capabilities",
    description="Get all currently deployed and active capabilities."
)
async def list_active_capabilities(
    db: AsyncSession = Depends(get_db),
):
    """
    List all active (deployed) capabilities.
    """
    crud = CapabilityCRUD(db)
    capabilities = await crud.get_active_capabilities()
    
    module_registry = get_module_registry()
    route_registry = get_route_registry()
    
    result = []
    for cap in capabilities:
        # Get routes for capability
        routes = route_registry.get_capability_routes(cap.id)
        route_paths = [r.path for r in routes]
        
        # Get module info
        module_name = module_registry.get_capability_module(cap.id)
        
        result.append(ActiveCapabilityResponse(
            capability_id=cap.id,
            name=cap.name,
            version=cap.version,
            deployed_at=cap.deployed_at.isoformat() if cap.deployed_at else "",
            routes=route_paths,
            module_name=module_name,
        ))
    
    return result


@router.get(
    "/routes",
    response_model=List[RouteInfoResponse],
    summary="List all routes",
    description="Get all dynamically registered routes."
)
async def list_routes(
    capability_id: Optional[UUID] = Query(None, description="Filter by capability"),
):
    """
    List all dynamically registered routes.
    """
    route_registry = get_route_registry()
    
    if capability_id:
        routes = route_registry.get_capability_routes(capability_id)
    else:
        routes = route_registry.get_routes()
    
    return [
        RouteInfoResponse(
            path=r.path,
            methods=r.methods,
            name=r.name,
            capability_id=r.capability_id,
            tags=r.tags,
        )
        for r in routes
    ]


@router.get(
    "/{capability_id}/snapshots",
    summary="Get capability snapshots",
    description="Get all snapshots for a capability."
)
async def get_snapshots(
    capability_id: UUID,
):
    """
    Get all rollback snapshots for a capability.
    """
    rollback_manager = get_rollback_manager()
    snapshots = rollback_manager.get_snapshots(capability_id)
    
    return [
        {
            "id": str(s.id),
            "version": s.version,
            "created_at": s.created_at.isoformat(),
            "database_revision": s.database_revision,
        }
        for s in sorted(snapshots, key=lambda x: x.created_at, reverse=True)
    ]


@router.get(
    "/{capability_id}/history",
    summary="Get rollback history",
    description="Get rollback history for a capability."
)
async def get_rollback_history(
    capability_id: UUID,
):
    """
    Get rollback history for a capability.
    """
    rollback_manager = get_rollback_manager()
    history = rollback_manager.get_history(capability_id)
    
    return [
        {
            "id": str(h.id),
            "rollback_id": str(h.rollback_id),
            "triggered_by": h.triggered_by,
            "reason": h.reason.value,
            "result": h.result,
            "timestamp": h.timestamp.isoformat(),
        }
        for h in sorted(history, key=lambda x: x.timestamp, reverse=True)
    ]


@router.post(
    "/{capability_id}/undeploy",
    summary="Undeploy a capability",
    description="Remove a deployed capability from production without rollback."
)
async def undeploy_capability(
    capability_id: UUID,
    reason: str = Query(..., description="Reason for undeployment"),
    db: AsyncSession = Depends(get_db),
):
    """
    Undeploy a capability without rolling back.
    
    This removes the capability from active service but doesn't
    restore previous state.
    """
    crud = CapabilityCRUD(db)
    capability = await crud.get_by_id(capability_id)
    
    if not capability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capability {capability_id} not found"
        )
    
    if capability.status != CapabilityStatus.DEPLOYED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Capability is not deployed (status: {capability.status})"
        )
    
    try:
        # Unregister routes
        route_registry = get_route_registry()
        route_registry.unregister_capability_routes(capability_id)
        
        # Unregister module
        module_registry = get_module_registry()
        module_registry.unregister_capability(capability_id)
        
        # Update status
        await crud.update_status(capability_id, CapabilityStatus.VALIDATED, reason=reason)
        
        return {
            "success": True,
            "capability_id": capability_id,
            "message": "Capability undeployed successfully",
        }
        
    except Exception as e:
        logger.error(f"Undeployment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Undeployment failed: {str(e)}"
        )
