"""
Agent API Endpoints - v2
Connects Smart Orchestrator + Reasoning Engine + Formula Library
"""

import os
import uuid
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.logging import get_logger
from app.orchestrator.intent_router import IntentRouter, MatchPriority
from app.reasoning.engine import ReasoningEngine
from app.services.formula_runtime import get_formulas, execute_formula

logger = get_logger(__name__)
router = APIRouter(prefix="/agent/v2", tags=["agent"])

# Initialize engines
intent_router = IntentRouter()
reasoning_engine = ReasoningEngine()


class AgentExecuteRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(default=None)
    current_file: Optional[str] = Field(default=None)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    layer: Optional[str] = Field(default="coding", description="Current layer")


class AgentExecuteResponse(BaseModel):
    success: bool
    action: str
    layer: str
    data: Dict[str, Any]
    message: str
    execution_time_ms: int
    suggested_next_actions: List[str]
    timestamp: str


class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 5


class MemorySearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_found: int


class LayerNavigateRequest(BaseModel):
    target_layer: str
    reason: Optional[str] = None


@router.post("/execute", response_model=AgentExecuteResponse)
async def agent_execute(request: AgentExecuteRequest):
    """
    Main agent execution endpoint.
    Uses Smart Orchestrator to route to appropriate action.
    """
    start_time = time.time()
    
    try:
        # Step 1: Route intent using Smart Orchestrator
        intent_match = intent_router.route(
            message=request.message,
            context=request.context,
            current_file=request.current_file
        )
        
        # Step 2: Execute based on matched action
        result_data = {}
        response_message = ""
        
        # Get action handler
        action = intent_match.action
        confidence = intent_match.confidence
        
        if confidence < 0.3:
            # Low confidence - use general LLM response
            response_message = f"I'm not sure what you're asking. Could you clarify? I detected possible intent: {action}"
            result_data = {"confidence": confidence, "clarification_needed": True}
        
        elif action.startswith("calculate_") or action == "formula_eval":
            # Use Formula Library
            formula_results = await _handle_formula_request(request.message)
            result_data = formula_results
            response_message = _format_formula_response(formula_results)
            
        elif action in ["analyze_document", "extract_specs", "check_compliance"]:
            # Use Reasoning Engine
            reasoning_result = await _handle_reasoning_request(action, request.message, request.context)
            result_data = reasoning_result
            response_message = reasoning_result.get("analysis", "Analysis complete")
            
        elif action in ["full_qto", "change_order_workflow", "compliance_check", "risk_assessment"]:
            # Use Orchestrator Workflows
            workflow_result = await _handle_workflow_request(action, request.message, request.context)
            result_data = workflow_result
            response_message = workflow_result.get("summary", "Workflow executed")
            
        else:
            # Default LLM response for general queries
            response_message = await _call_llm_for_response(request.message, action)
            result_data = {"action": action, "confidence": confidence}
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AgentExecuteResponse(
            success=True,
            action=action,
            layer=request.layer or "coding",
            data=result_data,
            message=response_message,
            execution_time_ms=execution_time,
            suggested_next_actions=intent_match.suggested_next or [],
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/enhanced")
async def agent_status():
    """Get enhanced agent status."""
    return {
        "status": "operational",
        "current_layer": "coding",
        "available_layers": [
            "coding", "registry", "validation", "hotswap", "healing",
            "prompts", "triggers", "economics", "vdc", "edge",
            "portal", "enterprise", "connectors", "monitoring"
        ],
        "orchestrator_actions": len(intent_router.list_actions()),
        "reasoning_engine": "sympy_based",
        "formula_count": len(get_formulas())
    }


@router.get("/layers")
async def list_layers():
    """List all available agent layers."""
    return {
        "layers": [
            {"name": "coding", "description": "Code generation and modification"},
            {"name": "economics", "description": "Cost estimation and pricing"},
            {"name": "vdc", "description": "Virtual Design and Construction"},
            {"name": "edge", "description": "Edge inference and IoT"},
            {"name": "validation", "description": "Security and code validation"},
            {"name": "healing", "description": "Self-healing and error recovery"},
        ]
    }


@router.post("/layer/navigate")
async def navigate_layer(request: LayerNavigateRequest):
    """Navigate to a different agent layer."""
    valid_layers = ["coding", "economics", "vdc", "edge", "validation", "healing"]
    
    if request.target_layer not in valid_layers:
        raise HTTPException(status_code=400, detail=f"Invalid layer: {request.target_layer}")
    
    return {
        "success": True,
        "previous_layer": "coding",
        "current_layer": request.target_layer,
        "reason": request.reason or "User navigation",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/memory/search")
async def memory_search(request: MemorySearchRequest):
    """Search agent memory (placeholder - would integrate with vector DB)."""
    # Placeholder implementation
    return MemorySearchResponse(
        results=[],
        total_found=0
    )


@router.get("/tools")
async def list_tools():
    """List all available agent tools."""
    formulas = get_formulas()
    orchestrator_actions = intent_router.list_actions()
    
    return {
        "formulas": [{"id": f.id, "name": f.name, "domain": f.domain} for f in formulas[:10]],
        "orchestrator_actions": orchestrator_actions,
        "reasoning_capabilities": [
            "variance_analysis",
            "compliance_check",
            "document_merge",
            "specification_extraction"
        ]
    }


# Helper functions

async def _handle_formula_request(message: str) -> Dict[str, Any]:
    """Extract formula parameters and execute."""
    formulas = get_formulas()
    
    # Try to find matching formula
    for formula in formulas:
        if formula.id.lower() in message.lower() or formula.name.lower() in message.lower():
            # Extract parameters from message (simplified)
            params = _extract_params_from_message(message, formula)
            
            try:
                result = execute_formula(formula.id, params)
                return {
                    "formula_used": formula.name,
                    "formula_id": formula.id,
                    "inputs": params,
                    "result": result.get("result"),
                    "unit": result.get("unit")
                }
            except Exception as e:
                return {"error": str(e), "formula_attempted": formula.id}
    
    return {"error": "No matching formula found", "available_formulas": [f.id for f in formulas[:5]]}


def _extract_params_from_message(message: str, formula) -> Dict[str, float]:
    """Extract numeric parameters from message."""
    import re
    params = {}
    
    # Find all numbers in message
    numbers = re.findall(r'(\d+\.?\d*)', message)
    
    for i, input_def in enumerate(formula.inputs):
        if i < len(numbers):
            try:
                params[input_def.name] = float(numbers[i])
            except:
                pass
    
    return params


def _format_formula_response(result: Dict[str, Any]) -> str:
    """Format formula execution result for user."""
    if "error" in result:
        return f"❌ Error: {result['error']}"
    
    return f"""📐 **Calculation Result**

**Formula:** {result.get('formula_used', 'Unknown')}
**Inputs:** {result.get('inputs', {})}

**Result:** {result.get('result')} {result.get('unit', '')}
"""


async def _handle_reasoning_request(action: str, message: str, context: Dict) -> Dict[str, Any]:
    """Handle reasoning engine requests."""
    # Placeholder - would integrate with reasoning engine
    return {
        "action": action,
        "analysis": f"Reasoning analysis for: {message[:50]}...",
        "confidence": 0.85,
        "recommendations": []
    }


async def _handle_workflow_request(action: str, message: str, context: Dict) -> Dict[str, Any]:
    """Handle orchestrator workflow requests."""
    # Placeholder - would run actual workflow
    return {
        "workflow": action,
        "summary": f"Executed {action} workflow",
        "steps_completed": 3,
        "total_steps": 5
    }


async def _call_llm_for_response(message: str, action: str) -> str:
    """Call LLM for general responses."""
    # Placeholder - would call DeepSeek
    return f"I understood your message about '{message[:30]}...' (detected action: {action}). How can I help further?"
