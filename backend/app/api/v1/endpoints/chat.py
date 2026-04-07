"""
Chat Completions API Endpoint - LOCAL LLM VERSION
OpenAI-compatible chat completions with local inference
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import time
import re

from app.core.logging import get_logger
from app.services.local_llm import is_local_llm_available, get_local_llm
from app.services.document_analyzer import document_analyzer

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# File storage path (same as documents.py)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/document_uploads")

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
    file_keys: Optional[List[str]] = Field(default=None, description="File keys of uploaded attachments")


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


def calculate_concrete_volume(message: str) -> str:
    """Calculate concrete volume from dimensions in message."""
    import re
    
    # Look for dimension patterns like "10m x 8m x 0.5m" or "10 x 8 x 0.5"
    # Support various units: m, meters, ft, feet, ' (feet), " (inches)
    patterns = [
        # Metric: 10m x 8m x 0.5m or 10 m x 8 m x 0.5 m
        r'(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m?',
        # Imperial: 10ft x 8ft x 0.5ft or 10' x 8' x 6"
        r'(\d+\.?\d*)\s*(?:ft|feet|\')\s*[x×]\s*(\d+\.?\d*)\s*(?:ft|feet|\')\s*[x×]\s*(\d+\.?\d*)\s*(?:ft|feet|\'|in|inches|\")?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            try:
                length = float(match.group(1))
                width = float(match.group(2))
                depth = float(match.group(3))
                
                # Determine unit from message context
                is_metric = any(unit in message.lower() for unit in ['m ', 'meter', 'mtr', 'metre'])
                is_imperial = any(unit in message.lower() for unit in ["'", 'ft', 'feet', 'inch'])
                
                # Default to metric if no unit specified but values are small
                if not is_metric and not is_imperial:
                    is_metric = length < 100 and width < 100 and depth < 10
                
                if is_metric:
                    # Metric calculation (meters)
                    volume_m3 = length * width * depth
                    volume_ft3 = volume_m3 * 35.3147
                    volume_yd3 = volume_ft3 / 27
                    
                    # Estimate concrete cost
                    cost_low = volume_yd3 * 120
                    cost_high = volume_yd3 * 150
                    
                    return f"""📐 **Concrete Volume Calculation**

**Dimensions:**
• Length: {length} m
• Width: {width} m  
• Depth: {depth} m

**Volume:**
• **{volume_m3:.2f} cubic meters** (m³)
• {volume_ft3:.2f} cubic feet
• {volume_yd3:.2f} cubic yards

**Estimated Cost:**
• ${cost_low:,.0f} - ${cost_high:,.0f} (@ $120-150/yd³)

**Formula Used:**
```
Volume = Length × Width × Depth
Volume = {length} × {width} × {depth} = {volume_m3:.2f} m³
```

*Note: Cost estimate is for ready-mix concrete only. Does not include labor, forms, or reinforcement.*"""
                else:
                    # Imperial calculation (feet)
                    volume_ft3 = length * width * depth
                    volume_yd3 = volume_ft3 / 27
                    volume_m3 = volume_ft3 / 35.3147
                    
                    # Estimate concrete cost
                    cost_low = volume_yd3 * 120
                    cost_high = volume_yd3 * 150
                    
                    return f"""📐 **Concrete Volume Calculation**

**Dimensions:**
• Length: {length} ft
• Width: {width} ft
• Depth: {depth} ft

**Volume:**
• **{volume_yd3:.2f} cubic yards** (yd³)
• {volume_ft3:.2f} cubic feet
• {volume_m3:.2f} cubic meters

**Estimated Cost:**
• ${cost_low:,.0f} - ${cost_high:,.0f} (@ $120-150/yd³)

**Formula Used:**
```
Volume = Length × Width × Depth
Volume = {length} × {width} × {depth} = {volume_ft3:.2f} ft³ = {volume_yd3:.2f} yd³
```

*Note: Cost estimate is for ready-mix concrete only. Does not include labor, forms, or reinforcement.*"""
            except (ValueError, IndexError):
                pass
    
    return None


async def handle_economics_query(message: str) -> str:
    """Handle economics/cost queries using direct API calls."""
    message_lower = message.lower()
    
    try:
        # Check for concrete volume calculation
        if any(word in message_lower for word in ['volume', 'calculate', 'calculation', 'cubic', 'm3', 'yd3']):
            if 'concrete' in message_lower or 'foundation' in message_lower or 'slab' in message_lower:
                volume_result = calculate_concrete_volume(message)
                if volume_result:
                    return volume_result
        
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
    """Generate a simple response - uses rule-based logic for construction queries."""
    message_lower = message.lower()
    
    # Check for greetings - use rule-based (fast)
    if message_lower.strip() in ['hello', 'hi', 'hey', 'greetings'] or len(message_lower.strip()) < 10:
        return generate_conversational_response(message, context)
    
    # Check for help - use rule-based
    if any(h in message_lower for h in ['what can you do', 'who are you', 'help']):
        return generate_conversational_response(message, context)
    
    # Check for concrete volume calculation FIRST (before general economics)
    if 'concrete' in message_lower and any(word in message_lower for word in ['volume', 'calculate', 'calculation', 'cubic', 'm3', 'yd3', 'foundation', 'slab']):
        volume_result = calculate_concrete_volume(message)
        if volume_result:
            return volume_result
    
    # Check for simple economics queries - use rule-based (fast, accurate)
    if is_simple_economics_query(message):
        return await handle_economics_query(message)
    
    # Fallback to rule-based conversational response
    return generate_conversational_response(message, context)


def is_simple_economics_query(message: str) -> bool:
    """Check if this is a simple cost query that rules can handle."""
    message_lower = message.lower()
    
    # Simple patterns that rules handle well
    simple_patterns = [
        r'cost of \w+',  # "cost of concrete"
        r'\d+\s*(sq ft|sf|square feet)',  # "5000 sq ft warehouse"
        r'price per \w+',  # "price per cubic yard"
        r'estimate for \w+',  # "estimate for office"
    ]
    
    for pattern in simple_patterns:
        if re.search(pattern, message_lower):
            return is_economics_query(message)
    
    return False


async def generate_local_llm_response(message: str, context: str) -> str:
    """Generate response using local LLM."""
    llm = get_local_llm()
    
    # Build system prompt for construction AI
    system_prompt = """You are Cerebrum AI, a construction intelligence assistant. 
You help with construction cost estimation, document analysis, and building information.
Be concise, professional, and practical. If you don't know something, say so.
If the user needs specific cost data, suggest they use the /cost command."""
    
    # Build messages for chat API
    messages = []
    if context:
        # Add context as previous messages
        for line in context.split('\n')[-5:]:  # Last 5 lines
            if line.startswith('user:'):
                messages.append({"role": "user", "content": line[5:].strip()})
            elif line.startswith('assistant:'):
                messages.append({"role": "assistant", "content": line[10:].strip()})
    
    messages.append({"role": "user", "content": message})
    
    # Generate response
    response = llm.chat(
        messages=messages,
        temperature=0.7,
        max_tokens=2048
    )
    
    return response


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
        
        # Process file_keys if provided
        file_context = ""
        if request.file_keys:
            logger.info(f"Processing {len(request.file_keys)} file keys: {request.file_keys}")
            file_parts = []
            for file_key in request.file_keys:
                # Try to find and read the file
                file_path = None
                for ext in ['.pdf', '.txt', '.md', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.webp', '']:
                    test_path = os.path.join(UPLOAD_DIR, f"{file_key}{ext}")
                    if os.path.exists(test_path):
                        file_path = test_path
                        break
                
                if file_path:
                    try:
                        # Extract text based on file type
                        if file_path.endswith('.pdf'):
                            from app.pipelines.ocr import TesseractOCR
                            ocr = TesseractOCR()
                            with open(file_path, 'rb') as f:
                                result = await ocr.process_pdf(f.read())
                            file_parts.append(f"[File: {file_key}]\n{result.text[:5000]}")
                        elif file_path.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                            from app.pipelines.ocr import TesseractOCR
                            ocr = TesseractOCR()
                            with open(file_path, 'rb') as f:
                                result = await ocr.process_image(f.read())
                            file_parts.append(f"[File: {file_key}]\n{result.text[:5000]}")
                        elif file_path.endswith(('.txt', '.md')):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            file_parts.append(f"[File: {file_key}]\n{content[:5000]}")
                        else:
                            file_parts.append(f"[File: {file_key}]\n[File uploaded successfully]")
                    except Exception as e:
                        logger.warning(f"Failed to extract text from {file_key}: {e}")
                        file_parts.append(f"[File: {file_key}]\n[File content available]")
                else:
                    logger.warning(f"File not found for key: {file_key}")
            
            if file_parts:
                file_context = "\n\n---\n\n" + "\n\n---\n\n".join(file_parts)
                logger.info(f"Added file context with {len(file_parts)} files")
        
        # Build conversation context
        conversation_history = []
        for msg in request.messages[:-1]:
            conversation_history.append(f"{msg.role}: {msg.content}")
        context_text = "\n".join(conversation_history[-5:])  # Last 5 messages
        
        # Append file context to the last message if available
        full_message = last_message
        if file_context:
            full_message += file_context
        
        # Generate response (simplified, no agent)
        response_text = await generate_simple_response(full_message, context_text)
        
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
    models = [
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
    
    # Add local LLM if available
    if is_local_llm_available():
        models.append({
            "id": "cerebrum-local",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "local-llm"
        })
    
    return {
        "object": "list",
        "data": models
    }


@router.get("/local-llm/status")
async def local_llm_status():
    """Check local LLM availability and model info."""
    available = is_local_llm_available()
    
    status = {
        "available": available,
        "model": "llama3.2" if available else None,
        "type": "local",
        "message": "Local LLM ready" if available else "Ollama not running or model not loaded"
    }
    
    if available:
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                status["loaded_models"] = [m["name"] for m in models]
        except:
            pass
    
    return status


@router.post("/analyze-document")
async def analyze_document(request: dict):
    """
    Analyze uploaded documents: contracts, floor plans, schedules.
    
    Request body:
    - text: Extracted text from the document
    - filename: Original filename
    - doc_type: 'contract', 'floor_plan', 'schedule', or 'auto'
    """
    try:
        text = request.get("text", "")
        filename = request.get("filename", "")
        doc_type = request.get("doc_type", "auto")
        
        if not text:
            return {
                "success": False,
                "error": "No document text provided"
            }
        
        # Auto-detect document type if not specified
        if doc_type == "auto":
            filename_lower = filename.lower()
            if any(word in filename_lower for word in ["contract", "agreement"]):
                doc_type = "contract"
            elif any(word in filename_lower for word in ["floor", "plan", "drawing"]):
                doc_type = "floor_plan"
            elif any(word in filename_lower for word in ["schedule", "primavera", "p6", "gantt"]):
                doc_type = "schedule"
            else:
                # Try to detect from content
                text_lower = text.lower()
                if "activity id" in text_lower or "duration" in text_lower:
                    doc_type = "schedule"
                elif "square feet" in text_lower or "dimension" in text_lower:
                    doc_type = "floor_plan"
                elif "contractor" in text_lower or "agreement" in text_lower:
                    doc_type = "contract"
                else:
                    doc_type = "general"
        
        # Analyze based on document type
        if doc_type == "contract":
            analysis = document_analyzer.analyze_contract(text, filename)
            return {
                "success": True,
                "doc_type": "contract",
                "analysis": {
                    "contract_type": analysis.contract_type,
                    "parties": analysis.parties,
                    "total_value": analysis.total_value,
                    "start_date": analysis.start_date,
                    "end_date": analysis.end_date,
                    "key_clauses": [
                        {
                            "section": c.section,
                            "title": c.title,
                            "content": c.content,
                            "risk_level": c.risk_level,
                            "key_points": c.key_points
                        } for c in analysis.key_clauses
                    ],
                    "risks": analysis.risks,
                    "recommendations": analysis.recommendations,
                    "payment_terms": analysis.payment_terms,
                    "termination_clause": analysis.termination_clause
                }
            }
        
        elif doc_type == "floor_plan":
            analysis = document_analyzer.analyze_floor_plan(text, filename)
            return {
                "success": True,
                "doc_type": "floor_plan",
                "analysis": {
                    "project_name": analysis.project_name,
                    "total_area_sqft": analysis.total_area_sqft,
                    "items": [
                        {
                            "category": item.category,
                            "description": item.description,
                            "quantity": item.quantity,
                            "unit": item.unit,
                            "area_sqft": item.area_sqft,
                            "notes": item.notes
                        } for item in analysis.items
                    ],
                    "summary_by_category": analysis.summary_by_category
                }
            }
        
        elif doc_type == "schedule":
            analysis = document_analyzer.analyze_schedule(text, filename)
            return {
                "success": True,
                "doc_type": "schedule",
                "analysis": {
                    "project_name": analysis.project_name,
                    "total_duration": analysis.total_duration,
                    "start_date": analysis.start_date,
                    "end_date": analysis.end_date,
                    "critical_path": analysis.critical_path,
                    "activities": [
                        {
                            "id": a.id,
                            "name": a.name,
                            "duration": a.duration,
                            "start_date": a.start_date,
                            "end_date": a.end_date,
                            "predecessors": a.predecessors,
                            "successors": a.successors,
                            "critical": a.critical,
                            "percent_complete": a.percent_complete
                        } for a in analysis.activities
                    ],
                    "milestones": analysis.milestones,
                    "risks": analysis.risks,
                    "recommendations": analysis.recommendations
                }
            }
        
        else:
            return {
                "success": True,
                "doc_type": "general",
                "analysis": {
                    "text_preview": text[:1000],
                    "word_count": len(text.split()),
                    "note": "Document type not recognized. Supported types: contract, floor_plan, schedule"
                }
            }
    
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }
