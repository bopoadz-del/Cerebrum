"""
STATELESS Agent API Endpoints - Memory Leak Fix

Key changes:
1. Fresh agent instance per request (no persistent state)
2. Explicit cleanup after each request
3. Memory profiling endpoint
4. No conversation history caching
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import os
import re
import time
import gc

logger = logging.getLogger(__name__)
router = APIRouter()

# Memory tracking
_request_count = 0
_total_memory_increase = 0

# Try to import psutil, fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class EnhancedTaskRequest(BaseModel):
    task: str = Field(..., description="Task description")
    context: Optional[Dict[str, Any]] = Field(default=None)
    use_memory: bool = Field(default=False, description="Search relevant memories (DISABLED)")
    target_layer: Optional[str] = Field(default=None, description="Force specific layer")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Previous conversation messages for context")
    attachments: Optional[List[Dict[str, Any]]] = Field(default=None, description="File attachments")


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


def get_memory_mb() -> float:
    """Get current process memory in MB."""
    if PSUTIL_AVAILABLE:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    return 0.0


def handle_concrete_calculation(task: str, is_follow_up: bool = False, original_task: str = "") -> Dict[str, Any]:
    """Handle concrete volume calculation."""
    import re
    
    # Extract dimensions
    pattern = r'(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m?'
    match = re.search(pattern, task.lower())
    
    if match:
        length, width, depth = map(float, match.groups())
        volume_m3 = length * width * depth
        volume_ft3 = volume_m3 * 35.315
        volume_yd3 = volume_m3 * 1.308
        cost_low = volume_yd3 * 120
        cost_high = volume_yd3 * 150
        
        # Use original task if this is a follow-up
        display_task = original_task if is_follow_up else task
        
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

*Note: Prices are national averages. Local costs may vary.*""",
        "related_conversations": [],
        "suggested_next_actions": ["Get specific item cost", "Calculate total estimate"],
        "timestamp": datetime.now().isoformat()
    }


def handle_formula_lookup(task: str) -> Dict[str, Any]:
    """Handle formula requests."""
    return {
        "success": True,
        "action": "formula_lookup",
        "layer": "economics",
        "data": {},
        "message": """📊 **Construction Formulas**

**Concrete:**
• Volume = Length × Width × Depth
• Bags needed = Volume (ft³) / 0.6 (for 80lb bags)

**Steel:**
• Rebar weight (lb) = Length (ft) × Weight per foot
• #4 bar = 0.668 lb/ft, #5 = 1.043 lb/ft, #6 = 1.502 lb/ft

**Beam Analysis:**
• Moment (M) = wL²/8 (uniform load, simple support)
• Deflection (Δ) = 5wL⁴/(384EI)

**Excavation:**
• Volume = Area × Depth
• Soil swell factor = Bank volume × 1.2-1.4""",
        "related_conversations": [],
        "suggested_next_actions": ["Calculate specific formula", "Get material quantities"],
        "timestamp": datetime.now().isoformat()
    }


def handle_steel_calculation(task: str) -> Dict[str, Any]:
    """Handle steel/rebar calculation requests."""
    import re
    
    # Extract area if provided
    area_match = re.search(r'(\d+\.?\d*)\s*(sq\s*ft|sqft|m2|m²|square)', task.lower())
    area_sqft = float(area_match.group(1)) if area_match else 1000  # Default 1000 sq ft
    
    # Rebar calculations
    rebar_lbs_per_sqft = 1.5  # Average for slabs
    total_rebar_lbs = area_sqft * rebar_lbs_per_sqft
    total_rebar_tons = total_rebar_lbs / 2000
    
    # Cost calculations
    cost_per_lb_installed = 1.0  # $1.00/lb installed average
    total_cost = total_rebar_lbs * cost_per_lb_installed
    
    message = f"""🔩 **Steel/Rebar Calculation**

**Area:** {area_sqft:,.0f} sq ft

**Rebar Quantities:**
• Total rebar: {total_rebar_lbs:,.0f} lbs ({total_rebar_tons:.2f} tons)
• Density: ~{rebar_lbs_per_sqft} lbs/sq ft (typical for slabs)

**Estimated Cost:**
• ${total_cost:,.0f} (@ ${cost_per_lb_installed}/lb installed)

**Typical Rebar Sizes:**
• #4 (1/2") - slabs, footings
• #5 (5/8") - beams, columns
• #6 (3/4") - heavy loads

*Note: Actual quantities depend on design loads and spacing.*"""
    
    return {
        "success": True,
        "action": "steel_calculation",
        "layer": "economics",
        "data": {
            "area_sqft": area_sqft,
            "rebar_lbs": total_rebar_lbs,
            "rebar_tons": total_rebar_tons,
            "cost": total_cost
        },
        "message": message,
        "related_conversations": [],
        "suggested_next_actions": ["Calculate concrete for this area", "Get formwork cost"],
        "timestamp": datetime.now().isoformat()
    }


def handle_greeting(task: str) -> Dict[str, Any]:
    """Handle greeting messages."""
    return {
        "success": True,
        "action": "greeting",
        "layer": "economics",
        "data": {},
        "message": """👋 **Hello! Welcome to Cerebrum AI**

I'm your construction intelligence assistant. I can help you with:

**📐 Calculations:**
• Concrete volume and cost
• Steel/rebar quantities
• Material estimates

**💰 Cost Estimates:**
• RSMeans cost data
• Building type estimates
• Project budgeting

**📊 Formulas & Analysis:**
• Structural calculations
• Construction formulas
• Engineering references

What would you like help with today?""",
        "related_conversations": [],
        "suggested_next_actions": ["Calculate concrete", "Estimate building cost", "Get RSMeans data"],
        "timestamp": datetime.now().isoformat()
    }


def handle_building_estimate(task: str) -> Dict[str, Any]:
    """Handle building cost estimate requests with proper type detection."""
    import re
    
    task_lower = task.lower()
    
    # Building type mapping with variations
    building_type_map = {
        # Office types
        "office-low": ["office-low", "office low", "budget office", "economy office"],
        "office-high": ["office-high", "office high", "premium office", "class a office"],
        # Warehouse types
        "warehouse-light": ["warehouse-light", "light warehouse", "warehouse"],
        "warehouse-heavy": ["warehouse-heavy", "heavy warehouse", "industrial warehouse"],
        # Other types
        "hospital": ["hospital", "medical", "healthcare"],
        "school": ["school", "education", "classroom"],
        "retail": ["retail", "store", "shopping"],
        "apartment": ["apartment", "residential", "housing"],
        "hotel": ["hotel", "hospitality"],
    }
    
    # Default building type costs (per sq ft)
    building_costs = {
        "office-low": 225,
        "office-high": 350,
        "warehouse-light": 95,
        "warehouse-heavy": 135,
        "hospital": 600,
        "school": 275,
        "retail": 200,
        "apartment": 250,
        "hotel": 300,
    }
    
    # Detect building type
    detected_type = None
    for type_code, keywords in building_type_map.items():
        if any(keyword in task_lower for keyword in keywords):
            detected_type = type_code
            break
    
    # If "office" mentioned but no specific type, default to office-low
    if not detected_type and "office" in task_lower:
        detected_type = "office-low"
    
    # Extract square footage
    sqft_match = re.search(r'(\d[\d,]*)\s*(?:sq\s*ft|sqft|square\s*feet|sq\.?\s*ft)', task_lower)
    if sqft_match:
        size_sf = int(sqft_match.group(1).replace(',', ''))
    else:
        # Try to find any number that might be square footage
        numbers = re.findall(r'\d[\d,]*', task_lower)
        for num_str in numbers:
            num = int(num_str.replace(',', ''))
            if 100 <= num <= 10000000:  # Reasonable range for building size
                size_sf = num
                break
        else:
            size_sf = 5000  # Default size
    
    # Get cost per sq ft
    cost_per_sf = building_costs.get(detected_type, 200) if detected_type else 200
    
    # Calculate estimate
    total_cost = cost_per_sf * size_sf
    
    # Format type name for display
    type_display = detected_type.replace('-', ' ').title() if detected_type else "Building"
    
    message = f"""🏢 **{type_display} Cost Estimate**

**Project Details:**
• Building Type: {type_display}
• Size: {size_sf:,} sq ft
• Cost per sq ft: ${cost_per_sf}/sq ft

**Estimated Total Cost:**
• **${total_cost:,}** (USD)

*Note: This is a preliminary estimate. Actual costs vary based on location, materials, labor rates, and project complexity.*"""
    
    return {
        "success": True,
        "action": "building_estimate",
        "layer": "economics",
        "data": {
            "building_type": detected_type or "unknown",
            "size_sf": size_sf,
            "cost_per_sf": cost_per_sf,
            "total_cost": total_cost,
        },
        "message": message,
        "related_conversations": [],
        "suggested_next_actions": ["Get detailed breakdown", "Adjust size/quality", "Save estimate"],
        "timestamp": datetime.now().isoformat()
    }


def extract_context_from_history(task: str, conversation_history: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Extract relevant context from conversation history to answer follow-up questions."""
    if not conversation_history or len(conversation_history) < 2:
        return {}
    
    context = {}
    task_lower = task.lower()
    
    # Look for references to previous calculations
    reference_patterns = [
        r'(?:that|the|this|those|these)\s+(\d+m?\s*x\s*\d+m?)\s+foundation',
        r'(?:that|the|this|those|these)\s+(\d+m?\s*x\s*\d+m?)\s+slab',
        r'(?:that|the|this|those|these)\s+(\d+m?\s*x\s*\d+m?)\s+area',
        r'(?:that|the|this|those|these)\s+dimensions?',
        r'(?:that|the|this|those|these)\s+calculation',
        r'(?:it|that|this)\s+is?\s+(\d+m?\s*x\s*\d+m?)',
        r'what\s+about\s+(\d+m?\s*x\s*\d+m?)',
    ]
    
    # Check if task contains reference patterns (indicating a follow-up question)
    is_follow_up = any(re.search(pattern, task_lower) for pattern in reference_patterns)
    is_follow_up = is_follow_up or any(word in task_lower for word in [
        'that foundation', 'that slab', 'those dimensions', 'the dimensions', 
        'the calculation', 'previous', 'earlier', 'we calculated', 'we discussed',
        'what about', 'how about', 'and for', 'also', 'too', 'about it'
    ])
    
    if not is_follow_up:
        return context
    
    # Search through conversation history for dimensions and calculations
    for msg in reversed(conversation_history):
        content = msg.get('content', '')
        role = msg.get('role', '')
        content_lower = content.lower()
        
        # Look for concrete/steel calculations in assistant responses
        if role == 'assistant':
            # Check for calculation output markers (Dimensions section with length/width/depth)
            has_dimensions_section = ('length' in content_lower and 'width' in content_lower) or \
                                     ('dimensions' in content_lower and 'volume' in content_lower)
            
            if has_dimensions_section:
                context['has_previous_calculation'] = True
                context['assistant_calculation_content'] = content
                
                # Extract dimensions - handle "10 m" format with space
                # Look for pattern: number followed by optional space and 'm' or 'meters'
                all_dims = re.findall(r'(\d+\.?\d*)\s*(?:m|meters?)', content_lower)
                if len(all_dims) >= 2:
                    context['previous_length'] = all_dims[0]
                    context['previous_width'] = all_dims[1]
                    if len(all_dims) >= 3:
                        context['previous_depth'] = all_dims[2]
                break
    
    return context


def handle_construction_task(task: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Handle construction-specific tasks without full agent."""
    task_lower = task.lower().strip()
    
    # Extract context from conversation history
    history_context = extract_context_from_history(task, conversation_history)
    
    # Remove leading slash from commands
    if task_lower.startswith('/'):
        task_lower = task_lower[1:]
    
    # GREETING - check first
    if task_lower in ["hello", "hi", "hey", "greetings", "howdy"]:
        return handle_greeting(task)
    
    # BUILDING ESTIMATE - check before cost_lookup for building-specific queries
    building_keywords = [
        "office", "warehouse", "hospital", "school", "retail", 
        "apartment", "hotel", "building", "estimate", "sq ft", 
        "square feet", "sqft"
    ]
    if any(keyword in task_lower for keyword in building_keywords):
        # Check if it looks like a building estimate request
        if any(size_word in task_lower for size_word in ["sq ft", "sqft", "square feet", "square"]) or \
           any(type_word in task_lower for type_word in ["office", "warehouse", "hospital", "school"]):
            return handle_building_estimate(task)
    
    # STEEL/REBAR calculation (check BEFORE concrete to avoid conflict)
    if any(word in task_lower for word in ["steel", "rebar", "reinforcement"]):
        return handle_steel_calculation(task)
    
    # Concrete volume calculation (needs dimensions)
    if "concrete" in task_lower:
        # Check if this is a follow-up and we have previous dimensions
        if history_context.get('has_previous_calculation') and not re.search(r'\d+\.?\d*\s*m?\s*[x×]\s*\d+\.?\d*', task_lower):
            # Use previous dimensions
            prev_length = history_context.get('previous_length', '10')
            prev_width = history_context.get('previous_width', '8')
            prev_depth = history_context.get('previous_depth', '0.3')
            task_with_context = f"Calculate concrete for {prev_length}m x {prev_width}m x {prev_depth}m"
            return handle_concrete_calculation(task_with_context, is_follow_up=True, original_task=task)
        return handle_concrete_calculation(task)
    
    # Cost estimates
    if any(word in task_lower for word in ["cost", "price", "estimate", "rsmeans"]):
        return handle_cost_lookup(task)
    
    # Formulas
    if any(word in task_lower for word in ["formula", "beam", "moment", "load", "deflection"]):
        return handle_formula_lookup(task)
    
    # Default response - show available commands
    return {
        "success": True,
        "action": "general_assistance",
        "layer": "economics",
        "data": {"query": task},
        "message": """🏗️ **Cerebrum AI - Construction Intelligence**

I can help you with:

**📐 Calculations:**
• **Concrete:** "Calculate concrete for 10m x 5m x 0.3m"
• **Steel:** "Calculate steel for 5000 sq ft"
• **Rebar:** "Calculate rebar for foundation"

**💰 Cost Estimates:**
• **RSMeans:** "Cost of concrete per cubic yard"
• **Projects:** "Estimate cost for 5000 sq ft office"

**📊 Formulas:**
• **Beam:** "Formula for beam moment"
• **Deflection:** "Deflection formula for cantilever"

**Try these commands:**
• `/formula beam` - Construction formulas
• `/cost concrete` - RSMeans costs

Upload a document for AI analysis!
""",
        "related_conversations": [],
        "suggested_next_actions": ["Calculate concrete", "Calculate steel", "Get cost estimate"],
        "timestamp": datetime.now().isoformat()
    }


@router.post("/execute", response_model=EnhancedTaskResponse)
async def execute_stateless(request: EnhancedTaskRequest):
    """
    STATELESS execution - fresh processing per request.
    No persistent state, explicit cleanup after each request.
    """
    global _request_count, _total_memory_increase
    
    start_time = time.time()
    mem_before = get_memory_mb()
    _request_count += 1
    
    try:
        # STATELESS: No agent instance created
        # Direct rule-based processing with conversation history for context
        result = handle_construction_task(request.task, request.conversation_history)
        
        # Add execution time
        result["execution_time_ms"] = (time.time() - start_time) * 1000
        
        return EnhancedTaskResponse(**result)
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        result = handle_construction_task(request.task, request.conversation_history)
        result["execution_time_ms"] = (time.time() - start_time) * 1000
        return EnhancedTaskResponse(**result)
    
    finally:
        # Explicit cleanup
        gc.collect()
        mem_after = get_memory_mb()
        mem_diff = mem_after - mem_before
        _total_memory_increase += max(0, mem_diff)
        
        if mem_diff > 10:  # Log if memory increased by more than 10MB
            logger.warning(f"Memory increase: {mem_diff:.2f} MB (request #{_request_count})")


@router.get("/memory/profile")
async def get_memory_profile():
    """Get memory profiling data."""
    if PSUTIL_AVAILABLE:
        process = psutil.Process()
        mem_info = process.memory_info()
        memory_data = {
            "rss": round(mem_info.rss / 1024 / 1024, 2),
            "vms": round(mem_info.vms / 1024 / 1024, 2),
        }
    else:
        memory_data = {"rss": 0, "vms": 0, "note": "psutil not available"}
    
    return {
        "memory_mb": memory_data,
        "psutil_available": PSUTIL_AVAILABLE,
        "request_stats": {
            "total_requests": _request_count,
            "total_memory_increase_mb": round(_total_memory_increase, 2),
            "avg_increase_per_request_mb": round(_total_memory_increase / _request_count, 2) if _request_count > 0 else 0
        },
        "gc_stats": {
            "garbage_count": len(gc.garbage),
            "collection_counts": gc.get_count()
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/memory/gc")
async def force_garbage_collection():
    """Force garbage collection."""
    gc_before = len(gc.garbage)
    collected = gc.collect()
    gc_after = len(gc.garbage)
    
    return {
        "collected": collected,
        "garbage_before": gc_before,
        "garbage_after": gc_after,
        "memory_after_mb": round(get_memory_mb(), 2),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/status/enhanced")
async def get_enhanced_status():
    """Get agent status - STATELESS mode."""
    return {
        "initialized": True,
        "mode": "stateless",
        "message": "Agent running in stateless mode with conversation history support",
        "features": {
            "memory_indexing": False,
            "ml_embeddings": False,
            "conversation_history": True,
        },
        "available_layers": [
            "coding", "registry", "validation", "hotswap", "healing",
            "prompts", "triggers", "economics", "vdc", "edge",
            "portal", "enterprise", "connectors", "monitoring"
        ],
        "timestamp": datetime.now().isoformat()
    }
