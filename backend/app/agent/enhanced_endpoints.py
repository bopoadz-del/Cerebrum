"""
Enhanced Agent API Endpoints

Connects all agent capabilities to REST endpoints.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.agent.enhanced_core import get_enhanced_agent, EnhancedCerebrumAgent, AgentLayer
from app.agent.websocket import get_websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ Enhanced Request/Response Models ============

class EnhancedTaskRequest(BaseModel):
    task: str = Field(..., description="Task description")
    context: Optional[Dict[str, Any]] = Field(default=None)
    use_memory: bool = Field(default=True, description="Search relevant memories")
    target_layer: Optional[str] = Field(default=None, description="Force specific layer")


class EnhancedTaskResponse(BaseModel):
    success: bool
    action: str
    layer: str
    data: Dict[str, Any]
    message: str
    execution_time_ms: Optional[float]
    related_conversations: List[str]
    suggested_next_actions: List[str]
    timestamp: str


class ConversationQueryRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=90)
    layers: Optional[List[str]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=50)
    context_window: int = Field(default=300)


class MemoryWriteRequest(BaseModel):
    content: str = Field(...)
    tags: Optional[List[str]] = Field(default=None)
    related_layers: Optional[List[str]] = Field(default=None)


class LayerNavigateRequest(BaseModel):
    layer: str = Field(..., description="Target layer name")
    context: Optional[Dict] = Field(default=None)


class LayerInfoResponse(BaseModel):
    name: str
    capabilities: List[str]
    dependencies: List[str]
    current_state: Optional[Dict]
    entry_count: int
    visit_count: int


# ============ ENHANCED AGENT ENDPOINTS ============

@router.post("/execute", response_model=EnhancedTaskResponse)
async def execute_enhanced(request: EnhancedTaskRequest):
    """
    Execute task with full memory awareness and layer navigation.
    
    Automatically:
    - Searches relevant conversations
    - Suggests best layer
    - Navigates and executes
    - Returns related context
    """
    try:
        agent = get_enhanced_agent()
        
        # Force layer if specified
        if request.target_layer:
            try:
                layer = AgentLayer(request.target_layer)
                agent.move_to_layer(layer, request.context)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid layer: {request.target_layer}")
        
        result = await agent.run(request.task, request.context)
        
        return EnhancedTaskResponse(
            success=result.success,
            action=result.action.value,
            layer=result.layer.value,
            data=result.data,
            message=result.message,
            execution_time_ms=result.execution_time_ms,
            related_conversations=result.related_conversations,
            suggested_next_actions=result.suggested_next_actions,
            timestamp=result.timestamp
        )
    except Exception as e:
        logger.error(f"Enhanced execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/enhanced")
async def get_enhanced_status():
    """Get comprehensive agent status with layer info."""
    try:
        agent = get_enhanced_agent()
        navigator = agent.layer_navigator
        
        return {
            "session_id": agent.context.session_id,
            "current_layer": agent.context.current_layer.value,
            "layer_history": [l.layer.value for l in agent.context.layer_history[-5:]],
            "available_tools": len(agent.tools),
            "memory_entries_indexed": len(agent.conversation_reader.memory_index),
            "layer_states": {
                layer.value: navigator.get_layer_info(layer)
                for layer in AgentLayer
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ ENHANCED MEMORY ENDPOINTS ============

@router.post("/conversation/query")
async def query_conversations(request: ConversationQueryRequest):
    """
    Query conversations with advanced filtering.
    
    Filter by days, layers, and tags.
    """
    try:
        agent = get_enhanced_agent()
        result = agent.conversation_reader.read_conversations(
            days=request.days,
            layers=request.layers,
            tags=request.tags
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/semantic-search")
async def semantic_search(request: SemanticSearchRequest):
    """
    Semantic memory search with relevance scoring.
    
    Uses multiple scoring factors:
    - Exact phrase matches
    - Keyword frequency
    - Recency boost
    - Tag matches
    """
    try:
        agent = get_enhanced_agent()
        result = agent.conversation_reader.semantic_search(
            query=request.query,
            limit=request.limit,
            context_window=request.context_window
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/search")
async def quick_search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=50)
):
    """Quick search endpoint (GET version)."""
    try:
        agent = get_enhanced_agent()
        return agent.conversation_reader.semantic_search(q, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/write")
async def write_memory(request: MemoryWriteRequest):
    """Write to memory with tags and layer references."""
    try:
        agent = get_enhanced_agent()
        result = agent.tools["write_memory"](
            content=request.content,
            tags=request.tags,
            related_layers=request.related_layers
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/insights")
async def memory_insights(days: int = Query(default=7, ge=1, le=30)):
    """Extract insights from recent activity."""
    try:
        agent = get_enhanced_agent()
        return agent.conversation_reader.extract_insights(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/entry/{entry_id}")
async def get_conversation_thread(
    entry_id: str,
    context: int = Query(default=3, ge=0, le=10)
):
    """Get a conversation entry with surrounding context."""
    try:
        agent = get_enhanced_agent()
        return agent.conversation_reader.get_conversation_thread(entry_id, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ LAYER NAVIGATION ENDPOINTS ============

@router.post("/layer/navigate")
async def navigate_layer(request: LayerNavigateRequest):
    """Navigate to a specific layer with dependency checking."""
    try:
        agent = get_enhanced_agent()
        layer = AgentLayer(request.layer)
        result = agent.move_to_layer(layer, request.context)
        
        return {
            "success": result.success,
            "from_layer": result.data["previous_layer"],
            "to_layer": result.layer.value,
            "dependencies_satisfied": result.data.get("dependencies_satisfied", True),
            "missing_dependencies": result.data.get("missing_dependencies", []),
            "capabilities": result.data.get("capabilities", []),
            "suggested_actions": result.suggested_next_actions
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid layer: {request.layer}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layer/current")
async def get_current_layer():
    """Get current layer with state information."""
    try:
        agent = get_enhanced_agent()
        current = agent.context.current_layer
        navigator = agent.layer_navigator
        
        return {
            "current_layer": current.value,
            "layer_info": navigator.get_layer_info(current),
            "state": navigator.layer_states.get(current),
            "history": [{
                "layer": h.layer.value,
                "entered_at": h.entered_at,
                "actions": len(h.actions_performed)
            } for h in agent.context.layer_history[-5:]]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layer/list")
async def list_layers():
    """List all available layers with their capabilities."""
    try:
        agent = get_enhanced_agent()
        navigator = agent.layer_navigator
        
        return {
            "layers": [
                navigator.get_layer_info(layer)
                for layer in AgentLayer
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layer/info/{layer_name}", response_model=LayerInfoResponse)
async def get_layer_info(layer_name: str):
    """Get detailed information about a specific layer."""
    try:
        agent = get_enhanced_agent()
        layer = AgentLayer(layer_name)
        info = agent.layer_navigator.get_layer_info(layer)
        return LayerInfoResponse(**info)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid layer: {layer_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/layer/suggest")
async def suggest_layers_for_task(task: str):
    """
    Suggest which layers are best for a given task.
    
    Returns ranked suggestions with confidence scores.
    """
    try:
        agent = get_enhanced_agent()
        suggestions = agent.layer_navigator.suggest_layer_for_task(task)
        return {
            "task": task,
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layer/transitions")
async def get_layer_transitions():
    """Get history of layer transitions."""
    try:
        agent = get_enhanced_agent()
        return {
            "transitions": agent.layer_navigator.transition_history[-20:]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ ALL LAYERS TOOLS ENDPOINTS ============

@router.get("/tools")
async def list_all_tools():
    """List all available tools across all layers."""
    try:
        agent = get_enhanced_agent()
        
        # Group tools by layer
        tools_by_layer = {
            "coding": ["generate_endpoint", "generate_component", "generate_model", "refactor_code"],
            "registry": ["register_capability", "list_capabilities", "get_capability"],
            "validation": ["validate_code", "scan_security", "run_tests"],
            "hotswap": ["deploy_capability", "hot_reload"],
            "healing": ["detect_errors", "analyze_incident", "heal_error"],
            "economics": ["calculate_cost", "estimate_project", "rsmeans_query"],
            "vdc": ["query_bim", "extract_quantities"],
            "edge": ["register_device", "deploy_model_to_edge"],
            "portal": ["create_project", "generate_report"],
            "enterprise": ["audit_security"],
            "triggers": ["create_trigger", "fire_trigger"],
            "monitoring": ["log_event", "record_metric"],
            "memory": ["read_conversation", "search_memory", "write_memory", "extract_insights"]
        }
        
        return {
            "total_tools": len(agent.tools),
            "tools_by_layer": tools_by_layer,
            "all_tools": list(agent.tools.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tool/{tool_name}/execute")
async def execute_tool(tool_name: str, params: Dict[str, Any]):
    """Execute any tool directly by name."""
    try:
        agent = get_enhanced_agent()
        
        if tool_name not in agent.tools:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        result = agent.tools[tool_name](**params)
        return {
            "tool": tool_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ WEBSOCKET ============

@router.websocket("/ws")
async def enhanced_websocket(websocket: WebSocket):
    """WebSocket for real-time agent interaction."""
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
