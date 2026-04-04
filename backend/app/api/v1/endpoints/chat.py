"""
Chat Completions API Endpoint - ULTRA SIMPLE VERSION
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import time
import re

router = APIRouter(prefix="/chat", tags=["chat"])

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
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in ECONOMICS_KEYWORDS)


def generate_greeting_response() -> str:
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

What would you like to work on today?"""


def generate_help_response() -> str:
    return """🧠 **I'm Cerebrum AI** — a construction intelligence platform.

**📱 Standard Mode:**
Quick commands for common tasks:
• `/cost <item>` — RSMeans cost data
• `/estimate <type> <size>` — Building estimates
• `/formula <query>` — Construction formulas
• Upload files for analysis

**🧠 Agent Mode:**
For complex, multi-step tasks with AI-powered capabilities.

**Switch modes:** Click the 🧠 **Agent Mode** toggle above the chat!"""


def handle_economics_query(message: str) -> str:
    message_lower = message.lower()
    
    # Warehouse cost
    if 'warehouse' in message_lower:
        size_match = re.search(r'(\d+)\s*(sq ft|square feet|sf)', message_lower)
        size = int(size_match.group(1)) if size_match else 10000
        cost_per_sf = 95
        total_cost = size * cost_per_sf
        return f"""🏗️ **Cost Estimate for Warehouse/Distribution**

📏 Size: {size:,} SF
📍 Location: National Average
💵 Base Cost/SF: ${cost_per_sf}
📊 Location Factor: 1.0

**📊 Total Estimated Cost: ${total_cost:,}**

*Note: This is a rough estimate. For detailed pricing, switch to 🧠 Agent Mode.*"""
    
    # Office cost
    if 'office' in message_lower:
        size_match = re.search(r'(\d+)\s*(sq ft|square feet|sf)', message_lower)
        size = int(size_match.group(1)) if size_match else 10000
        cost_per_sf = 225
        total_cost = size * cost_per_sf
        return f"""🏢 **Cost Estimate for Office Building**

📏 Size: {size:,} SF
📍 Location: National Average
💵 Base Cost/SF: ${cost_per_sf}
📊 Location Factor: 1.0

**📊 Total Estimated Cost: ${total_cost:,}**

*Note: This is a rough estimate. For detailed pricing, switch to 🧠 Agent Mode.*"""
    
    # Concrete cost
    if 'concrete' in message_lower:
        return """📊 **Concrete Cost Information**

**Ready-mix concrete (3000 psi):**
• National average: $120-$150 per cubic yard
• Price varies by location and quantity

**Common concrete formulas:**
• Volume = Length × Width × Depth
• For a 10×10×0.5 ft slab: 50 cubic feet = 1.85 cubic yards"""
    
    # Steel cost
    if 'steel' in message_lower:
        return """📊 **Structural Steel Cost Information**

**Wide flange beams (W-shape):**
• National average: $0.80-$1.20 per pound
• Price varies by size and grade

**Note:** Steel prices fluctuate with market conditions."""
    
    # Default economics response
    return """💰 **Construction Cost Information**

I can help you with:

**Building Estimates:**
• `/estimate warehouse 10000` — Warehouse costs
• `/estimate office 50000` — Office building costs

**Material Costs:**
• `/cost concrete` — Concrete prices
• `/cost steel` — Steel prices
• `/cost lumber` — Lumber prices

**Or switch to 🧠 Agent Mode** for detailed cost analysis!"""


def generate_default_response(message: str) -> str:
    return f"""I understand you're asking about: "{message[:50]}..."

I can help with construction costs, formulas, and document analysis. Try:

**Quick Commands:**
• `/cost concrete` — Search RSMeans database
• `/formula beam` — Find construction formulas
• `/estimate warehouse 100000` — Get building cost estimates
• `/help` — See all available commands

**Or switch to 🧠 Agent Mode** for AI-powered conversations!"""


@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    try:
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        last_message = user_messages[-1].content
        message_lower = last_message.lower().strip()
        
        # Determine response type
        if message_lower in ['hello', 'hi', 'hey', 'greetings'] or len(message_lower) < 10:
            response_text = generate_greeting_response()
        elif any(h in message_lower for h in ['what can you do', 'who are you', 'help']):
            response_text = generate_help_response()
        elif is_economics_query(last_message):
            response_text = handle_economics_query(last_message)
        else:
            response_text = generate_default_response(last_message)
        
        prompt_tokens = len(" ".join([m.content for m in request.messages]).split())
        completion_tokens = len(response_text.split())
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_text),
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
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content="I apologize, but I'm having trouble processing your request. Please try again."
                    ),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
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
            }
        ]
    }
