"""
Agent API - DeepSeek + DuckDuckGo Implementation
AI agent endpoints using DeepSeek for chat and DuckDuckGo for web search
"""

import uuid
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.models.conversation_session import ConversationSession
from app.models.message import Message
from app.api.v1.endpoints.auth import get_current_user
from app.services.ai_service import get_ai_service, AIService
from app.agent.web_search_duckduckgo import get_web_search_tool, web_search

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])

# Agent system prompt
AGENT_SYSTEM_PROMPT = """You are Cerebrum AI, a construction intelligence assistant powered by DeepSeek.

Your capabilities include:
- Construction cost estimation and RSMeans data lookups
- Building information modeling (BIM) analysis
- Document analysis (contracts, floor plans, schedules)
- Construction formulas and calculations
- Code generation for construction applications
- Project management assistance
- Web search for current information (via DuckDuckGo)

Guidelines:
- Be concise, professional, and practical
- Provide actionable insights
- Reference industry standards when relevant
- If you don't know something, say so
- Use construction terminology appropriately
- When asked about costs, provide ranges with context about location factors

You have access to web search via DuckDuckGo for current information."""

# Request/Response Models
class AgentExecuteRequest(BaseModel):
    task: str = Field(..., description="Task description for the agent")
    context: Optional[str] = Field(None, description="Additional context for the task")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for continuity")
    use_web_search: bool = Field(False, description="Enable web search for this task")


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for persistence")
    temperature: float = Field(0.7, ge=0, le=2)
    use_web_search: bool = Field(False, description="Enable web search for current information")


class AgentResponse(BaseModel):
    id: str
    status: str
    result: Dict[str, Any]
    model_used: str
    tokens_used: int


class ChatResponse(BaseModel):
    id: str
    conversation_id: str
    message: Dict[str, str]
    model: str
    tokens_used: int


def generate_session_token() -> str:
    """Generate a random session token."""
    import secrets
    return secrets.token_urlsafe(32)


@router.get("/v2/status/enhanced")
async def get_agent_status():
    """Get agent status and available capabilities."""
    service = get_ai_service()
    
    return {
        "status": "ready" if service.is_available() else "unconfigured",
        "version": "2.0.0",
        "capabilities": ["chat", "code", "analysis", "documents", "web_search"],
        "ai_provider": "DeepSeek",
        "ai_model": "deepseek-chat (V3)",
        "ai_enabled": service.is_available(),
        "web_search_provider": "DuckDuckGo (FREE)",
        "web_search_enabled": True,
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek V3", "provider": "deepseek"},
        ] if service.is_available() else [],
    }


@router.post("/v2/execute", response_model=AgentResponse)
async def execute_agent(
    request: AgentExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute an agent task with DeepSeek AI.
    
    This endpoint handles complex tasks like:
    - Code generation
    - Document analysis
    - Cost estimation
    - BIM analysis
    - Web search (if enabled)
    """
    service = get_ai_service()
    
    if not service.is_available():
        raise HTTPException(
            status_code=503,
            detail="DeepSeek AI not configured. Please set DEEPSEEK_API_KEY."
        )
    
    start_time = time.time()
    
    try:
        # Optionally perform web search
        web_search_results = None
        if request.use_web_search:
            logger.info(f"Performing web search for task: {request.task[:50]}...")
            search_response = await web_search(request.task, count=3)
            if search_response.success:
                web_search_results = "\n\n".join([
                    f"[{i+1}] {r.title}\n{r.description}\nURL: {r.url}"
                    for i, r in enumerate(search_response.results[:3])
                ])
        
        # Build messages for the task
        messages = []
        
        # Add web search results if available
        if web_search_results:
            messages.append({
                "role": "system",
                "content": f"Web search results for context:\n{web_search_results}"
            })
        
        messages.append({"role": "user", "content": f"Task: {request.task}"})
        
        if request.context:
            messages.insert(0, {"role": "user", "content": f"Context: {request.context}"})
        
        # Get AI response from DeepSeek
        response = await service.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
        )
        
        execution_time = time.time() - start_time
        
        logger.info(
            f"Agent task executed",
            task=request.task[:50],
            user_id=str(current_user.id),
            model=response["model"],
            tokens=response["tokens_used"],
            time_ms=int(execution_time * 1000),
            web_search=request.use_web_search,
        )
        
        return AgentResponse(
            id=str(uuid.uuid4()),
            status="completed",
            result={
                "message": response["content"],
                "task": request.task,
                "execution_time_ms": int(execution_time * 1000),
                "web_search_used": request.use_web_search,
            },
            model_used=response["model"],
            tokens_used=response["tokens_used"],
        )
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completion(
    request: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI chat completion with DeepSeek and conversation persistence.
    
    This endpoint:
    1. Creates or retrieves a conversation
    2. Loads previous messages for context
    3. Optionally performs web search (DuckDuckGo)
    4. Sends to DeepSeek for response
    5. Saves the exchange to database
    """
    service = get_ai_service()
    
    if not service.is_available():
        raise HTTPException(
            status_code=503,
            detail="DeepSeek AI not configured. Please set DEEPSEEK_API_KEY."
        )
    
    # Get or create conversation
    conversation = None
    if request.conversation_id:
        try:
            conv_uuid = uuid.UUID(request.conversation_id)
            result = await db.execute(
                select(ConversationSession).where(
                    ConversationSession.id == conv_uuid,
                    ConversationSession.user_id == current_user.id
                )
            )
            conversation = result.scalar_one_or_none()
        except ValueError:
            pass
    
    if not conversation:
        # Create new conversation
        from datetime import timedelta
        conversation = ConversationSession(
            id=uuid.uuid4(),
            user_id=current_user.id,
            session_token=generate_session_token(),
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            capacity_percent=0,
            message_count=0,
            token_count=0,
            is_active=True,
            last_activity_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    
    # Load previous messages for context (last 10)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(desc(Message.created_at))
        .limit(10)
    )
    previous_messages = list(reversed(result.scalars().all()))  # Oldest first
    
    # Build message list for AI
    messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
    
    # Optionally perform web search
    if request.use_web_search:
        logger.info(f"Performing web search for: {request.message[:50]}...")
        search_response = await web_search(request.message, count=3)
        if search_response.success and search_response.results:
            search_context = "Web search results:\n" + "\n\n".join([
                f"[{i+1}] {r.title}: {r.description}"
                for i, r in enumerate(search_response.results[:3])
            ])
            messages.append({"role": "system", "content": search_context})
    
    for msg in previous_messages:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Add current user message
    messages.append({"role": "user", "content": request.message})
    
    try:
        # Get AI response from DeepSeek
        response = await service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=4096,
        )
        
        # Save user message to database
        user_message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            user_id=current_user.id,
            role="user",
            content=request.message,
            model=None,
            tokens_used=None,
        )
        db.add(user_message)
        
        # Save assistant response to database
        assistant_message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            user_id=None,  # Assistant has no user
            role="assistant",
            content=response["content"],
            model=response["model"],
            tokens_used=response["tokens_used"],
        )
        db.add(assistant_message)
        
        # Update conversation stats
        conversation.message_count += 2
        conversation.token_count += response["tokens_used"]
        conversation.last_activity_at = datetime.utcnow()
        
        # Simple capacity estimation (rough approximation)
        if conversation.token_count > 4000:
            conversation.capacity_percent = min(100, int((conversation.token_count / 8000) * 100))
        
        await db.commit()
        
        logger.info(
            f"Agent chat completed",
            conversation_id=str(conversation.id),
            user_id=str(current_user.id),
            model=response["model"],
            tokens=response["tokens_used"],
            web_search=request.use_web_search,
        )
        
        return ChatResponse(
            id=str(assistant_message.id),
            conversation_id=str(conversation.id),
            message={
                "role": "assistant",
                "content": response["content"],
            },
            model=response["model"],
            tokens_used=response["tokens_used"],
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Chat completion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


@router.get("/conversations")
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's conversations."""
    result = await db.execute(
        select(ConversationSession)
        .where(ConversationSession.user_id == current_user.id)
        .order_by(desc(ConversationSession.last_activity_at))
        .offset(offset)
        .limit(limit)
    )
    conversations = result.scalars().all()
    
    return {
        "conversations": [conv.to_dict() for conv in conversations],
        "total": len(conversations),
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation with all messages."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")
    
    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.id == conv_uuid,
            ConversationSession.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    return {
        "conversation": conversation.to_dict(),
        "messages": [msg.to_dict() for msg in messages],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")
    
    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.id == conv_uuid,
            ConversationSession.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await db.delete(conversation)
    await db.commit()
    
    logger.info(f"Conversation deleted: {conversation_id} by user {current_user.id}")
    
    return {"success": True, "message": "Conversation deleted"}
