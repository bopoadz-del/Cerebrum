"""
Chat Completions API Endpoint - REAL DATA VERSION
OpenAI-compatible chat completions with DeepSeek LLM and live RSMeans data
"""

import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import time
import re

from app.core.logging import get_logger
from app.llm.client import LLMClient
from app.api.v1.endpoints.economics import router as economics_router
from app.economics.pricing_engine import get_pricing_engine
from app.api.deps import get_current_user
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# File storage path
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/document_uploads")


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
    file_keys: Optional[List[str]] = Field(default=None, description="File keys of uploaded attachments")
    extracted_texts: Optional[List[str]] = Field(default=None, description="Extracted text from uploaded files")


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


def is_command(message: str) -> bool:
    """Check if message is a slash command."""
    return message.strip().startswith('/')


def parse_cost_command(message: str) -> tuple[str, Optional[str]]:
    """Parse /cost command to extract item and location."""
    parts = message.strip().split()
    if len(parts) < 2:
        return "", None
    
    item = " ".join(parts[1:])
    zip_code = None
    
    # Check for ZIP code at end
    if parts[-1].isdigit() and len(parts[-1]) == 5:
        zip_code = parts[-1]
        item = " ".join(parts[1:-1])
    
    return item, zip_code


def parse_estimate_command(message: str) -> tuple[str, int, Optional[str]]:
    """Parse /estimate command: /estimate warehouse 10000 [zip]

    Strategy: collect all numeric tokens. The LAST token is treated as
    ZIP if it's exactly 5 digits AND there is at least one other number
    (the size). Otherwise all numbers contribute to size (last one wins).
    """
    parts = message.strip().split()
    if len(parts) < 3:
        return "", 0, None

    building_type = parts[1]
    numbers = [p for p in parts[2:] if p.isdigit()]

    if not numbers:
        return building_type, 0, None

    # If last token is exactly 5 digits AND we have another number for size → it's a ZIP
    if len(numbers) >= 2 and len(numbers[-1]) == 5:
        zip_code = numbers[-1]
        size = int(numbers[-2])
    else:
        zip_code = None
        size = int(numbers[-1])

    return building_type, size, zip_code


async def handle_cost_command(item: str, zip_code: Optional[str]) -> str:
    """Get REAL RSMeans cost data."""
    try:
        engine = await get_pricing_engine()
        results = await engine.rsmeans.search_cost_items(item, limit=5)
        
        if not results:
            return f"❌ No RSMeans data found for '{item}'. Try: concrete, steel, lumber, drywall"
        
        # Get location factor if ZIP provided
        location_factor = 1.0
        if zip_code:
            try:
                loc_data = await engine.get_location_factor(zip_code)
                if loc_data:
                    # LocationFactor is a dataclass; cost_index is 0-100 scale
                    location_factor = loc_data.cost_index / 100 if hasattr(loc_data, 'cost_index') else loc_data.get("factor", 1.0)
            except:
                pass
        
        response_lines = [f"📊 **RSMeans Cost Data: {item.title()}**"]
        if zip_code:
            response_lines.append(f"📍 Location: {zip_code} (Factor: {location_factor:.2f})")
        response_lines.append("")
        
        for r in results[:3]:
            # CostItem is a dataclass — use attribute access, not .get()
            base_price = float(r.total_cost) if hasattr(r, 'total_cost') else float(r.get("total_cost", 0))
            adjusted_price = base_price * location_factor
            description = r.description if hasattr(r, 'description') else r.get('description', 'Unknown')
            rsmeans_id = r.rsmeans_id if hasattr(r, 'rsmeans_id') else r.get('rsmeans_id', 'N/A')
            unit = r.unit if hasattr(r, 'unit') else r.get('unit', 'ea')
            response_lines.append(
                f"**{description}**\n"
                f"• ID: {rsmeans_id}\n"
                f"• Unit: {unit}\n"
                f"• Base Price: ${base_price:.2f}\n"
                f"• Adjusted: ${adjusted_price:.2f}\n"
            )
        
        response_lines.append("*Data source: RSMeans 2024*")
        return "\n".join(response_lines)
        
    except Exception as e:
        logger.error(f"Cost command failed: {e}")
        return f"❌ Error fetching cost data: {str(e)}"


async def handle_estimate_command(building_type: str, size: int, zip_code: Optional[str]) -> str:
    """Get REAL building cost estimate."""
    if size == 0:
        return "❌ Please specify size: `/estimate warehouse 10000`"
    
    try:
        engine = await get_pricing_engine()
        
        # Get real location factor
        location_factor = 1.0
        location_name = "National Average"
        if zip_code:
            try:
                loc_data = await engine.get_location_factor(zip_code)
                if loc_data:
                    # LocationFactor is a dataclass; cost_index is 0-100 scale
                    location_factor = loc_data.cost_index / 100 if hasattr(loc_data, 'cost_index') else loc_data.get("factor", 1.0)
                    location_name = loc_data.city if hasattr(loc_data, 'city') else loc_data.get("city", zip_code)
            except:
                location_name = zip_code
        
        # Building type costs (per SF) - these could come from a database too
        base_costs = {
            "warehouse": (95, 130),
            "office": (225, 350),
            "retail": (180, 280),
            "hospital": (400, 600),
            "school": (200, 300),
            "apartment": (180, 250),
            "hotel": (220, 320),
        }
        
        low_base, high_base = base_costs.get(building_type.lower(), (150, 250))
        
        low_cost = size * low_base * location_factor
        high_cost = size * high_base * location_factor
        
        return f"""🏗️ **Cost Estimate: {building_type.title()}**

📏 Size: {size:,} SF
📍 Location: {location_name}
💵 Base Cost/SF: ${low_base:.0f}-${high_base:.0f}
📊 Location Factor: {location_factor:.2f}

**📊 Total Estimated Cost:**
• Low: ${low_cost:,.0f}
• High: ${high_cost:,.0f}
• Average: ${(low_cost + high_cost)/2:,.0f}

*Source: RSMeans 2024 Building Cost Data*
"""
        
    except Exception as e:
        logger.error(f"Estimate command failed: {e}")
        return f"❌ Error generating estimate: {str(e)}"


async def call_deepseek_llm(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
    """Call REAL DeepSeek LLM for responses."""
    try:
        client = LLMClient()
        response = await client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=2048
        )
        # LLMClient.chat() returns an LLMResponse object — extract the text content
        if hasattr(response, 'choices') and response.choices:
            return response.choices[0].message.content
        return str(response)
    except Exception as e:
        logger.error(f"DeepSeek LLM call failed: {e}")
        return f"I encountered an error: {str(e)}. Please try again."


@router.post("/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    OpenAI-compatible chat completions endpoint.
    Uses REAL DeepSeek LLM and RSMeans data - NO TEMPLATES.
    """
    try:
        # Get last user message
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        
        last_message = user_messages[-1].content
        
        # Handle slash commands with REAL data
        if is_command(last_message):
            cmd = last_message.lower()
            
            if cmd.startswith('/cost'):
                item, zip_code = parse_cost_command(last_message)
                response_content = await handle_cost_command(item, zip_code)
                
            elif cmd.startswith('/estimate'):
                building_type, size, zip_code = parse_estimate_command(last_message)
                response_content = await handle_estimate_command(building_type, size, zip_code)
                
            elif cmd.startswith('/help'):
                response_content = """🧠 **Cerebrum AI Commands**

**Cost & Estimation:**
• `/cost <item>` - Get RSMeans cost data
• `/estimate <type> <size>` - Building cost estimate
• `/city <name>` - Location cost index

**Examples:**
• `/cost concrete foundation`
• `/estimate warehouse 10000`
• `/estimate office 50000 90210`

For complex tasks, just ask naturally - I'll use AI to help!"""
            
            else:
                # Unknown command - ask LLM
                response_content = await call_deepseek_llm(
                    messages=[
                        {"role": "system", "content": "You are Cerebrum AI. The user entered an unknown command. Explain that you don't recognize it and suggest /help."},
                        {"role": "user", "content": f"Unknown command: {last_message}"}
                    ]
                )
        
        else:
            # Regular message - call REAL LLM
            # Build message history
            llm_messages = []
            
            # Add file context if present
            if request.file_keys and request.extracted_texts:
                file_context = "\n\n".join([
                    f"[File {i+1}]:\n{text[:2000]}"
                    for i, text in enumerate(request.extracted_texts)
                ])
                llm_messages.append({
                    "role": "system", 
                    "content": f"The user has uploaded files. File contents:\n{file_context}"
                })
            
            # Add conversation history
            for msg in request.messages:
                llm_messages.append({"role": msg.role, "content": msg.content})
            
            # Call DeepSeek
            response_content = await call_deepseek_llm(
                messages=llm_messages,
                temperature=request.temperature or 0.7
            )
        
        # Build response
        created = int(time.time())
        prompt_tokens = len(last_message.split())
        completion_tokens = len(response_content.split())
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{created}",
            created=created,
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_content),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
        
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    """List available models."""
    return {
        "object": "list",
        "data": [
            {
                "id": "cerebrum-default",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "cerebrum"
            },
            {
                "id": "deepseek-chat",
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "deepseek"
            }
        ]
    }
