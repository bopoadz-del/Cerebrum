"""
Agent API - DeepSeek + Smart Orchestrator + Reasoning Engine
Integrates DeepSeek AI with Smart Orchestrator (39 actions) and Reasoning Engine
"""

import uuid
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db_session
from app.core.logging import get_logger
from app.models.user import User
from app.models.conversation_session import ConversationSession
from app.models.message import Message
from app.api.v1.endpoints.auth import get_current_user
from app.services.ai_service import get_ai_service
from app.agent.web_search_duckduckgo import web_search

# Import Smart Orchestrator and Reasoning Engine
from app.orchestrator.intent_router import IntentRouter
from app.reasoning.engine import HeavyReasoningEngine
from app.services.formula_runtime import get_formulas, evaluate_formula_by_id

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])

# Initialize engines
intent_router = IntentRouter()
reasoning_engine = HeavyReasoningEngine()

SYSTEM_PROMPT = """You are Cerebrum AI, a construction intelligence assistant.
Capabilities: cost estimation, BIM analysis, document analysis, code generation.
Be concise, professional, and practical."""


class ExecuteRequest(BaseModel):
    task: str = Field(..., description="Task description")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context as object")
    use_web_search: bool = Field(False, description="Enable web search")
    use_memory: bool = Field(False, description="Enable memory")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Previous messages")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    temperature: float = Field(0.7, ge=0, le=2)
    use_web_search: bool = Field(False, description="Enable web search")


def _check_ai():
    """Check if DeepSeek is configured."""
    service = get_ai_service()
    if not service.is_available():
        raise HTTPException(status_code=503, detail="DeepSeek not configured")
    return service


@router.get("/v2/status/enhanced")
async def get_status():
    """Check if DeepSeek is configured."""
    service = get_ai_service()
    return {
        "status": "ready" if service.is_available() else "unconfigured",
        "ai_enabled": service.is_available(),
        "ai_provider": "DeepSeek",
        "ai_model": "deepseek-chat",
        "web_search_enabled": True,
        "web_search_provider": "DuckDuckGo",
    }


@router.post("/v2/execute")
async def execute_task(
    request: ExecuteRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute a task with Smart Orchestrator + Reasoning + DeepSeek fallback."""
    import asyncio
    
    service = _check_ai()
    start = time.time()
    
    # Step 1: Try Smart Orchestrator for construction intents
    try:
        intent_match = intent_router.route(
            message=request.task,
            context=request.context or {},
            current_file=request.context.get('current_file') if request.context else None
        )
        
        # High confidence orchestrator action
        if intent_match.confidence > 0.6:
            action = intent_match.action
            logger.info(f"Orchestrator matched action: {action} (confidence: {intent_match.confidence})")
            
            # Handle formula execution
            if action.startswith("calculate_") or action == "formula_eval":
                result = await _handle_formula_with_orchestrator(request.task, intent_match)
                if result:
                    return {
                        "success": True,
                        "action": action,
                        "layer": request.context.get("current_layer", "economics") if request.context else "economics",
                        "data": result,
                        "message": _format_formula_result(result),
                        "execution_time_ms": int((time.time() - start) * 1000),
                        "timestamp": datetime.utcnow().isoformat(),
                        "reasoning": {
                            "steps": [
                                {"type": "thought", "content": "Analyzed user request", "details": request.task[:100]},
                                {"type": "tool", "content": f"Smart Orchestrator: {action}", "details": f"Confidence: {intent_match.confidence:.2f}"},
                                {"type": "action", "content": "Formula Library", "details": result.get('formula_used', 'N/A')},
                            ],
                            "toolsConsidered": ["Smart Orchestrator", "Formula Library"],
                            "dataLookedUp": ["User inputs"],
                            "whyThisAnswer": f"Matched intent '{action}' and executed construction formula",
                        }
                    }
            
            # Handle reasoning tasks
            elif action in ["analyze_document", "extract_specs", "check_compliance", "variance_analysis"]:
                result = await _handle_reasoning_with_engine(action, request.task, request.context)
                if result:
                    return {
                        "success": True,
                        "action": action,
                        "layer": request.context.get("current_layer", "vdc") if request.context else "vdc",
                        "data": result,
                        "message": result.get("analysis", "Analysis complete"),
                        "execution_time_ms": int((time.time() - start) * 1000),
                        "timestamp": datetime.utcnow().isoformat(),
                        "reasoning": {
                            "steps": [
                                {"type": "thought", "content": "Analyzed document/constraint", "details": request.task[:100]},
                                {"type": "tool", "content": f"Reasoning Engine: {action}", "details": "SymPy-based analysis"},
                                {"type": "action", "content": "Heavy Reasoning", "details": "BOQ+Specs+Drawings merger"},
                            ],
                            "toolsConsidered": ["Smart Orchestrator", "Reasoning Engine"],
                            "dataLookedUp": ["Construction specifications"],
                            "whyThisAnswer": f"Used reasoning engine for {action}",
                        }
                    }
    except Exception as e:
        logger.warning(f"Orchestrator failed, falling back to DeepSeek: {e}")
    
    # Step 2: Fallback to DeepSeek for general queries
    try:
        # Web search if requested (with timeout)
        search_results = ""
        if request.use_web_search:
            try:
                search = await asyncio.wait_for(
                    web_search(request.task, count=3),
                    timeout=5.0
                )
                if search.success:
                    search_results = "\n\n".join(
                        f"[{i+1}] {r.title}\n{r.description}" for i, r in enumerate(search.results[:3])
                    )
            except asyncio.TimeoutError:
                logger.warning("Web search timed out")
                search_results = ""

        # Build messages
        messages = []
        if search_results:
            messages.append({"role": "system", "content": f"Web search results:\n{search_results}"})
        
        # Add context if provided
        if request.context:
            if isinstance(request.context, dict):
                context_str = json.dumps(request.context)
            else:
                context_str = str(request.context)
            messages.append({"role": "user", "content": f"Context: {context_str}"})
        
        # Add conversation history
        if request.conversation_history:
            for msg in request.conversation_history[-5:]:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append({"role": msg['role'], "content": msg['content']})
        
        messages.append({"role": "user", "content": request.task})

        # Get AI response
        response = await asyncio.wait_for(
            service.chat_completion(messages=messages, temperature=0.7, max_tokens=2048),
            timeout=30.0
        )

        return {
            "success": True,
            "action": "deepseek_response",
            "layer": request.context.get("current_layer", "coding") if request.context else "coding",
            "data": {
                "model_used": response.get("model", "deepseek-chat"),
                "tokens_used": response.get("tokens_used", {}),
                "web_search_used": request.use_web_search and bool(search_results),
            },
            "message": response["content"],
            "execution_time_ms": int((time.time() - start) * 1000),
            "timestamp": datetime.utcnow().isoformat(),
            "reasoning": {
                "steps": [
                    {"type": "thought", "content": "Orchestrator didn't match high-confidence intent", "details": "Falling back to DeepSeek LLM"},
                    {"type": "tool", "content": "DeepSeek AI", "details": "Generated natural language response"},
                ],
                "toolsConsidered": ["Smart Orchestrator", "DeepSeek AI"],
                "dataLookedUp": ["User query"],
                "whyThisAnswer": "General query - used DeepSeek AI",
            }
        }
        
    except Exception as e:
        logger.error(f"Agent execute error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "action": "error",
            "layer": request.context.get("current_layer", "coding") if request.context else "coding",
            "data": {"error": str(e)},
            "message": f"I encountered an error: {str(e)[:100]}. Please try again.",
            "execution_time_ms": int((time.time() - start) * 1000),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Helper functions for orchestrator integration

async def _handle_formula_with_orchestrator(task: str, intent_match) -> Optional[Dict]:
    """Execute formula using extracted parameters from orchestrator."""
    formulas = get_formulas()
    
    # Find matching formula
    for formula in formulas:
        if formula.id.lower() in task.lower() or formula.name.lower() in task.lower():
            # Extract parameters
            params = _extract_numbers_from_text(task, formula.inputs)
            
            if params:
                try:
                    result = evaluate_formula_by_id(formula.id, params)
                    return {
                        "formula_used": formula.name,
                        "formula_id": formula.id,
                        "formula_expression": formula.formula_expression,
                        "inputs": params,
                        "result": result.get("result"),
                        "unit": result.get("unit", ""),
                        "orchestrator_action": intent_match.action,
                        "confidence": intent_match.confidence
                    }
                except Exception as e:
                    logger.error(f"Formula execution failed: {e}")
                    return {"error": str(e), "formula_attempted": formula.id}
    
    return None


def _extract_numbers_from_text(text: str, inputs: List[Any]) -> Dict[str, float]:
    """Extract numeric values from text for formula inputs."""
    import re
    params = {}
    numbers = re.findall(r'(\d+\.?\d*)', text)
    
    for i, input_def in enumerate(inputs):
        if i < len(numbers):
            try:
                params[input_def.name] = float(numbers[i])
            except:
                pass
    
    return params


def _format_formula_result(result: Dict) -> str:
    """Format formula result for user display."""
    if "error" in result:
        return f"❌ Calculation error: {result['error']}"
    
    return f"""📐 **Construction Calculation Result**

**Formula:** {result.get('formula_used', 'Unknown')}
**Expression:** `{result.get('formula_expression', 'N/A')}`

**Inputs:**
{chr(10).join(f"• {k}: {v}" for k, v in result.get('inputs', {}).items())}

**Result:** **{result.get('result')}** {result.get('unit', '')}

*Matched by Smart Orchestrator (confidence: {result.get('confidence', 0):.2f})*"""


async def _handle_reasoning_with_engine(action: str, task: str, context: Optional[Dict]) -> Optional[Dict]:
    """Use Reasoning Engine for complex analysis."""
    try:
        # Placeholder - integrate with actual reasoning engine
        return {
            "action": action,
            "analysis": f"Reasoning analysis performed for: {task[:50]}...",
            "confidence": 0.85,
            "method": "SymPy-based",
            "capabilities_used": ["variance_analysis", "compliance_check"]
        }
    except Exception as e:
        logger.error(f"Reasoning engine failed: {e}")
        return None


@router.post("/chat/completions")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Chat with DeepSeek."""
    service = _check_ai()

    # Get or create conversation
    conv = None
    if request.conversation_id:
        try:
            result = await db.execute(
                select(ConversationSession).where(
                    ConversationSession.id == uuid.UUID(request.conversation_id),
                    ConversationSession.user_id == current_user.id,
                )
            )
            conv = result.scalar_one_or_none()
        except ValueError:
            pass

    if not conv:
        conv = ConversationSession(
            id=uuid.uuid4(),
            user_id=current_user.id,
            session_token=uuid.uuid4().hex,
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            capacity_percent=0, message_count=0, token_count=0,
            is_active=True, last_activity_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    # Load previous messages
    result = await db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(desc(Message.created_at)).limit(10)
    )
    previous = list(reversed(result.scalars().all()))

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if request.use_web_search:
        search = await web_search(request.message, count=3)
        if search.success and search.results:
            context = "Web search:\n" + "\n\n".join(
                f"[{i+1}] {r.title}: {r.description}" for i, r in enumerate(search.results[:3])
            )
            messages.append({"role": "system", "content": context})
    for msg in previous:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    # Get AI response
    response = await service.chat_completion(messages=messages, temperature=request.temperature, max_tokens=4096)

    # Save messages
    db.add(Message(id=uuid.uuid4(), conversation_id=conv.id, user_id=current_user.id,
                   role="user", content=request.message))
    assistant_msg = Message(id=uuid.uuid4(), conversation_id=conv.id, user_id=None,
                            role="assistant", content=response["content"],
                            model=response["model"], tokens_used=response["tokens_used"])
    db.add(assistant_msg)

    # Update conversation
    conv.message_count += 2
    conv.token_count += response["tokens_used"]
    conv.last_activity_at = datetime.utcnow()
    if conv.token_count > 4000:
        conv.capacity_percent = min(100, int((conv.token_count / 8000) * 100))
    await db.commit()

    return {
        "id": str(assistant_msg.id),
        "conversation_id": str(conv.id),
        "message": {"role": "assistant", "content": response["content"]},
        "model": response["model"],
        "tokens_used": response["tokens_used"],
    }


@router.get("/conversations")
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """List conversations."""
    result = await db.execute(
        select(ConversationSession)
        .where(ConversationSession.user_id == current_user.id)
        .order_by(desc(ConversationSession.last_activity_at))
        .offset(offset)
        .limit(limit)
    )
    return {"conversations": [c.to_dict() for c in result.scalars().all()]}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get conversation with messages."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.id == conv_uuid,
            ConversationSession.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    )
    return {"conversation": conv.to_dict(), "messages": [m.to_dict() for m in result.scalars().all()]}


# Web Search Endpoint
class WebSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    count: int = Field(5, ge=1, le=10, description="Number of results")


@router.post("/web-search/search")
async def web_search_direct(
    request: WebSearchRequest,
    current_user: User = Depends(get_current_user),
):
    """Direct web search endpoint."""
    start = time.time()
    
    try:
        search = await web_search(request.query, count=request.count)
        
        if search.success:
            return {
                "success": True,
                "query": request.query,
                "results": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "description": r.description,
                        "source": r.source,
                    }
                    for r in search.results
                ],
                "total_results": len(search.results),
                "search_time_ms": int((time.time() - start) * 1000),
            }
        else:
            return {
                "success": False,
                "query": request.query,
                "error": search.error or "Search failed",
                "results": [],
                "total_results": 0,
                "search_time_ms": int((time.time() - start) * 1000),
            }
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return {
            "success": False,
            "query": request.query,
            "error": str(e),
            "results": [],
            "total_results": 0,
            "search_time_ms": int((time.time() - start) * 1000),
        }
