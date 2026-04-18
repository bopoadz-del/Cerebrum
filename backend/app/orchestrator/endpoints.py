"""
Orchestrator Endpoints

FastAPI routes for the Smart Orchestrator:
- Intent routing
- Workflow management
- Session management
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from app.orchestrator.intent_router import IntentRouter, IntentMatch
from app.orchestrator.intelligent_workflow import IntelligentWorkflow
from app.orchestrator.session_memory import SessionMemory

router = APIRouter(tags=["orchestrator"])


# ═══════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════

class RouteRequest(BaseModel):
    """Request model for intent routing."""
    message: str = Field(..., description="User message to route")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    file_path: Optional[str] = Field(None, description="Current file path if available")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class RouteResponse(BaseModel):
    """Response model for intent routing."""
    action: str = Field(..., description="Matched action name")
    priority: str = Field(..., description="Match priority level")
    confidence: float = Field(..., description="Match confidence (0-1)")
    extracted_params: Dict[str, Any] = Field(..., description="Extracted parameters")
    reasoning: str = Field(..., description="Routing reasoning")


class WorkflowExecuteRequest(BaseModel):
    """Request model for workflow execution."""
    workflow_name: str = Field(..., description="Name of workflow to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Initial parameters")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")


class WorkflowBuildRequest(BaseModel):
    """Request model for custom workflow building."""
    goal: str = Field(..., description="User goal for workflow")
    params: Dict[str, Any] = Field(default_factory=dict, description="Initial context")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    steps: int = Field(..., description="Number of steps")
    inputs: List[str] = Field(..., description="Required inputs")


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    state: str = Field(..., description="Current workflow state")
    completed_actions: List[str] = Field(..., description="Actions completed so far")
    data_keys: List[str] = Field(..., description="Keys of accumulated data")


class WorkflowExecuteResponse(BaseModel):
    """Response model for workflow execution."""
    workflow_name: str = Field(..., description="Name of executed workflow")
    status: str = Field(..., description="Execution status")
    steps_completed: int = Field(..., description="Steps completed")
    total_steps: int = Field(..., description="Total steps")
    step_results: List[Dict[str, Any]] = Field(..., description="Results of each step")
    accumulated_data: Dict[str, Any] = Field(..., description="Accumulated workflow data")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class SessionContextResponse(BaseModel):
    """Response model for session context."""
    session_id: str = Field(..., description="Session ID")
    current_file: Optional[str] = Field(None, description="Current file")
    current_package: Optional[str] = Field(None, description="Current package")
    last_action: Optional[str] = Field(None, description="Last executed action")
    last_outcome: Optional[str] = Field(None, description="Outcome of last action")
    action_count: int = Field(..., description="Total actions executed")
    file_count: int = Field(..., description="Total files processed")
    files: List[str] = Field(..., description="Recent files")
    workflow_active: bool = Field(..., description="Whether workflow is active")
    workflow_state: Optional[str] = Field(None, description="Current workflow state")
    workflow_chain: List[str] = Field(..., description="Workflow action chain")


class ActionInfoResponse(BaseModel):
    """Response model for action information."""
    name: str = Field(..., description="Action name")
    category: str = Field(..., description="Action category")
    description: str = Field(..., description="Action description")
    keywords: List[str] = Field(..., description="Matching keywords")
    required_input: List[str] = Field(..., description="Required inputs")
    optional_input: List[str] = Field(..., description="Optional inputs")
    schema_triggers: List[str] = Field(..., description="File type triggers")


# ═══════════════════════════════════════════════════════════
# DEPENDENCIES
# ═══════════════════════════════════════════════════════════

def get_intent_router() -> IntentRouter:
    """Dependency to get the intent router instance."""
    return IntentRouter()

def get_workflow_engine() -> IntelligentWorkflow:
    """Dependency to get the workflow engine instance."""
    return IntelligentWorkflow()

def get_session_memory() -> SessionMemory:
    """Dependency to get the session memory instance."""
    return SessionMemory()


# ═══════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════

@router.post("/orchestrator/route", response_model=RouteResponse)
async def route_intent(
    request: RouteRequest,
    router: IntentRouter = Depends(get_intent_router)
) -> RouteResponse:
    """
    Route a user message to the appropriate construction action.
    
    Uses multi-priority intent matching:
    1. Exact action name/synonym match
    2. Keyword + pattern match
    3. Schema match (file type + keywords)
    4. Goal chaining detection
    5. Fallback to Self-Coding Agent
    """
    # Build context
    context = request.context or {}
    if request.session_id:
        context["session_id"] = request.session_id
    if request.file_path:
        context["file_path"] = request.file_path
    
    # Route the intent
    match = await router.route(request.message, context)
    
    return RouteResponse(
        action=match.action_name,
        priority=match.priority.name,
        confidence=match.confidence,
        extracted_params=match.extracted_params,
        reasoning=match.reasoning,
    )


@router.get("/orchestrator/actions", response_model=List[ActionInfoResponse])
async def list_actions(
    category: Optional[str] = Query(None, description="Filter by category"),
    router: IntentRouter = Depends(get_intent_router)
) -> List[ActionInfoResponse]:
    """List all available construction actions."""
    actions = router.list_actions(category=category)
    return [
        ActionInfoResponse(
            name=a["name"],
            category=a["category"],
            description=a["description"],
            keywords=a.get("keywords", []),
            required_input=a.get("required_input", []),
            optional_input=a.get("optional_input", []),
            schema_triggers=a.get("schema_triggers", []),
        )
        for a in actions
    ]


@router.get("/orchestrator/actions/{action_name}", response_model=ActionInfoResponse)
async def get_action_info(
    action_name: str,
    router: IntentRouter = Depends(get_intent_router)
) -> ActionInfoResponse:
    """Get detailed information about a specific action."""
    info = router.get_action_info(action_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Action '{action_name}' not found")
    
    return ActionInfoResponse(
        name=info["name"],
        category=info["category"],
        description=info["description"],
        keywords=info.get("keywords", []),
        required_input=info.get("required_input", []),
        optional_input=info.get("optional_input", []),
        schema_triggers=info.get("schema_triggers", []),
    )


@router.get("/orchestrator/workflows", response_model=List[WorkflowResponse])
async def list_workflows(
    engine: IntelligentWorkflow = Depends(get_workflow_engine)
) -> List[WorkflowResponse]:
    """List all available predefined workflows."""
    workflows = engine.list_workflows()
    return [
        WorkflowResponse(
            name=w["name"],
            description=w["description"],
            steps=w["steps"],
            inputs=w["inputs"],
        )
        for w in workflows
    ]


@router.post("/orchestrator/workflows/build", response_model=WorkflowResponse)
async def build_workflow(
    request: WorkflowBuildRequest,
    engine: IntelligentWorkflow = Depends(get_workflow_engine)
) -> WorkflowResponse:
    """
    Build a custom workflow from a user goal.
    
    Analyzes the goal and context to determine appropriate
    action sequence.
    """
    workflow = engine.build_workflow(request.goal, request.params)
    
    if not workflow:
        raise HTTPException(
            status_code=400,
            detail="Could not build workflow from goal. Try being more specific."
        )
    
    return WorkflowResponse(
        name=workflow.name,
        description=workflow.description,
        steps=len(workflow.steps),
        inputs=workflow.input_requirements,
    )


@router.post("/orchestrator/workflows/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow(
    request: WorkflowExecuteRequest,
    engine: IntelligentWorkflow = Depends(get_workflow_engine)
) -> WorkflowExecuteResponse:
    """
    Execute a predefined or custom workflow.
    
    Chains multiple construction actions together,
    passing outputs from one action to the next.
    """
    # Get the workflow
    workflow = engine.get_workflow(request.workflow_name)
    
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{request.workflow_name}' not found"
        )
    
    # Execute the workflow
    result = await engine.execute_workflow(
        workflow,
        request.params,
        request.session_id
    )
    
    return WorkflowExecuteResponse(
        workflow_name=result["workflow_name"],
        status=result["status"],
        steps_completed=result["steps_completed"],
        total_steps=result["total_steps"],
        step_results=result["step_results"],
        accumulated_data=result.get("accumulated_data", {}),
        errors=result.get("errors", []),
    )


@router.get("/orchestrator/workflows/status/{session_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    session_id: str,
    engine: IntelligentWorkflow = Depends(get_workflow_engine)
) -> WorkflowStatusResponse:
    """Get the status of a running workflow."""
    status = engine.get_workflow_status(session_id)
    
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"No active workflow for session '{session_id}'"
        )
    
    return WorkflowStatusResponse(
        state=status["state"],
        completed_actions=status["completed_actions"],
        data_keys=status["data_keys"],
    )


@router.get("/orchestrator/session/{session_id}", response_model=SessionContextResponse)
async def get_session_context(
    session_id: str,
    memory: SessionMemory = Depends(get_session_memory)
) -> SessionContextResponse:
    """Get the current context for a session."""
    summary = memory.get_context_summary(session_id)
    
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found or expired"
        )
    
    return SessionContextResponse(
        session_id=summary["session_id"],
        current_file=summary.get("current_file"),
        current_package=summary.get("current_package"),
        last_action=summary.get("last_action"),
        last_outcome=summary.get("last_outcome"),
        action_count=summary.get("action_count", 0),
        file_count=summary.get("file_count", 0),
        files=summary.get("files", []),
        workflow_active=summary.get("workflow_active", False),
        workflow_state=summary.get("workflow_state"),
        workflow_chain=summary.get("workflow_chain", []),
    )


@router.post("/orchestrator/session/{session_id}/clear")
async def clear_session(
    session_id: str,
    memory: SessionMemory = Depends(get_session_memory)
) -> Dict[str, str]:
    """Clear all session context and history."""
    memory.clear_workflow(session_id)
    # Also clear the session completely by removing it
    if session_id in memory._sessions:
        del memory._sessions[session_id]
    
    return {"status": "cleared", "session_id": session_id}
