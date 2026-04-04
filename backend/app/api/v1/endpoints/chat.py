"""
Chat Completions API Endpoint - FIXED VERSION
OpenAI-compatible chat completions for Cerebrum AI
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import time
import re

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Economics query keywords
ECONOMICS_KEYWORDS = [
    'cost', 'price', 'budget', 'estimate', 'concrete', 'building', 'sq ft',
    'square feet', 'square foot', 'cubic', 'meters', 'masonry', 'steel', 'wood',
    'drywall', 'paint', 'flooring', 'roofing', 'electrical', 'plumbing', 'hvac',
    'excavation', 'rebar', 'formwork', 'quantity', 'quantities', 'material',
    'labor', 'rsmeans', 'csi', 'division', 'unit price', 'cubic meters',
    'cubic feet', 'square meters', 'square footage', 'warehouse', 'office'
]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "cerebrum-default"
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=4096)
    stream: bool = False
    conversation_id: Optional[str] = None


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


def is_economics_query(message: str) -> bool:
    """Check if the message is an economics/construction cost query."""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in ECONOMICS_KEYWORDS)


def generate_conversational_response(message: str, context: str) -> str:
    """Generate a conversational response based on the message content."""
    message_lower = message.lower()
    
    # Greeting responses
    is_pure_greeting = (
        message_lower.strip() in ['hello', 'hi', 'hey', 'greetings'] or
        message_lower.strip() in ['hello!', 'hi!', 'hey!', 'greetings!'] or
        len(message_lower.strip()) < 10
    )
    
    if is_pure_greeting:
        return """👋 Hello! I'm Cerebrum AI, your construction intelligence assistant.

I can help you with:

**🏗️ Construction & Cost Estimation:**
• RSMeans cost lookups (`/cost concrete`)
• Building cost estimates (`/estimate office 50000`)
• Construction formulas (`/formula beam`)

**📄 Documents & Analysis:**
• Upload and search documents
• Process invoices and reports
• Extract quantities from files

**🤖 Agent Mode (Complex Tasks):**
• Code generation and modification
• BIM model analysis and clash detection
• Multi-step autonomous workflows

**Try:** Type `/help` for all commands or switch to 🧠 **Agent Mode** for AI-powered tasks!

What would you like to work on today?"""
    
    # Help/what can you do
    if any(h in message_lower for h in ['what can you do', 'who are you', 'help', 'capabilities']):
        return """🧠 **I'm Cerebrum AI** — a construction intelligence platform with two modes:

**📱 Standard Mode (Current):**
Quick commands for common tasks:
• `/cost <item>` — RSMeans cost data
• `/estimate <type> <size>` — Building estimates
• `/formula <query>` — Construction formulas
• `/search <query>` — Document search
• Upload files for analysis

**🧠 Agent Mode:**
For complex, multi-step tasks:
• "Generate an API endpoint for material tracking"
• "Analyze this BIM model for clashes"
• "Create a cost report from uploaded documents"
• Self-modifying code capabilities

**Switch modes:** Click the 🧠 **Agent Mode** toggle above the chat!

What kind of help do you need?"""
    
    # Default response
    return f"""I understand you're asking about: "{message}"

I can help with construction costs, formulas, and document analysis. Try:

**Quick Commands:**
• `/cost concrete` — Search RSMeans database
• `/formula beam` — Find construction formulas
• `/estimate warehouse 100000` — Get building cost estimates
• `/help` — See all available commands

**Or switch to 🧠 Agent Mode** for AI-powered conversations and complex tasks!

Is there a specific construction calculation or document you'd like help with?"""


async def handle_economics_query(message: str) -> str:
    """Handle economics/cost queries using direct API calls."""
    message_lower = message.lower()
    
    try:
        # Check for building cost estimate
        if any(word in message_lower for word in ['warehouse', 'office', 'building', 'estimate', 'cost']):
            # Extract building type
            building_type = None
            if 'warehouse' in message_lower:
                building_type = 'warehouse'
            elif 'office' in message_lower:
                building_type = 'office'
            
            # Extract size
            import re
            size_match = re.search(r'(\d+)\s*(sq ft|square feet|sf)', message_lower)
            size = int(size_match.group(1)) if size_match else 10000
            
            # Calculate cost
            if building_type == 'warehouse':
                cost_per_sf = 95
                total_cost = size * cost_per_sf
                return f"""🏗️ **Cost Estimate for Warehouse/Distribution**

📏 Size: {size:,} SF
📍 Location: National Average
💵 Base Cost/SF: ${cost_per_sf}
📊 Location Factor: 1.0

**📊 Total Estimated Cost: ${total_cost:,}**

*Note: This is a rough estimate. For detailed pricing, switch to 🧠 Agent Mode or use `/estimate warehouse {size}`*"""
            
            elif building_type == 'office':
                cost_per_sf = 225
                total_cost = size * cost_per_sf
                return f"""🏢 **Cost Estimate for Office Building**

📏 Size: {size:,} SF
📍 Location: National Average  
💵 Base Cost/SF: ${cost_per_sf}
📊 Location Factor: 1.0

**📊 Total Estimated Cost: ${total_cost:,}**

*Note: This is a rough estimate. For detailed pricing, switch to 🧠 Agent Mode or use `/estimate office {size}`*"""
        
        # Check for material cost
        if any(word in message_lower for word in ['concrete', 'steel', 'lumber', 'material']):
            if 'concrete' in message_lower:
                return """📊 **Concrete Cost Information**

**Ready-mix concrete (3000 psi):**
• National average: $120-$150 per cubic yard
• Price varies by location and quantity

**For accurate pricing:**
• Use `/cost concrete` to search RSMeans database
• Or switch to 🧠 Agent Mode for detailed analysis

**Common concrete formulas:**
• Volume = Length × Width × Depth
• For a 10×10×0.5 ft slab: 50 cubic feet = 1.85 cubic yards"""
            
            elif 'steel' in message_lower:
                return """📊 **Structural Steel Cost Information**

**Wide flange beams (W-shape):**
• National average: $0.80-$1.20 per pound
• Price varies by size and grade

**For accurate pricing:**
• Use `/cost steel beam` to search RSMeans database
• Or switch to 🧠 Agent Mode for detailed analysis

**Note:** Steel prices fluctuate with market conditions."""
        
        # Generic economics response
        return """💰 **Construction Cost Information**

I can help you with:

**Building Estimates:**
• `/estimate warehouse 10000` — Warehouse costs
• `/estimate office 50000` — Office building costs

**Material Costs:**
• `/cost concrete` — Concrete prices
• `/cost steel` — Steel prices
• `/cost lumber` — Lumber prices

**Location Factors:**
• `/city New York` — Get location cost index

**Or switch to 🧠 Agent Mode** for detailed cost analysis and quantity takeoffs!"""
    
    except Exception as e:
        logger.error(f"Economics query handling failed: {e}")
        return """💰 **Construction Cost Assistant**

I can help you with construction costs! Try asking:

• "Cost of concrete per cubic yard"
• "Estimate for 5000 sq ft warehouse"  
• "Steel price per ton"
• "Building cost per square foot"

Or switch to 🧠 **Agent Mode** for complex calculations!"""


async def generate_simple_response(message: str, context: str) -> str:
    """Generate a simple response without using the agent system."""
    message_lower = message.lower()
    
    # Check for greetings
    if message_lower.strip() in ['hello', 'hi', 'hey', 'greetings'] or len(message_lower.strip()) < 10:
        return generate_conversational_response(message, context)
    
    # Check for help
    if any(h in message_lower for h in ['what can you do', 'who are you', 'help']):
        return generate_conversational_response(message, context)
    
    # Check for economics
    if is_economics_query(message):
        return await handle_economics_query(message)
    
    # Default response
    return generate_conversational_response(message, context)


@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.
    Provides conversational AI responses.
    """
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
        
        # Build conversation context
        conversation_history = []
        for msg in request.messages[:-1]:
            conversation_history.append(f"{msg.role}: {msg.content}")
        context_text = "\n".join(conversation_history[-5:])  # Last 5 messages
        
        # Generate response (simplified, no agent)
        response_text = await generate_simple_response(last_message, context_text)
        
        # Calculate token counts
        prompt_tokens = len(" ".join([m.content for m in request.messages]).split())
        completion_tokens = len(response_text.split())
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response_text
                    ),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        # Return a friendly error response
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content="I apologize, but I'm having trouble processing your request right now. Please try again in a moment."
                    ),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
        )


@router.get("/models")
async def list_models():
    """List available chat models."""
    return {
        "object": "list",
        "data": [
            {
                "id": "cerebrum-default",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "cerebrum-ai"
            },
            {
                "id": "cerebrum-agent",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "cerebrum-ai"
            }
        ]
    }
