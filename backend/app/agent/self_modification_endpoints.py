"""
Self-Modification Engine API Endpoints

Enables programmatic access to self-modification capabilities.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging

from app.agent.self_modification import (
    get_modification_engine, SelfModificationEngine,
    ModificationType, ModificationStatus
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ Request/Response Models ============

class CreateLayerRequest(BaseModel):
    name: str = Field(..., description="Layer name (e.g., 'energy', 'compliance')")
    description: str = Field(..., description="Short description")
    purpose: str = Field(..., description="What this layer does")
    dependencies: List[str] = Field(default_factory=list, description="Required layers")
    tools: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tool specifications"
    )
    auto_apply: bool = Field(default=False, description="Skip approval (dangerous)")


class ToolSpec(BaseModel):
    name: str
    description: str
    params: List[Dict[str, Any]] = Field(default_factory=list)


class ModifyCodeRequest(BaseModel):
    file_path: str = Field(..., description="Path relative to repo root")
    original_pattern: str = Field(..., description="Text to find")
    replacement: str = Field(..., description="Text to replace with")
    description: str = Field(..., description="What this change does")


class RefactorRequest(BaseModel):
    file_path: str = Field(..., description="File to refactor")
    target: str = Field(..., description="What to refactor (function/class)")
    improvement: str = Field(..., description="What improvement to make")


class ApprovalRequest(BaseModel):
    approver: str = Field(default="user", description="Who approved")


class ModificationResponse(BaseModel):
    request_id: str
    status: str
    type: str
    description: str
    timestamp: str
    changes_count: int
    approved_by: Optional[str] = None
    applied_at: Optional[str] = None


class ModificationStatusResponse(BaseModel):
    request_id: str
    status: str
    description: str
    changes: List[Dict[str, Any]]
    test_results: Optional[Dict] = None
    metadata: Dict[str, Any]


# ============ LAYER MANAGEMENT ============

@router.post("/layers/create", response_model=ModificationResponse)
async def create_layer(request: CreateLayerRequest):
    """
    Create a new architectural layer.
    
    The agent will:
    1. Generate the layer file with tools
    2. Run safety checks
    3. Queue for approval (or auto-apply if requested)
    
    Example:
    ```json
    {
      "name": "energy",
      "description": "Energy calculations and solar analysis",
      "purpose": "Handle renewable energy calculations",
      "tools": [
        {
          "name": "calculate_solar_roi",
          "description": "Calculate solar panel ROI",
          "params": [
            {"name": "panel_capacity", "type": "float", "default": 5.0}
          ]
        }
      ]
    }
    ```
    """
    try:
        engine = get_modification_engine()
        
        spec = {
            "name": request.name,
            "description": request.description,
            "purpose": request.purpose,
            "dependencies": request.dependencies,
            "tools": request.tools
        }
        
        mod_request = engine.request_create_layer(spec)
        
        return ModificationResponse(
            request_id=mod_request.id,
            status=mod_request.status.value,
            type=mod_request.type.value,
            description=mod_request.description,
            timestamp=mod_request.timestamp,
            changes_count=len(mod_request.changes),
            approved_by=mod_request.approved_by,
            applied_at=mod_request.applied_at
        )
    except Exception as e:
        logger.error(f"Layer creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layers/pending")
async def list_pending_layers():
    """List all pending layer creation requests."""
    try:
        engine = get_modification_engine()
        pending = engine.get_pending_requests()
        
        return {
            "count": len(pending),
            "requests": [
                {
                    "id": r.id,
                    "type": r.type.value,
                    "description": r.description,
                    "timestamp": r.timestamp,
                    "metadata": r.metadata
                }
                for r in pending
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ CODE MODIFICATION ============

@router.post("/code/modify", response_model=ModificationResponse)
async def modify_code(request: ModifyCodeRequest):
    """
    Request modification of existing code.
    
    Uses string replacement — finds `original_pattern` and replaces with `replacement`.
    
    Safety checks are run before the request is queued.
    """
    try:
        engine = get_modification_engine()
        
        mod_request = engine.request_modify_code(
            file_path=request.file_path,
            original_pattern=request.original_pattern,
            replacement=request.replacement,
            description=request.description
        )
        
        return ModificationResponse(
            request_id=mod_request.id,
            status=mod_request.status.value,
            type=mod_request.type.value,
            description=mod_request.description,
            timestamp=mod_request.timestamp,
            changes_count=len(mod_request.changes)
        )
    except Exception as e:
        logger.error(f"Code modification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code/refactor", response_model=ModificationResponse)
async def request_refactor(request: RefactorRequest):
    """
    Request AI-powered refactoring.
    
    This creates a refactoring task. In full implementation,
    the LLM would analyze the code and suggest improvements.
    """
    try:
        engine = get_modification_engine()
        
        mod_request = engine.request_refactor(
            file_path=request.file_path,
            target=request.target,
            improvement=request.improvement
        )
        
        return ModificationResponse(
            request_id=mod_request.id,
            status=mod_request.status.value,
            type=mod_request.type.value,
            description=mod_request.description,
            timestamp=mod_request.timestamp,
            changes_count=len(mod_request.changes)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ APPROVAL WORKFLOW ============

@router.post("/modifications/{request_id}/approve")
async def approve_modification(request_id: str, approval: ApprovalRequest):
    """Approve a pending modification."""
    try:
        engine = get_modification_engine()
        
        success = engine.approve_request(request_id, approval.approver)
        if not success:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return {"success": True, "request_id": request_id, "approved_by": approval.approver}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modifications/{request_id}/reject")
async def reject_modification(request_id: str, reason: str = "Rejected by user"):
    """Reject a pending modification."""
    try:
        engine = get_modification_engine()
        
        success = engine.reject_request(request_id, reason)
        if not success:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return {"success": True, "request_id": request_id, "reason": reason}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modifications/{request_id}/apply")
async def apply_modification(request_id: str, background_tasks: BackgroundTasks):
    """
    Apply an approved modification.
    
    Steps:
    1. Create git checkpoint
    2. Apply changes
    3. Validate code
    4. Commit if successful
    5. Rollback if failed
    """
    try:
        engine = get_modification_engine()
        
        result = engine.apply_modification(request_id)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Modification failed",
                    "result": result
                }
            )
        
        return {
            "success": True,
            "request_id": request_id,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modifications/{request_id}/rollback")
async def rollback_modification(request_id: str):
    """Rollback a previously applied modification."""
    try:
        engine = get_modification_engine()
        
        success = engine.rollback_modification(request_id)
        if not success:
            raise HTTPException(status_code=400, detail="Rollback failed or not applicable")
        
        return {"success": True, "request_id": request_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ STATUS & MONITORING ============

@router.get("/status")
async def get_modification_status():
    """Get self-modification engine status."""
    try:
        engine = get_modification_engine()
        return engine.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modifications/{request_id}")
async def get_modification_details(request_id: str):
    """Get detailed information about a modification request."""
    try:
        engine = get_modification_engine()
        details = engine.get_request_details(request_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_modification_history(limit: int = 20):
    """Get history of all modifications."""
    try:
        engine = get_modification_engine()
        return {
            "count": len(engine.history),
            "history": engine.history[-limit:]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ SAFETY & VALIDATION ============

@router.post("/validate")
async def validate_code(code: str):
    """
    Validate code for safety issues.
    
    Checks for:
    - Syntax errors
    - Dangerous patterns (eval, exec, os.system)
    - Suspicious imports
    """
    from app.agent.self_modification import CodeSafetyChecker
    
    checker = CodeSafetyChecker()
    is_safe, warnings, errors = checker.check_safety(code)
    
    return {
        "is_safe": is_safe,
        "warnings": warnings,
        "errors": errors,
        "can_execute": is_safe and len(errors) == 0
    }


# ============ ONE-SHOT MODIFICATION (FULL WORKFLOW) ============

class OneShotModificationRequest(BaseModel):
    """Request immediate modification with auto-approval."""
    task: str = Field(..., description="Natural language task")
    layer: Optional[str] = Field(default=None, description="Target layer if known")
    context: Optional[Dict] = Field(default=None)


@router.post("/autonomous/execute")
async def autonomous_execute(request: OneShotModificationRequest):
    """
    Execute a self-modification task autonomously.
    
    This is the high-level endpoint that:
    1. Parses the natural language task
    2. Determines what needs to be created/modified
    3. Generates the code
    4. Runs safety checks
    5. Applies changes (with checkpoint)
    
    **Use with caution** — this bypasses manual approval.
    """
    try:
        engine = get_modification_engine(require_approval=False)
        
        # Parse task and determine action
        task_lower = request.task.lower()
        
        # Example: "Create a layer for energy calculations"
        if "create layer" in task_lower or "new layer" in task_lower:
            # Extract layer name and purpose
            layer_name = request.layer or "auto_layer"
            
            spec = {
                "name": layer_name,
                "description": f"Auto-generated {layer_name} layer",
                "purpose": request.task,
                "dependencies": [],
                "tools": [
                    {
                        "name": f"{layer_name}_main",
                        "description": f"Main function for {layer_name}",
                        "params": []
                    }
                ]
            }
            
            mod_request = engine.request_create_layer(spec)
            result = engine.apply_modification(mod_request.id)
            
            return {
                "success": result.get("success"),
                "task": request.task,
                "action": "create_layer",
                "request_id": mod_request.id,
                "result": result
            }
        
        # Add more task types as needed
        return {
            "success": False,
            "error": "Could not determine action from task"
        }
        
    except Exception as e:
        logger.error(f"Autonomous execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
