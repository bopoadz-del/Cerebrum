"""
Cerebrum Agent API Endpoints

Provides REST API for the autonomous agent.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging

from app.agent.core import get_agent, CerebrumAgent, AgentLayer, AgentAction
from app.agent.websocket import get_websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ Request/Response Models ============

class AgentTaskRequest(BaseModel):
    """Request to execute an agent task."""
    task: str = Field(..., description="The task description for the agent")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    layer: Optional[str] = Field(default=None, description="Optional: force specific layer")


class AgentTaskResponse(BaseModel):
    """Response from agent task execution."""
    success: bool
    action: str
    layer: str
    data: Dict[str, Any]
    message: str
    timestamp: str


class AgentStatusResponse(BaseModel):
    """Agent status response."""
    current_layer: str
    session_id: str
    available_tools: int
    conversation_entries: int
    generated_artifacts: List[str]


class ConversationReadRequest(BaseModel):
    """Request to read conversation history."""
    days: int = Field(default=2, ge=1, le=30, description="Number of days to look back")


class ConversationReadResponse(BaseModel):
    """Response with conversation data."""
    recent_conversations: List[Dict]
    memory_md: Dict
    session_id: str


class MemorySearchRequest(BaseModel):
    """Request to search memory."""
    query: str = Field(..., description="Search query")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum results")


class MemorySearchResponse(BaseModel):
    """Response from memory search."""
    query: str
    results: List[Dict]
    total_matches: int


class MemoryWriteRequest(BaseModel):
    """Request to write to memory."""
    content: str = Field(..., description="Content to write")
    memory_file: Optional[str] = Field(default=None, description="Specific memory file (optional)")


class MemoryWriteResponse(BaseModel):
    """Response from memory write."""
    success: bool
    file: str
    timestamp: str


class CodeGenerateRequest(BaseModel):
    """Request to generate code."""
    description: str = Field(..., description="Feature description")
    code_type: str = Field(default="endpoint", description="Type: endpoint, component, model")
    model_name: Optional[str] = Field(default=None, description="Model/Component name")
    fields: Optional[List[Dict]] = Field(default=None, description="Field definitions")


class CodeGenerateResponse(BaseModel):
    """Response from code generation."""
    success: bool
    code: Optional[str]
    language: str
    metadata: Dict[str, Any]
    errors: List[str]


class CodeValidateRequest(BaseModel):
    """Request to validate code."""
    code: str = Field(..., description="Code to validate")
    code_type: str = Field(default="python", description="Code type/language")


class CodeValidateResponse(BaseModel):
    """Response from code validation."""
    security_violations: List[str]
    syntax_valid: bool
    syntax_error: Optional[str]
    passed: bool


class LayerMoveRequest(BaseModel):
    """Request to move to a specific layer."""
    layer: str = Field(..., description="Target layer name")


class LayerMoveResponse(BaseModel):
    """Response from layer move."""
    success: bool
    previous_layer: str
    current_layer: str
    message: str


# ============ API Endpoints ============

@router.post("/execute", response_model=AgentTaskResponse)
async def execute_task(request: AgentTaskRequest):
    """
    Execute an autonomous agent task.
    
    The agent will:
    1. Parse the task and determine the appropriate layer
    2. Read conversation context
    3. Execute the appropriate tools
    4. Return results
    
    Example tasks:
    - "Generate an endpoint for Project model with name, status, budget fields"
    - "Search memory for RSMeans pricing discussions"
    - "Validate this code for security issues"
    - "Heal errors in the drywall calculator"
    """
    try:
        agent = get_agent()
        
        # If layer is specified, move there first
        if request.layer:
            try:
                layer = AgentLayer(request.layer)
                agent.move_to_layer(layer)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid layer: {request.layer}")
        
        # Execute the task
        result = await agent.run(request.task, request.context)
        
        return AgentTaskResponse(
            success=result.success,
            action=result.action.value,
            layer=result.layer.value,
            data=result.data,
            message=result.message,
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=AgentStatusResponse)
async def get_status():
    """Get current agent status and layer information."""
    agent = get_agent()
    status = agent.get_layer_status()
    return AgentStatusResponse(**status)


@router.get("/layers", response_model=List[str])
async def list_layers():
    """List all available layers the agent can navigate."""
    return [layer.value for layer in AgentLayer]


@router.get("/tools", response_model=List[str])
async def list_tools():
    """List all available tools the agent can use."""
    agent = get_agent()
    return agent.get_available_tools()


@router.post("/layer/move", response_model=LayerMoveResponse)
async def move_layer(request: LayerMoveRequest):
    """Move the agent to a specific layer."""
    try:
        agent = get_agent()
        layer = AgentLayer(request.layer)
        result = agent.move_to_layer(layer)
        
        return LayerMoveResponse(
            success=result.success,
            previous_layer=result.data["previous_layer"],
            current_layer=result.layer.value,
            message=result.message
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid layer: {request.layer}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Conversation & Memory Endpoints ============

@router.post("/conversation/read", response_model=ConversationReadResponse)
async def read_conversation(request: ConversationReadRequest):
    """
    Read recent conversation history from memory files.
    
    This allows the agent to access context from previous interactions.
    """
    try:
        agent = get_agent()
        result = agent.tools["read_conversation"](days=request.days)
        
        return ConversationReadResponse(**result)
    except Exception as e:
        logger.error(f"Failed to read conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """
    Search through memory files for specific information.
    
    Searches both daily memory files and MEMORY.md.
    """
    try:
        agent = get_agent()
        result = agent.tools["search_memory"](query=request.query, limit=request.limit)
        
        return MemorySearchResponse(**result)
    except Exception as e:
        logger.error(f"Failed to search memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/write", response_model=MemoryWriteResponse)
async def write_memory(request: MemoryWriteRequest):
    """
    Write to MEMORY.md or a specific memory file.
    
    Use this to persist important information for future reference.
    """
    try:
        agent = get_agent()
        result = agent.tools["write_memory"](
            content=request.content,
            memory_file=request.memory_file
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        return MemoryWriteResponse(**result)
    except Exception as e:
        logger.error(f"Failed to write memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Code Generation Endpoints ============

@router.post("/code/generate", response_model=CodeGenerateResponse)
async def generate_code(request: CodeGenerateRequest):
    """
    Generate code using the agent's self-coding capabilities.
    
    Supports:
    - FastAPI endpoints
    - React components  
    - Database models
    """
    try:
        agent = get_agent()
        
        if request.code_type == "endpoint":
            result = agent.tools["generate_endpoint"](
                description=request.description,
                model_name=request.model_name or "Item",
                fields=request.fields or []
            )
        elif request.code_type == "component":
            result = agent.tools["generate_component"](
                description=request.description,
                component_name=request.model_name or "MyComponent"
            )
        else:
            # Default to endpoint
            result = agent.tools["generate_endpoint"](
                description=request.description,
                model_name=request.model_name or "Item",
                fields=request.fields or []
            )
        
        return CodeGenerateResponse(**result)
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code/validate", response_model=CodeValidateResponse)
async def validate_code(request: CodeValidateRequest):
    """
    Validate code for security and syntax issues.
    
    Uses the validation pipeline from the self-coding system.
    """
    try:
        agent = get_agent()
        result = agent.tools["validate_code"](
            code=request.code,
            code_type=request.code_type
        )
        
        return CodeValidateResponse(**result)
    except Exception as e:
        logger.error(f"Code validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Healing & Execution Endpoints ============

@router.post("/heal/analyze")
async def heal_analyze(error_logs: str, capability_name: str = "unknown"):
    """
    Analyze error logs and suggest healing actions.
    
    Part of the self-healing layer.
    """
    try:
        agent = get_agent()
        result = agent.tools["heal_error"](
            error_logs=error_logs,
            capability_name=capability_name
        )
        
        return result
    except Exception as e:
        logger.error(f"Healing analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sandbox/execute")
async def execute_sandbox(code: str, timeout: int = 30):
    """
    Execute code in a sandboxed Docker environment.
    
    Safe execution with resource limits and no network access.
    """
    try:
        agent = get_agent()
        result = agent.tools["execute_sandbox"](code=code, timeout=timeout)
        
        return result
    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ WebSocket for Real-time Agent ============

@router.websocket("/ws")
async def agent_websocket(websocket: WebSocket):
    """
    WebSocket for real-time agent interaction.
    
    Message types:
    - task: Execute single task
    - plan: Multi-step plan execution  
    - stream: Streaming execution with progress
    - cancel: Cancel current task
    - ping: Heartbeat
    """
    import uuid
    client_id = str(uuid.uuid4())[:8]
    
    agent = get_agent()
    manager = get_websocket_manager(agent)
    
    try:
        connection = await manager.connect(websocket, client_id)
        
        while True:
            message = await connection.receive()
            await manager.handle_message(client_id, message)
            
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(client_id)


# ============ Multi-Step Planning Endpoints ============

class CreatePlanRequest(BaseModel):
    """Request to create a multi-step plan."""
    goal: str = Field(..., description="The goal to achieve")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class PlanResponse(BaseModel):
    """Response with plan details."""
    id: str
    goal: str
    steps: List[Dict]
    status: str
    progress: Dict
    created_at: str


@router.post("/plan/create", response_model=PlanResponse)
async def create_plan(request: CreatePlanRequest):
    """
    Create a multi-step execution plan.
    
    Breaks down complex goals into executable steps with dependencies.
    """
    try:
        agent = get_agent()
        plan_dict = await agent.create_plan(request.goal, request.context)
        return PlanResponse(**plan_dict)
    except Exception as e:
        logger.error(f"Plan creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan/execute/{plan_id}", response_model=PlanResponse)
async def execute_plan(plan_id: str, background_tasks: BackgroundTasks):
    """
    Execute a previously created plan.
    
    Runs all steps with dependency resolution and error recovery.
    """
    try:
        agent = get_agent()
        # Run in background for long-running plans
        plan_dict = await agent.execute_plan(plan_id)
        return PlanResponse(**plan_dict)
    except Exception as e:
        logger.error(f"Plan execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan/run", response_model=PlanResponse)
async def create_and_run_plan(request: CreatePlanRequest):
    """
    Create and execute a plan in one call.
    
    Convenience endpoint for simple use cases.
    """
    try:
        agent = get_agent()
        plan_dict = await agent.run_with_plan(request.goal, request.context)
        return PlanResponse(**plan_dict)
    except Exception as e:
        logger.error(f"Plan run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/{plan_id}")
async def get_plan(plan_id: str):
    """Get plan status and details."""
    try:
        agent = get_agent()
        planner = agent._get_planner()
        plan = planner.get_plan(plan_id)
        if plan:
            return plan.to_dict()
        raise HTTPException(status_code=404, detail="Plan not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get plan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def list_plans():
    """List all active plans."""
    try:
        agent = get_agent()
        planner = agent._get_planner()
        return {"plans": planner.list_plans()}
    except Exception as e:
        logger.error(f"List plans failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Task Scheduling Endpoints ============

class ScheduleTaskRequest(BaseModel):
    """Request to schedule a recurring task."""
    name: str = Field(..., description="Task name")
    description: str = Field(..., description="Task description")
    task_template: str = Field(..., description="The agent task to execute")
    schedule_type: str = Field(..., description="once, interval, daily, weekly, cron")
    schedule_config: Dict[str, Any] = Field(..., description="Schedule configuration")
    max_runs: Optional[int] = Field(default=None, description="Max executions (None=infinite)")


class ScheduledTaskResponse(BaseModel):
    """Response with scheduled task details."""
    id: str
    name: str
    description: str
    schedule_type: str
    status: str
    next_run: Optional[str]
    run_count: int
    max_runs: Optional[int]
    enabled: bool
    created_at: str


@router.post("/schedule/create", response_model=ScheduledTaskResponse)
async def schedule_task(request: ScheduleTaskRequest):
    """
    Schedule a recurring agent task.
    
    Examples:
    - Daily: {"schedule_type": "daily", "schedule_config": {"at": "09:00"}}
    - Interval: {"schedule_type": "interval", "schedule_config": {"minutes": 30}}
    - Weekly: {"schedule_type": "weekly", "schedule_config": {"day": "monday", "at": "10:00"}}
    """
    try:
        agent = get_agent()
        task_dict = agent.schedule_task(
            name=request.name,
            description=request.description,
            task_template=request.task_template,
            schedule_type=request.schedule_type,
            schedule_config=request.schedule_config,
            max_runs=request.max_runs
        )
        
        # Start scheduler if not running
        if agent.scheduler:
            await agent.start_scheduler()
        
        return ScheduledTaskResponse(**task_dict)
    except Exception as e:
        logger.error(f"Task scheduling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/tasks", response_model=List[ScheduledTaskResponse])
async def list_scheduled_tasks():
    """List all scheduled tasks."""
    try:
        agent = get_agent()
        tasks = agent.list_scheduled_tasks()
        return [ScheduledTaskResponse(**t) for t in tasks]
    except Exception as e:
        logger.error(f"List tasks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule/{task_id}/enable")
async def enable_task(task_id: str):
    """Enable a scheduled task."""
    try:
        agent = get_agent()
        scheduler = agent._get_scheduler()
        if scheduler.enable_task(task_id):
            return {"success": True, "message": "Task enabled"}
        raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enable task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule/{task_id}/disable")
async def disable_task(task_id: str):
    """Disable a scheduled task."""
    try:
        agent = get_agent()
        scheduler = agent._get_scheduler()
        if scheduler.disable_task(task_id):
            return {"success": True, "message": "Task disabled"}
        raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Disable task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedule/{task_id}")
async def delete_scheduled_task(task_id: str):
    """Delete a scheduled task."""
    try:
        agent = get_agent()
        if agent.cancel_scheduled_task(task_id):
            return {"success": True, "message": "Task deleted"}
        raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule/{task_id}/run")
async def run_task_now(task_id: str):
    """Manually trigger a scheduled task to run immediately."""
    try:
        agent = get_agent()
        scheduler = agent._get_scheduler()
        if scheduler.run_task_now(task_id):
            return {"success": True, "message": "Task triggered"}
        raise HTTPException(status_code=404, detail="Task not found or already running")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
