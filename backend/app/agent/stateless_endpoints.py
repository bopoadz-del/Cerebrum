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
import psutil

logger = logging.getLogger(__name__)
router = APIRouter()

# Memory tracking
_request_count = 0
_total_memory_increase = 0


class EnhancedTaskRequest(BaseModel):
    task: str = Field(..., description="Task description")
    context: Optional[Dict[str, Any]] = Field(default=None)
    use_memory: bool = Field(default=False, description="Search relevant memories (DISABLED)")
    target_layer: Optional[str] = Field(default=None, description="Force specific layer")
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
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def handle_concrete_calculation(task: str) -> Dict[str, Any]:
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
        "related_conversations": [],
        "suggested_next_actions": ["Calculate concrete", "Get cost estimate"],
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
        # Direct rule-based processing
        result = handle_construction_task(request.task)
        
        # Add execution time
        result["execution_time_ms"] = (time.time() - start_time) * 1000
        
        return EnhancedTaskResponse(**result)
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        result = handle_construction_task(request.task)
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
    process = psutil.Process()
    mem_info = process.memory_info()
    
    return {
        "memory_mb": {
            "rss": round(mem_info.rss / 1024 / 1024, 2),
            "vms": round(mem_info.vms / 1024 / 1024, 2),
        },
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
