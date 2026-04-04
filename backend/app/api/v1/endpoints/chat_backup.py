"""
Chat Completions API Endpoint - Enhanced with Kimi-like Capabilities
OpenAI-compatible chat completions for Cerebrum AI

New Features:
- Web search integration
- Code execution capabilities
- Image understanding
- Enhanced document analysis
- Long context support
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any, Union
import time
import os
import json
import asyncio
from datetime import datetime

from app.agent.enhanced_core import get_enhanced_agent, initialize_agent, AgentLayer
from app.agent.web_search import get_web_search_tool, WebSearchResponse
from app.core.logging import get_logger
from app.errors import format_error_response
from app.api.deps import get_current_user, User

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Economics query keywords for routing
ECONOMICS_KEYWORDS = [
    'cost', 'price', 'budget', 'estimate', 'concrete', 'building', 'sq ft',
    'square feet', 'square foot', 'cubic', 'meters', 'masonry', 'steel', 'wood',
    'drywall', 'paint', 'flooring', 'roofing', 'electrical', 'plumbing', 'hvac',
    'excavation', 'rebar', 'formwork', 'quantity', 'quantities', 'material',
    'labor', 'rsmeans', 'csi', 'division', 'unit price', 'cubic meters',
    'cubic feet', 'square meters', 'square footage'
]

# Web search trigger keywords
WEBSEARCH_KEYWORDS = [
    'search', 'look up', 'find', 'latest', 'current', 'news', 'recent',
    'what is', 'who is', 'where is', 'when did', 'how to', 'why does',
    'weather', 'stock', 'price of', 'cost of', 'market', 'today'
]

# Code execution trigger keywords
CODE_KEYWORDS = [
    'calculate', 'compute', 'solve', 'plot', 'graph', 'analyze data',
    'run code', 'execute', 'python', 'code:', '```python'
]


def is_economics_query(message: str) -> bool:
    """Check if the message is an economics/construction cost query."""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in ECONOMICS_KEYWORDS)


def is_web_search_query(message: str) -> tuple[bool, str]:
    """
    Check if the message should trigger web search.
    Returns (should_search, extracted_query)
    """
    message_lower = message.lower()
    
    # Check for explicit search commands
    if message_lower.startswith('/search ') or message_lower.startswith('search for '):
        query = message[message_lower.find(' '):].strip()
        return True, query
    
    # Check for search keywords
    if any(kw in message_lower for kw in WEBSEARCH_KEYWORDS):
        # Extract the search-worthy part
        return True, message
    
    return False, message


def is_code_execution_query(message: str) -> bool:
    """Check if the message should trigger code execution."""
    message_lower = message.lower()
    
    # Check for code blocks
    if '```python' in message or '```py' in message:
        return True
    
    # Check for code keywords
    if any(kw in message_lower for kw in CODE_KEYWORDS):
        return True
    
    return False


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    attachments: Optional[List[Dict[str, Any]]] = None


class ChatCompletionRequest(BaseModel):
    model: str = "cerebrum-default"
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192)
    stream: bool = False
    conversation_id: Optional[str] = None
    enable_web_search: Optional[bool] = True
    enable_code_execution: Optional[bool] = True


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage
    web_search_results: Optional[List[Dict]] = None
    code_execution: Optional[Dict] = None


# ============================================================================
# Web Search Integration
# ============================================================================

async def perform_web_search(query: str, count: int = 5) -> Optional[WebSearchResponse]:
    """Perform web search and return results."""
    try:
        tool = get_web_search_tool()
        result = await tool.search(query, count=count)
        return result
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return None


def format_search_results_for_chat(search_response: WebSearchResponse) -> str:
    """Format web search results for inclusion in chat response."""
    if not search_response or not search_response.success:
        return ""
    
    if not search_response.results:
        return f"\n\n🔍 I searched for '{search_response.query}' but didn't find any results."
    
    lines = [
        f"\n\n🔍 **Web Search Results** for \"{search_response.query}\":\n",
        f"Found {search_response.total_results} results:\n"
    ]
    
    for i, result in enumerate(search_response.results[:5], 1):
        lines.append(f"\n**{i}. {result.title}**")
        lines.append(f"{result.description[:200]}..." if len(result.description) > 200 else result.description)
        lines.append(f"*Source: {result.source}*")
    
    return "\n".join(lines)


# ============================================================================
# Code Execution Integration
# ============================================================================

async def execute_code_in_chat(code: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """Execute code and return results for chat."""
    try:
        from app.services.code_execution import get_code_execution_service
        
        service = get_code_execution_service()
        result = await service.execute(code, context=context)
        
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
            "figures": result.figures,
            "variables": result.variables
        }
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        return {
            "success": False,
            "error": f"Code execution failed: {str(e)}"
        }


def format_code_result_for_chat(code_result: Dict) -> str:
    """Format code execution results for chat response."""
    if not code_result.get("success"):
        error = code_result.get("error", "Unknown error")
        return f"\n\n⚠️ **Code Execution Error:**\n```\n{error}\n```"
    
    lines = ["\n\n💻 **Code Execution Results:**\n"]
    
    if code_result.get("output"):
        output = code_result["output"]
        if len(output) > 1000:
            output = output[:1000] + "\n... (output truncated)"
        lines.append(f"**Output:**\n```\n{output}\n```")
    
    if code_result.get("figures"):
        lines.append(f"\n📊 Generated {len(code_result['figures'])} figure(s)")
    
    lines.append(f"\n⏱️ Execution time: {code_result.get('execution_time_ms', 0):.0f}ms")
    
    return "\n".join(lines)


# ============================================================================
# Image Understanding Integration
# ============================================================================

async def analyze_image_for_chat(
    image_data: Union[bytes, str],
    prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze image and return results for chat."""
    try:
        from app.services.image_understanding import get_image_understanding_service, AnalysisType
        
        service = get_image_understanding_service()
        result = await service.analyze_image(
            image_data,
            analysis_type=AnalysisType.GENERAL,
            prompt=prompt
        )
        
        return result.to_dict()
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return {
            "success": False,
            "error": f"Image analysis failed: {str(e)}"
        }


# ============================================================================
# Main Chat Completion Endpoint
# ============================================================================

@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint with Kimi-like capabilities.
    
    Features:
    - Conversational AI responses
    - Automatic web search for relevant queries
    - Code execution for calculations and data analysis
    - Economics/construction cost queries
    - Long conversation context support
    """
    start_time = time.time()
    
    try:
        # Get the last user message
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "We need your message to respond.",
                    "suggestion": "Please include at least one user message in your request.",
                    "category": "validation",
                    "retry_allowed": True,
                }
            )
        
        last_message = user_messages[-1].content
        
        # Build conversation context from previous messages (support long context)
        conversation_history = []
        total_context_length = 0
        max_context_length = 8000  # Support long context
        
        for msg in reversed(request.messages[:-1]):  # Most recent first
            msg_text = f"{msg.role}: {msg.content}"
            if total_context_length + len(msg_text) < max_context_length:
                conversation_history.insert(0, msg_text)
                total_context_length += len(msg_text)
            else:
                break
        
        context_text = "\n".join(conversation_history)
        
        # Initialize response components
        response_text = ""
        web_search_results = None
        code_execution_result = None
        
        # Ensure agent is initialized
        try:
            agent = await initialize_agent()
        except Exception as init_error:
            logger.error(f"Agent initialization failed: {init_error}")
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Service temporarily unavailable. Please try again in a moment.",
                    "suggestion": "The AI agent is still warming up. Retry your request.",
                    "category": "service_unavailable",
                    "retry_allowed": True,
                }
            )
        
        # Determine query type and route appropriately
        message_lower = last_message.lower().strip()
        
        # Check for pure greetings
        simple_greetings = ['hello', 'hi', 'hey', 'greetings']
        is_just_greeting = (
            any(message_lower == g or message_lower == g + '!' for g in simple_greetings) or
            len(message_lower) < 10
        )
        
        # Check for help queries
        is_help_query = any(phrase in message_lower for phrase in ['what can you do', 'who are you', 'help', 'what do you do'])
        
        # Check for web search query
        should_search, search_query = is_web_search_query(last_message)
        
        # Check for code execution
        should_execute_code = request.enable_code_execution and is_code_execution_query(last_message)
        
        # Check for economics query
        is_economics = is_economics_query(last_message) and not is_just_greeting and not is_help_query
        
        # Route to appropriate handler
        if is_just_greeting or is_help_query:
            # Direct conversational response
            response_text = generate_conversational_response(last_message, context_text)
            
        elif should_execute_code and '```python' in last_message:
            # Extract and execute code
            code = extract_code_from_message(last_message)
            code_execution_result = await execute_code_in_chat(code)
            
            # Generate response with code results
            response_text = generate_code_response(last_message, code_execution_result)
            
        elif should_search and request.enable_web_search:
            # Perform web search and include results
            search_response = await perform_web_search(search_query)
            
            if search_response and search_response.success:
                web_search_results = [
                    {
                        "title": r.title,
                        "url": r.url,
                        "description": r.description,
                        "source": r.source
                    }
                    for r in search_response.results
                ]
                
                # Generate response with search context
                search_context = format_search_results_for_chat(search_response)
                response_text = await generate_search_enhanced_response(
                    agent, last_message, context_text, search_context
                )
            else:
                # Fall back to normal response
                response_text = await generate_agent_response(agent, last_message, context_text, request)
                
        elif is_economics:
            # Route economics queries to economics layer
            response_text = await handle_economics_query(agent, last_message, context_text)
            
        else:
            # Default: use agent for complex tasks
            response_text = await generate_agent_response(agent, last_message, context_text, request)
        
        # Calculate token counts (rough estimation)
        prompt_tokens = len(" ".join([m.content for m in request.messages]).s