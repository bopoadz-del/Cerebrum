"""
Cerebrum Agent API Endpoints

Provides REST API for the autonomous agent.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging

from app.agent.core import get_agent, CerebrumAgent, AgentLayer, AgentAction
from app.agent.enhanced_core import get_enhanced_agent, EnhancedCerebrumAgent
from app.agent.websocket import get_websocket_manager
from app.errors import format_error_response, get_user_friendly_error, handle_errors

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ Request/Response Models ============

class AgentTaskRequest(BaseModel):
    """Request to execute an agent task."""
    task: str = Field(..., description="The task description for the agent")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    layer: Optional[str] = Field(default=None, description="Optional: force specific layer")
    include_reasoning: Optional[bool] = Field(default=True, description="Include reasoning content in response (Kimi-style)")
    reasoning_format: Optional[str] = Field(default="markdown", description="Reasoning format: markdown, plain, or structured")


class AgentTaskResponse(BaseModel):
    """Response from agent task execution."""
    success: bool
    action: str
    layer: str
    data: Dict[str, Any]
    message: str
    timestamp: str
    reasoning_content: Optional[str] = Field(default=None, description="Step-by-step reasoning/thinking process (Kimi-style)")
    execution_time_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")


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
    
    model_config = {"protected_namespaces": ()}


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


# ============ Reasoning Configuration Models ============

class ReasoningConfigRequest(BaseModel):
    """Request to update reasoning configuration."""
    enabled: bool = Field(default=True, description="Enable/disable reasoning content generation")
    include_in_response: bool = Field(default=True, description="Include reasoning in API responses")
    max_reasoning_length: int = Field(default=10000, ge=1000, le=50000, description="Maximum reasoning length in characters")
    preserve_across_turns: bool = Field(default=True, description="Preserve reasoning across multi-turn conversations")
    format_style: str = Field(default="markdown", description="Format style: markdown, plain, or structured")


class ReasoningConfigResponse(BaseModel):
    """Response with current reasoning configuration."""
    enabled: bool
    include_in_response: bool
    max_reasoning_length: int
    preserve_across_turns: bool
    format_style: str
    message: str


class ReasoningStep(BaseModel):
    """A single reasoning step."""
    step_number: int
    timestamp: str
    step_type: str
    title: str
    content: str
    layer: Optional[str]


class ReasoningHistoryResponse(BaseModel):
    """Response with reasoning history."""
    session_id: str
    total_steps: int
    steps: List[ReasoningStep]
    formatted_reasoning: Optional[str]


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
        # Use enhanced agent for better conversational routing
        agent = get_enhanced_agent()
        
        # If layer is specified, move there first
        if request.layer:
            try:
                layer = AgentLayer(request.layer)
                agent.move_to_layer(layer)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "That layer doesn't exist.",
                        "suggestion": f"'{request.layer}' is not a valid layer. Use /agent/layers to see available options.",
                        "category": "validation",
                        "retry_allowed": True,
                    }
                )
        
        # Execute the task
        result = await agent.run(request.task, request.context)
        
        return AgentTaskResponse(
            success=result.success,
            action=result.action.value if hasattr(result.action, 'value') else str(result.action),
            layer=result.layer.value if hasattr(result.layer, 'value') else str(result.layer),
            data=result.data,
            message=result.message,
            timestamp=result.timestamp,
            reasoning_content=result.reasoning_content,
            execution_time_ms=result.execution_time_ms
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        error_response = format_error_response(
            e,
            operation="executing your task",
            include_retry=True
        )
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.get("/status", response_model=AgentStatusResponse)
async def get_status():
    """Get current agent status and layer information."""
    agent = get_enhanced_agent()
    status = {
        "current_layer": agent.context.current_layer.value,
        "session_id": agent.context.session_id,
        "available_tools": len(agent.tools),
        "conversation_entries": len(agent.context.conversation_history),
        "generated_artifacts": agent.context.generated_artifacts
    }
    return AgentStatusResponse(**status)


@router.get("/layers", response_model=List[str])
async def list_layers():
    """List all available layers the agent can navigate."""
    return [layer.value for layer in AgentLayer]


@router.get("/tools", response_model=List[str])
async def list_tools():
    """List all available tools the agent can use."""
    agent = get_enhanced_agent()
    return list(agent.tools.keys())


@router.post("/layer/move", response_model=LayerMoveResponse)
async def move_layer(request: LayerMoveRequest):
    """Move the agent to a specific layer."""
    try:
        agent = get_enhanced_agent()
        layer = AgentLayer(request.layer)
        result = agent.move_to_layer(layer)
        
        return LayerMoveResponse(
            success=result.success,
            previous_layer=result.data["previous_layer"],
            current_layer=result.layer.value if hasattr(result.layer, 'value') else str(result.layer),
            message=result.message
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "That layer doesn't exist.",
                "suggestion": f"'{request.layer}' is not a valid layer. Use /agent/layers to see all available layers.",
                "category": "validation",
                "retry_allowed": True,
                "actions": [{"label": "View Layers", "action": "navigate:/agent/layers"}],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Layer move failed: {e}")
        error_response = format_error_response(e, operation="changing layers")
        raise HTTPException(status_code=500, detail=error_response["error"])


# ============ Conversation & Memory Endpoints ============

@router.post("/conversation/read", response_model=ConversationReadResponse)
async def read_conversation(request: ConversationReadRequest):
    """
    Read recent conversation history from memory files.
    
    This allows the agent to access context from previous interactions.
    """
    try:
        agent = get_enhanced_agent()
        result = agent.tools["read_conversation"](days=request.days)
        
        return ConversationReadResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read conversation: {e}")
        error_response = format_error_response(e, operation="reading conversation history")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """
    Search through memory files for specific information.
    
    Searches both daily memory files and MEMORY.md.
    """
    try:
        agent = get_enhanced_agent()
        result = agent.tools["search_memory"](query=request.query, limit=request.limit)
        
        return MemorySearchResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search memory: {e}")
        error_response = format_error_response(e, operation="searching memory")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/memory/write", response_model=MemoryWriteResponse)
async def write_memory(request: MemoryWriteRequest):
    """
    Write to MEMORY.md or a specific memory file.
    
    Use this to persist important information for future reference.
    """
    try:
        agent = get_enhanced_agent()
        result = agent.tools["write_memory"](
            content=request.content,
            tags=["memory_write"] if request.memory_file is None else [request.memory_file]
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Failed to write to memory")
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "We couldn't save your note.",
                    "suggestion": "Please try again. If this keeps happening, check that you have permission to write to the memory files.",
                    "category": "service_unavailable",
                    "retry_allowed": True,
                    "actions": [{"label": "Try Again", "action": "retry"}],
                }
            )
        
        return MemoryWriteResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to write memory: {e}")
        error_response = format_error_response(e, operation="saving to memory")
        raise HTTPException(status_code=500, detail=error_response["error"])


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
        agent = get_enhanced_agent()
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        error_response = format_error_response(e, operation="generating code")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/code/validate", response_model=CodeValidateResponse)
async def validate_code(request: CodeValidateRequest):
    """
    Validate code for security and syntax issues.
    
    Uses the validation pipeline from the self-coding system.
    """
    try:
        agent = get_enhanced_agent()
        result = agent.tools["validate_code"](
            code=request.code,
            code_type=request.code_type
        )
        
        return CodeValidateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code validation failed: {e}")
        error_response = format_error_response(e, operation="validating code")
        raise HTTPException(status_code=500, detail=error_response["error"])


# ============ Healing & Execution Endpoints ============

@router.post("/heal/analyze")
async def heal_analyze(error_logs: str, capability_name: str = "unknown"):
    """
    Analyze error logs and suggest healing actions.
    
    Part of the self-healing layer.
    """
    try:
        agent = get_enhanced_agent()
        result = agent.tools["heal_error"](
            error_logs=error_logs,
            capability_name=capability_name
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Healing analysis failed: {e}")
        error_response = format_error_response(e, operation="analyzing errors")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/sandbox/execute")
async def execute_sandbox(code: str, timeout: int = 30):
    """
    Execute code in a sandboxed Docker environment.
    
    Safe execution with resource limits and no network access.
    """
    try:
        agent = get_enhanced_agent()
        result = agent.tools["execute_sandbox"](code=code, timeout=timeout)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}")
        error_response = format_error_response(e, operation="running code in sandbox")
        raise HTTPException(status_code=500, detail=error_response["error"])


# ============ Reasoning Configuration Endpoints ============

@router.get("/reasoning/config", response_model=ReasoningConfigResponse)
async def get_reasoning_config():
    """
    Get current reasoning configuration.
    
    Returns the current settings for Kimi-style reasoning display.
    """
    try:
        agent = get_enhanced_agent()
        config = agent.reasoning_config
        
        return ReasoningConfigResponse(
            enabled=config.enabled,
            include_in_response=config.include_in_response,
            max_reasoning_length=config.max_reasoning_length,
            preserve_across_turns=config.preserve_across_turns,
            format_style=config.format_style,
            message="Current reasoning configuration retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to get reasoning config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reasoning/config", response_model=ReasoningConfigResponse)
async def update_reasoning_config(request: ReasoningConfigRequest):
    """
    Update reasoning configuration.
    
    Controls Kimi-style reasoning display:
    - enabled: Turn reasoning on/off
    - include_in_response: Include in API responses
    - max_reasoning_length: Limit reasoning length
    - preserve_across_turns: Keep reasoning across turns
    - format_style: markdown, plain, or structured
    """
    try:
        agent = get_enhanced_agent()
        
        # Update config
        agent.reasoning_config.enabled = request.enabled
        agent.reasoning_config.include_in_response = request.include_in_response
        agent.reasoning_config.max_reasoning_length = request.max_reasoning_length
        agent.reasoning_config.preserve_across_turns = request.preserve_across_turns
        agent.reasoning_config.format_style = request.format_style
        
        # Update the tracker's config reference
        agent.reasoning_tracker.config = agent.reasoning_config
        
        return ReasoningConfigResponse(
            enabled=agent.reasoning_config.enabled,
            include_in_response=agent.reasoning_config.include_in_response,
            max_reasoning_length=agent.reasoning_config.max_reasoning_length,
            preserve_across_turns=agent.reasoning_config.preserve_across_turns,
            format_style=agent.reasoning_config.format_style,
            message="Reasoning configuration updated successfully"
        )
    except Exception as e:
        logger.error(f"Failed to update reasoning config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reasoning/history", response_model=ReasoningHistoryResponse)
async def get_reasoning_history():
    """
    Get the current reasoning history.
    
    Returns the step-by-step reasoning from the current/last task execution.
    """
    try:
        agent = get_enhanced_agent()
        tracker = agent.reasoning_tracker
        
        steps = [
            ReasoningStep(
                step_number=step["step_number"],
                timestamp=step["timestamp"],
                step_type=step["step_type"],
                title=step["title"],
                content=step["content"],
                layer=step.get("layer")
            )
            for step in tracker.steps
        ]
        
        return ReasoningHistoryResponse(
            session_id=tracker.session_id,
            total_steps=len(tracker.steps),
            steps=steps,
            formatted_reasoning=tracker.format_reasoning()
        )
    except Exception as e:
        logger.error(f"Failed to get reasoning history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reasoning/clear")
async def clear_reasoning_history():
    """
    Clear the reasoning history.
    
    Useful for starting fresh or resetting between conversations.
    """
    try:
        agent = get_enhanced_agent()
        old_step_count = len(agent.reasoning_tracker.steps)
        
        # Reset the tracker
        from app.agent.enhanced_core import ReasoningTracker
        agent.reasoning_tracker = ReasoningTracker(agent.reasoning_config)
        agent.previous_reasoning = None
        
        return {
            "success": True,
            "message": f"Reasoning history cleared ({old_step_count} steps removed)",
            "cleared_steps": old_step_count
        }
    except Exception as e:
        logger.error(f"Failed to clear reasoning: {e}")
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
    
    agent = get_enhanced_agent()
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
        agent = get_enhanced_agent()
        plan_dict = await agent.create_plan(request.goal, request.context)
        return PlanResponse(**plan_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plan creation failed: {e}")
        error_response = format_error_response(e, operation="creating your plan")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/plan/execute/{plan_id}", response_model=PlanResponse)
async def execute_plan(plan_id: str, background_tasks: BackgroundTasks):
    """
    Execute a previously created plan.
    
    Runs all steps with dependency resolution and error recovery.
    """
    try:
        agent = get_enhanced_agent()
        # Run in background for long-running plans
        plan_dict = await agent.execute_plan(plan_id)
        return PlanResponse(**plan_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plan execution failed: {e}")
        error_response = format_error_response(e, operation="executing your plan")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/plan/run", response_model=PlanResponse)
async def create_and_run_plan(request: CreatePlanRequest):
    """
    Create and execute a plan in one call.
    
    Convenience endpoint for simple use cases.
    """
    try:
        agent = get_enhanced_agent()
        plan_dict = await agent.run_with_plan(request.goal, request.context)
        return PlanResponse(**plan_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Plan run failed: {e}")
        error_response = format_error_response(e, operation="running your task")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.get("/plan/{plan_id}")
async def get_plan(plan_id: str):
    """Get plan status and details."""
    try:
        agent = get_enhanced_agent()
        planner = agent._get_planner()
        plan = planner.get_plan(plan_id)
        if plan:
            return plan.to_dict()
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that plan.",
                "suggestion": "The plan may have been deleted or the ID might be incorrect. Check your plans list to find the correct one.",
                "category": "not_found",
                "retry_allowed": True,
                "actions": [{"label": "View All Plans", "action": "navigate:/agent/plans"}],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get plan failed: {e}")
        error_response = format_error_response(e, operation="getting plan details")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.get("/plans")
async def list_plans():
    """List all active plans."""
    try:
        agent = get_enhanced_agent()
        planner = agent._get_planner()
        return {"plans": planner.list_plans()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List plans failed: {e}")
        error_response = format_error_response(e, operation="listing your plans")
        raise HTTPException(status_code=500, detail=error_response["error"])


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
        agent = get_enhanced_agent()
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task scheduling failed: {e}")
        error_response = format_error_response(e, operation="scheduling your task")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.get("/schedule/tasks", response_model=List[ScheduledTaskResponse])
async def list_scheduled_tasks():
    """List all scheduled tasks."""
    try:
        agent = get_enhanced_agent()
        tasks = agent.list_scheduled_tasks()
        return [ScheduledTaskResponse(**t) for t in tasks]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List tasks failed: {e}")
        error_response = format_error_response(e, operation="listing scheduled tasks")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/schedule/{task_id}/enable")
async def enable_task(task_id: str):
    """Enable a scheduled task."""
    try:
        agent = get_enhanced_agent()
        scheduler = agent._get_scheduler()
        if scheduler.enable_task(task_id):
            return {"success": True, "message": "Task enabled"}
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that scheduled task.",
                "suggestion": "The task may have been deleted or the ID is incorrect. Check your scheduled tasks list.",
                "category": "not_found",
                "retry_allowed": True,
                "actions": [{"label": "View Tasks", "action": "navigate:/agent/schedule/tasks"}],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enable task failed: {e}")
        error_response = format_error_response(e, operation="enabling the task")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/schedule/{task_id}/disable")
async def disable_task(task_id: str):
    """Disable a scheduled task."""
    try:
        agent = get_enhanced_agent()
        scheduler = agent._get_scheduler()
        if scheduler.disable_task(task_id):
            return {"success": True, "message": "Task disabled"}
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that scheduled task.",
                "suggestion": "The task may have been deleted or the ID is incorrect. Check your scheduled tasks list.",
                "category": "not_found",
                "retry_allowed": True,
                "actions": [{"label": "View Tasks", "action": "navigate:/agent/schedule/tasks"}],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Disable task failed: {e}")
        error_response = format_error_response(e, operation="disabling the task")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.delete("/schedule/{task_id}")
async def delete_scheduled_task(task_id: str):
    """Delete a scheduled task."""
    try:
        agent = get_enhanced_agent()
        if agent.cancel_scheduled_task(task_id):
            return {"success": True, "message": "Task deleted"}
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't find that scheduled task.",
                "suggestion": "The task may have already been deleted or the ID is incorrect.",
                "category": "not_found",
                "retry_allowed": True,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete task failed: {e}")
        error_response = format_error_response(e, operation="deleting the task")
        raise HTTPException(status_code=500, detail=error_response["error"])


@router.post("/schedule/{task_id}/run")
async def run_task_now(task_id: str):
    """Manually trigger a scheduled task to run immediately."""
    try:
        agent = get_enhanced_agent()
        scheduler = agent._get_scheduler()
        if scheduler.run_task_now(task_id):
            return {"success": True, "message": "Task triggered"}
        raise HTTPException(
            status_code=404,
            detail={
                "message": "We couldn't run that task right now.",
                "suggestion": "The task may not exist or is already running. Check your scheduled tasks list and try again.",
                "category": "not_found",
                "retry_allowed": True,
                "actions": [{"label": "View Tasks", "action": "navigate:/agent/schedule/tasks"}],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run task failed: {e}")
        error_response = format_error_response(e, operation="running the task")
        raise HTTPException(status_code=500, detail=error_response["error"])
