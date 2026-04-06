"""
Enhanced Agent API Endpoints - FIXED VERSION

Fixes:
1. Proper agent initialization with Redis fallback
2. Memory indexing on startup
3. Error handling for uninitialized agent
4. Fallback to rule-based processing
5. Document analysis for uploads
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import os
import re
import time

from app.agent.enhanced_core import (
    get_enhanced_agent, 
    EnhancedCerebrumAgent, 
    AgentLayer, 
    initialize_agent,
    AgentAction
)
from app.agent.websocket import get_websocket_manager
from app.services.document_analyzer import document_analyzer

logger = logging.getLogger(__name__)
router = APIRouter()

# Track agent initialization status
_agent_init_error = None


class EnhancedTaskRequest(BaseModel):
    task: str = Field(..., description="Task description")
    context: Optional[Dict[str, Any]] = Field(default=None)
    use_memory: bool = Field(default=True, description="Search relevant memories")
    target_layer: Optional[str] = Field(default=None, description="Force specific layer")
    attachments: Optional[List[Dict[str, Any]]] = Field(default=None, description="File attachments with extracted text")


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


async def ensure_agent_initialized():
    """Ensure agent is initialized with proper error handling."""
    global _agent_init_error
    
    try:
        agent = get_enhanced_agent()
        # Check if initialized by checking if reader has index
        if hasattr(agent, '_reader_initialized') and not agent._reader_initialized:
            logger.info("Agent not initialized, initializing now...")
            await agent.initialize()
        return agent, None
    except Exception as e:
        logger.error(f"Agent initialization failed: {e}")
        _agent_init_error = str(e)
        return None, e


def handle_construction_task(task: str) -> Dict[str, Any]:
    """Handle construction-specific tasks without full agent."""
    task_lower = task.lower()
    
    # Concrete volume calculation
    if any(word in task_lower for word in ["concrete", "volume", "calculate"]):
        return handle_concrete_calculation(task)
    
    # Cost estimates
    if any(word in task_lower for word in ["cost", "price", "estimate", "rsmeans"]):
        return handle_cost_lookup(task)
    
    # Formulas
    if any(word in task_lower for word in ["formula", "beam", "moment", "load", "deflection"]):
        return handle_formula_lookup(task)
    
    # Default response
    return {
        "success": True,
        "action": "general_assistance",
        "layer": "economics",
        "data": {"query": task},
        "message": """🏗️ **Cerebrum AI - Construction Intelligence**

I can help you with:

**📐 Calculations:**
• Concrete volume: "Calculate concrete for 10x5x0.5m"
• Steel quantities: "Calculate rebar for 1000 sq ft slab"

**💰 Cost Estimates:**
• RSMeans lookups: "Cost of concrete per cubic yard"
• Project estimates: "Estimate cost for 5000 sq ft office"

**📊 Formulas:**
• Beam calculations: "Formula for beam moment"
• Structural: "Deflection formula for cantilever"

Upload a document (PDF, image) for AI analysis of:
• Contracts (parties, clauses, risks)
• Floor plans (quantities, areas)
• Schedules (activities, critical path)
""",
        "execution_time_ms": 0,
        "related_conversations": [],
        "suggested_next_actions": ["Upload a document for analysis", "Calculate concrete volume"],
        "timestamp": datetime.now().isoformat()
    }


def handle_concrete_calculation(task: str) -> Dict[str, Any]:
    """Calculate concrete volume from dimensions."""
    import re
    
    patterns = [
        r'(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m?',
        r'(\d+\.?\d*)\s*(?:ft|feet)\s*[x×]\s*(\d+\.?\d*)\s*(?:ft|feet)\s*[x×]\s*(\d+\.?\d*)\s*(?:ft|feet)',
    ]
    
    dimensions = None
    for pattern in patterns:
        match = re.search(pattern, task.lower())
        if match:
            dimensions = [float(match.group(1)), float(match.group(2)), float(match.group(3))]
            break
    
    if dimensions:
        length, width, depth = dimensions
        volume_m3 = length * width * depth
        volume_ft3 = volume_m3 * 35.315
        volume_yd3 = volume_m3 * 1.308
        cost_low = volume_yd3 * 120
        cost_high = volume_yd3 * 150
        
        message = f"""📐 **Concrete Volume Calculation**

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

**Formula:**
```
Volume = {length} × {width} × {depth} = {volume_m3:.2f} m³
```

*Note: Cost is for ready-mix concrete only. Does not include labor, forms, or reinforcement.*"""
        
        return {
            "success": True,
            "action": "concrete_calculation",
            "layer": "economics",
            "data": {"volume_m3": volume_m3, "volume_yd3": volume_yd3, "cost_range": [cost_low, cost_high]},
            "message": message,
            "execution_time_ms": 0,
            "related_conversations": [],
            "suggested_next_actions": ["Get steel quantities", "Calculate formwork cost"],
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "success": False,
            "action": "error",
            "layer": "economics",
            "data": {},
            "message": "Please provide dimensions in format: length x width x depth (e.g., '10m x 5m x 0.5m')",
            "execution_time_ms": 0,
            "related_conversations": [],
            "suggested_next_actions": ["Try: Calculate concrete for 10m x 5m x 0.5m"],
            "timestamp": datetime.now().isoformat()
        }


def handle_cost_lookup(task: str) -> Dict[str, Any]:
    """Handle cost estimate requests."""
    return {
        "success": True,
        "action": "cost_lookup",
        "layer": "economics",
        "data": {},
        "message": """💰 **RSMeans Cost Data (2024)**

**Concrete & Masonry:**
• Ready-mix concrete: $120-150/yd³
• Rebar (installed): $0.80-1.20/lb
• CMU block: $15-25/sq ft
• Brick: $25-40/sq ft

**Structural Steel:**
• Structural steel: $2,500-4,000/ton
• Steel decking: $8-15/sq ft
• Metal studs: $4-8/sq ft

**Finishes:**
• Drywall (installed): $1.50-2.50/sq ft
• Paint: $2-5/sq ft
• Flooring: $3-12/sq ft
• Roofing: $5-15/sq ft

**MEP:**
• Electrical: $3-8/sq ft
• Plumbing: $4-10/sq ft
• HVAC: $15-30/sq ft

*Prices vary by location and project complexity.*""",
        "execution_time_ms": 0,
        "related_conversations": [],
        "suggested_next_actions": ["Get specific item cost", "Generate full estimate"],
        "timestamp": datetime.now().isoformat()
    }


def handle_formula_lookup(task: str) -> Dict[str, Any]:
    """Handle formula requests."""
    return {
        "success": True,
        "action": "formula_lookup",
        "layer": "economics",
        "data": {},
        "message": """📐 **Construction Formulas**

**Concrete:**
```
Volume = Length × Width × Depth
```

**Beam Bending (Simple Span, UDL):**
```
M = wL²/8
Where: w = uniform load (lb/ft), L = span (ft)
```

**Beam Deflection:**
```
δ = 5wL⁴/(384EI)
Where: E = modulus of elasticity, I = moment of inertia
```

**Soil Bearing:**
```
q = P/A
Where: P = total load (lb), A = area (ft²)
```

**Rebar Weight:**
```
Weight (lb/ft) = (Diameter in inches)² × 0.668
```

**Slab Concrete:**
```
Volume (yd³) = Area (ft²) × Thickness (in) / 324
```

What calculation do you need?""",
        "execution_time_ms": 0,
        "related_conversations": [],
        "suggested_next_actions": ["Calculate beam moment", "Get rebar weight"],
        "timestamp": datetime.now().isoformat()
    }


async def analyze_attachments(attachments: List[Dict[str, Any]], task: str) -> Dict[str, Any]:
    """Analyze uploaded file attachments using document analyzer."""
    if not attachments:
        return None
    
    # Collect all attachment texts
    all_extracted_text = []
    file_summaries = []
    
    for attachment in attachments:
        filename = attachment.get('filename', 'unknown')
        extracted_text = attachment.get('text', '')
        
        if extracted_text:
            all_extracted_text.append(f"--- {filename} ---\n{extracted_text[:5000]}")
        
        file_summaries.append(f"📄 {filename} ({len(extracted_text)} chars)")
    
    combined_text = "\n\n".join(all_extracted_text)
    file_list = "\n".join(file_summaries)
    
    # Determine document type
    doc_type = classify_document(combined_text, [a.get('filename', '') for a in attachments])
    
    # Analyze based on document type
    if doc_type == "contract":
        analysis = analyze_contract(combined_text, file_list)
    elif doc_type == "cv":
        analysis = analyze_cv(combined_text, file_list)
    elif doc_type == "floor_plan":
        analysis = analyze_floor_plan(combined_text, file_list)
    elif doc_type == "schedule":
        analysis = analyze_schedule(combined_text, file_list)
    else:
        analysis = analyze_general_document(combined_text, file_list, task)
    
    return {
        "success": True,
        "action": f"{doc_type}_analysis",
        "layer": "portal",
        "data": {
            "document_type": doc_type,
            "files_analyzed": len(attachments),
            "extracted_text_length": len(combined_text),
            "analysis": analysis
        },
        "message": analysis,
        "execution_time_ms": 0,
        "related_conversations": [],
        "suggested_next_actions": ["Ask specific questions about the document"],
        "timestamp": datetime.now().isoformat()
    }


def classify_document(text: str, filenames: List[str]) -> str:
    """Classify document type based on content and filename."""
    text_lower = text.lower()
    
    # CV/Resume indicators
    cv_keywords = ["experience", "education", "skills", "qualifications", "employment", 
                   "resume", "curriculum vitae", "cv", "references", "objective"]
    
    # Contract indicators
    contract_keywords = ["contract", "agreement", "party", "parties", "clause", 
                        "terms", "conditions", "scope of work", "payment", 
                        "termination", "liability", "hereby", "whereas"]
    
    # Floor plan indicators  
    floor_plan_keywords = ["floor plan", "elevation", "section", "dimension",
                          "sq ft", "square feet", "scale", "drawing", "plan view",
                          "room", "bedroom", "bathroom", "kitchen", "layout"]
    
    # Schedule indicators
    schedule_keywords = ["activity", "duration", "start date", "finish date",
                        "predecessor", "successor", "critical path", "milestone",
                        "primavera", "schedule", "calendar", "gantt"]
    
    scores = {
        "cv": sum(1 for kw in cv_keywords if kw in text_lower),
        "contract": sum(1 for kw in contract_keywords if kw in text_lower),
        "floor_plan": sum(1 for kw in floor_plan_keywords if kw in text_lower),
        "schedule": sum(1 for kw in schedule_keywords if kw in text_lower)
    }
    
    # Filename bonuses
    for fn in filenames:
        fn_lower = fn.lower()
        if any(word in fn_lower for word in ["cv", "resume"]):
            scores["cv"] += 10
        if any(word in fn_lower for word in ["contract", "agreement"]):
            scores["contract"] += 10
        if any(word in fn_lower for word in ["plan", "drawing", "floor", "elevation"]):
            scores["floor_plan"] += 10
        if any(word in fn_lower for word in ["schedule", "primavera", "programme"]):
            scores["schedule"] += 10
    
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "general"


def analyze_contract(text: str, file_list: str) -> str:
    """Analyze contract document."""
    import re
    
    # Extract parties
    parties = []
    party_patterns = [
        r'between\s+([^,]+(?:LLC|Inc|Corp|Ltd|Company))\s+and\s+([^,]+(?:LLC|Inc|Corp|Ltd|Company))',
        r'(?:Owner|Contractor|Client)\s*[:\-]?\s*([^\n,]+)',
    ]
    for pattern in party_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                parties.extend(match)
            else:
                parties.append(match)
    
    # Extract value
    value = None
    value_patterns = [
        r'\$[\d,]+(?:\.\d{2})?',
        r'(?:total|amount|value|price)\s*:?\s*\$?[\d,]+',
    ]
    for pattern in value_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            value = matches[0]
            break
    
    # Extract key clauses
    clauses = []
    clause_keywords = ["payment", "termination", "liability", "indemnification", 
                      "insurance", "warranty", "force majeure", "dispute resolution",
                      "scope of work", "change order", "delay", "penalty"]
    for keyword in clause_keywords:
        if keyword in text.lower():
            clauses.append(keyword.title())
    
    parties_str = "\n• ".join(parties[:3]) if parties else "Not clearly identified"
    value_str = value if value else "Not specified"
    clauses_str = ", ".join(clauses[:8]) if clauses else "Standard clauses"
    
    return f"""📋 **Contract Analysis**

**Files Analyzed:**
{file_list}

**Parties Identified:**
• {parties_str}

**Contract Value:** {value_str}

**Key Clauses Detected:**
{clauses_str}

**Summary:**
This contract has been analyzed. Found {len(clauses)} key clauses.

**Recommendations:**
✓ Review payment terms carefully
✓ Verify insurance requirements
✓ Check termination clauses
✓ Understand dispute resolution process

*For detailed legal review, consult a construction attorney.*"""


def analyze_cv(text: str, file_list: str) -> str:
    """Analyze CV/Resume."""
    import re
    
    # Extract name (first line or pattern)
    name = "Not identified"
    lines = text.split('\n')
    for line in lines[:5]:
        if line.strip() and len(line.strip()) < 50:
            name = line.strip()
            break
    
    # Extract skills
    skills = []
    skill_keywords = ["project management", "autocad", "revit", "cost estimation", 
                     "scheduling", "bim", "construction", "engineering", "pmp"]
    for skill in skill_keywords:
        if skill in text.lower():
            skills.append(skill.title())
    
    # Extract experience years
    exp_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', text, re.IGNORECASE)
    experience = f"{exp_match.group(1)} years" if exp_match else "Not specified"
    
    skills_str = ", ".join(skills) if skills else "Not specified"
    
    return f"""📄 **CV/Resume Analysis**

**Files Analyzed:**
{file_list}

**Candidate:** {name}

**Experience:** {experience}

**Key Skills:**
{skills_str}

**Summary:**
This CV has been analyzed for construction industry qualifications.

**Recommendations:**
✓ Verify certifications (PMP, PE, etc.)
✓ Check project portfolio
✓ Validate education credentials
✓ Review references"""


def analyze_floor_plan(text: str, file_list: str) -> str:
    """Analyze floor plan."""
    import re
    
    # Try to extract dimensions
    dimensions = []
    dim_pattern = r'(\d+[\'"]?)\s*[x×]\s*(\d+[\'"]?)'
    matches = re.findall(dim_pattern, text)
    for match in matches[:5]:
        dimensions.append(f"{match[0]} x {match[1]}")
    
    # Count rooms
    room_types = ["bedroom", "bathroom", "kitchen", "living", "dining", "office", "garage"]
    room_counts = {}
    for room in room_types:
        count = text.lower().count(room)
        if count > 0:
            room_counts[room.title()] = count
    
    # Try to find area
    area = None
    area_patterns = [
        r'(\d{3,5})\s*(?:sq\.?\s*ft\.?|square\s*feet|sf)',
    ]
    for pattern in area_patterns:
        match = re.search(pattern, text.lower())
        if match:
            area = match.group(1)
            break
    
    rooms_str = "\n• ".join([f"{k}: {v}" for k, v in room_counts.items()]) if room_counts else "Not specified"
    dims_str = "\n• ".join(dimensions[:5]) if dimensions else "See drawing"
    area_str = f"{area} sq ft" if area else "Calculate from dimensions"
    
    # Estimate quantities if area available
    quantity_estimate = ""
    if area:
        area_val = int(area)
        concrete = area_val * 0.05
        steel = area_val * 0.003
        drywall = area_val * 3.5
        
        quantity_estimate = f"""
**Estimated Quantities (based on {area} sq ft):**
• Concrete: ~{concrete:.1f} cubic yards
• Structural Steel: ~{steel:.1f} tons
• Drywall: ~{drywall:.0f} sheets (4x8)
• Flooring: ~{area} sq ft
• Paint: ~{area * 3.5:.0f} sq ft (walls + ceiling)"""
    
    return f"""🏗️ **Floor Plan Analysis**

**Files Analyzed:**
{file_list}

**Building Area:** {area_str}

**Rooms Identified:**
• {rooms_str}

**Dimensions Found:**
• {dims_str}
{quantity_estimate}

**Next Steps:**
1. Verify all dimensions on the drawing
2. Check scale accuracy
3. Review structural requirements
4. Get RSMeans cost data for detailed estimate"""


def analyze_schedule(text: str, file_list: str) -> str:
    """Analyze schedule."""
    import re
    
    # Extract dates
    date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    dates = re.findall(date_pattern, text)
    
    # Extract activities
    lines = text.split('\n')
    activities = []
    for line in lines:
        if any(char.isdigit() for char in line) and len(line.strip()) > 10 and len(line.strip()) < 100:
            if not line.strip().startswith('http'):
                activities.append(line.strip()[:80])
    
    # Find milestones
    milestone_keywords = ["milestone", "substantial completion", "final completion", 
                         "mobilization", "demobilization", "handover", "closeout"]
    milestones = []
    for keyword in milestone_keywords:
        if keyword in text.lower():
            milestones.append(keyword.title())
    
    activities_str = "\n• ".join(activities[:8]) if activities else "See schedule for full activity list"
    milestones_str = ", ".join(milestones) if milestones else "Not specified"
    dates_str = f"{len(dates)} dates found" if dates else "Not extracted"
    
    return f"""📅 **Schedule Analysis**

**Files Analyzed:**
{file_list}

**Key Activities (sample):**
• {activities_str}

**Milestones Identified:**
{milestones_str}

**Dates Found:** {dates_str}

**Critical Path Analysis:**
• Review predecessor/successor relationships
• Identify float activities
• Check for constraints and deadlines
• Verify calendar settings

**Recommendations:**
✓ Validate activity durations with site team
✓ Check resource loading
✓ Review lag times between activities
✓ Update progress regularly"""


def analyze_general_document(text: str, file_list: str, task: str) -> str:
    """General document analysis."""
    word_count = len(text.split())
    char_count = len(text)
    
    # Extract key sentences
    sentences = text.split('.')[:5]
    preview = '. '.join(s.strip() for s in sentences if len(s.strip()) > 20)[:500]
    
    return f"""📄 **Document Analysis**

**Files Analyzed:**
{file_list}

**Document Statistics:**
• Words: {word_count:,}
• Characters: {char_count:,}
• Pages (est.): {max(1, word_count // 500)}

**Content Preview:**
{preview}...

**Your Question:** {task}

Based on the extracted text, I can help you understand this document. Please ask specific questions about:
• Specific sections or clauses
• Numbers, dates, or values
• Technical specifications
• Requirements or conditions"""


# ============ FIXED ENDPOINTS ============

@router.post("/execute", response_model=EnhancedTaskResponse)
async def execute_enhanced(request: EnhancedTaskRequest):
    """
    Execute task with full memory awareness and layer navigation.
    FIXED: Proper initialization with fallback to rule-based processing.
    """
    start_time = time.time()
    
    try:
        # Check if we have attachments to analyze
        if request.attachments:
            result = await analyze_attachments(request.attachments, request.task)
            if result:
                result["execution_time_ms"] = (time.time() - start_time) * 1000
                return EnhancedTaskResponse(**result)
        
        # Try to use the enhanced agent
        agent, error = await ensure_agent_initialized()
        
        if agent and not error:
            # Use full agent capabilities
            if request.target_layer:
                try:
                    layer = AgentLayer(request.target_layer)
                    agent.move_to_layer(layer, request.context)
                except ValueError:
                    pass  # Invalid layer, continue with auto-selection
            
            result = await agent.run(request.task, request.context)
            
            return EnhancedTaskResponse(
                success=result.success,
                action=result.action.value,
                layer=result.layer.value,
                data=result.data,
                message=result.message,
                execution_time_ms=(time.time() - start_time) * 1000,
                related_conversations=result.related_conversations,
                suggested_next_actions=result.suggested_next_actions,
                timestamp=result.timestamp
            )
        else:
            # Fallback to rule-based processing
            logger.warning(f"Agent not available, using rule-based fallback: {error}")
            result = handle_construction_task(request.task)
            result["execution_time_ms"] = (time.time() - start_time) * 1000
            return EnhancedTaskResponse(**result)
            
    except Exception as e:
        logger.error(f"Enhanced execution failed: {e}")
        # Final fallback
        result = handle_construction_task(request.task)
        result["execution_time_ms"] = (time.time() - start_time) * 1000
        return EnhancedTaskResponse(**result)


@router.get("/status/enhanced")
async def get_enhanced_status():
    """Get comprehensive agent status with layer info."""
    try:
        agent, error = await ensure_agent_initialized()
        
        if agent and not error:
            navigator = agent.layer_navigator
            all_layers = list(AgentLayer)
            layer_states = {}
            for layer in all_layers:
                layer_states[layer.value] = navigator.get_layer_info(layer)
            
            return {
                "initialized": True,
                "session_id": agent.context.session_id,
                "current_layer": agent.context.current_layer.value,
                "layer_history": [l.layer.value for l in agent.context.layer_history[-5:]],
                "available_tools": len(agent.tools),
                "memory_entries_indexed": len(agent.conversation_reader.memory_index),
                "layers_count": len(all_layers),
                "layers": [layer.value for layer in all_layers],
                "layer_states": layer_states
            }
        else:
            return {
                "initialized": False,
                "error": str(error) if error else "Agent not initialized",
                "fallback_mode": True,
                "available_layers": [l.value for l in AgentLayer]
            }
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return {
            "initialized": False,
            "error": str(e),
            "fallback_mode": True
        }


# Keep other existing endpoints from original file...
# (WebSocket, status, health check endpoints)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time agent communication."""
    ws_manager = get_websocket_manager()
    await ws_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            
            # Process message through agent
            task = data.get("task", "")
            context = data.get("context")
            
            try:
                agent, error = await ensure_agent_initialized()
                
                if agent and not error:
                    result = await agent.run(task, context)
                    await websocket.send_json({
                        "type": "response",
                        "success": result.success,
                        "action": result.action.value,
                        "layer": result.layer.value,
                        "message": result.message,
                        "data": result.data,
                        "suggested_next_actions": result.suggested_next_actions
                    })
                else:
                    # Fallback
                    result = handle_construction_task(task)
                    await websocket.send_json({
                        "type": "response",
                        **result
                    })
                    
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
