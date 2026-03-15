"""
Economics API Endpoints - RSMeans Cost Estimation
"""

import os
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger

try:
    from app.economics.pricing_engine import RSMeansAPI, CostItem, LocationFactor
    from app.economics.change_orders import ChangeOrderManager
    ECONOMICS_AVAILABLE = True
except ImportError:
    ECONOMICS_AVAILABLE = False

try:
    from app.api.deps import get_current_user, User
except ImportError:
    from app.core.deps import get_current_user
    User = dict

router = APIRouter(prefix="/economics", tags=["Economics"])
logger = get_logger(__name__)

# Mock RSMeans data for demo (replace with API calls)
MOCK_RSMEANS_DATA = {
    "031011-010": {
        "rsmeans_id": "031011-010",
        "description": "Concrete, 3000 psi, ready mix",
        "unit": "CY",
        "material_cost": 125.50,
        "labor_cost": 45.00,
        "equipment_cost": 15.00,
        "total_cost": 185.50,
        "category": "Concrete"
    },
    "092216-100": {
        "rsmeans_id": "092216-100",
        "description": "Drywall, 5/8\" gypsum board",
        "unit": "SF",
        "material_cost": 0.65,
        "labor_cost": 1.20,
        "equipment_cost": 0.10,
        "total_cost": 1.95,
        "category": "Drywall"
    },
    "081113-100": {
        "rsmeans_id": "081113-100",
        "description": "Steel door, hollow metal, 3'0\" x 7'0\"",
        "unit": "EA",
        "material_cost": 285.00,
        "labor_cost": 125.00,
        "equipment_cost": 15.00,
        "total_cost": 425.00,
        "category": "Doors"
    }
}

MOCK_CITY_INDEX = {
    "10001": {"city": "New York", "state": "NY", "index": 135.5},
    "90210": {"city": "Los Angeles", "state": "CA", "index": 128.3},
    "60601": {"city": "Chicago", "state": "IL", "index": 118.7},
    "77001": {"city": "Houston", "state": "TX", "index": 98.4},
    "85001": {"city": "Phoenix", "state": "AZ", "index": 102.1},
}

# In-memory storage for demo
_budgets: Dict[str, Dict] = {}
_estimates: Dict[str, Dict] = {}


class CostItemRequest(BaseModel):
    rsmeans_id: str
    quantity: float = Field(gt=0)
    zip_code: Optional[str] = None


class CostItemResponse(BaseModel):
    rsmeans_id: str
    description: str
    unit_cost: float
    total_cost: float
    city_cost_index: Optional[float] = None


class CostEstimateRequest(BaseModel):
    items: List[CostItemRequest]
    zip_code: Optional[str] = None
    contingency_percent: float = Field(default=10.0, ge=0, le=100)


class CostEstimateResponse(BaseModel):
    total_cost: float
    subtotal: float
    contingency: float
    line_items: List[CostItemResponse]


class BudgetCreateRequest(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    total_budget: float


def _get_city_index(zip_code: Optional[str]) -> float:
    """Get city cost index for zip code."""
    if not zip_code:
        return 100.0
    return MOCK_CITY_INDEX.get(zip_code, {}).get("index", 100.0)


def _lookup_rsmeans(rsmeans_id: str) -> Optional[Dict]:
    """Lookup RSMeans item by ID."""
    # First check mock data
    if rsmeans_id in MOCK_RSMEANS_DATA:
        return MOCK_RSMEANS_DATA[rsmeans_id]
    
    # Try API if available
    if ECONOMICS_AVAILABLE and settings.RSMEANS_API_KEY:
        # Would call RSMeans API here
        pass
    
    return None


# RSMeans Data Endpoints

@router.get("/rsmeans/search")
async def search_rsmeans(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """Search RSMeans cost database"""
    results = []
    
    # Search mock data
    for item_id, item in MOCK_RSMEANS_DATA.items():
        if q.lower() in item["description"].lower() or q.lower() in item_id.lower():
            if not category or item.get("category") == category:
                results.append(item)
    
    return {
        "query": q,
        "results": results[:limit],
        "total": len(results),
        "limit": limit
    }


@router.get("/rsmeans/{rsmeans_id}")
async def get_rsmeans_item(
    rsmeans_id: str,
    current_user = Depends(get_current_user)
):
    """Get RSMeans item details"""
    item = _lookup_rsmeans(rsmeans_id)
    
    if not item:
        raise HTTPException(status_code=404, detail=f"RSMeans item {rsmeans_id} not found")
    
    return item


@router.get("/rsmeans/categories")
async def list_rsmeans_categories(current_user = Depends(get_current_user)):
    """List RSMeans categories"""
    categories = set()
    for item in MOCK_RSMEANS_DATA.values():
        if "category" in item:
            categories.add(item["category"])
    
    return {"categories": sorted(categories)}


# Cost Estimation Endpoints

@router.post("/estimate", response_model=CostEstimateResponse)
async def create_cost_estimate(
    request: CostEstimateRequest,
    current_user = Depends(get_current_user)
):
    """Create detailed cost estimate"""
    line_items = []
    subtotal = Decimal('0')
    
    city_index = _get_city_index(request.zip_code)
    
    for item_req in request.items:
        item = _lookup_rsmeans(item_req.rsmeans_id)
        
        if not item:
            raise HTTPException(
                status_code=404, 
                detail=f"RSMeans item {item_req.rsmeans_id} not found"
            )
        
        # Apply location factor
        base_cost = Decimal(str(item["total_cost"]))
        location_factor = Decimal(str(city_index / 100.0))
        adjusted_cost = base_cost * location_factor
        
        total_cost = adjusted_cost * Decimal(str(item_req.quantity))
        subtotal += total_cost
        
        line_items.append(CostItemResponse(
            rsmeans_id=item_req.rsmeans_id,
            description=item["description"],
            unit_cost=float(adjusted_cost),
            total_cost=float(total_cost),
            city_cost_index=city_index if request.zip_code else None
        ))
    
    contingency = subtotal * Decimal(str(request.contingency_percent / 100))
    total = subtotal + contingency
    
    # Save estimate
    estimate_id = f"est_{datetime.utcnow().timestamp()}"
    _estimates[estimate_id] = {
        "id": estimate_id,
        "items": request.items,
        "zip_code": request.zip_code,
        "contingency_percent": request.contingency_percent,
        "subtotal": float(subtotal),
        "contingency": float(contingency),
        "total": float(total),
        "created_at": datetime.utcnow().isoformat()
    }
    
    return CostEstimateResponse(
        total_cost=float(total),
        subtotal=float(subtotal),
        contingency=float(contingency),
        line_items=line_items
    )


@router.post("/estimate/quick")
async def quick_estimate(
    description: str,
    area_sqft: float,
    building_type: str = "office",
    zip_code: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Quick square-footage based estimate"""
    # Rough costs per sq ft by building type
    base_costs = {
        "office": 175.0,
        "retail": 145.0,
        "warehouse": 85.0,
        "apartment": 195.0,
        "hospital": 450.0,
        "school": 220.0,
        "industrial": 125.0
    }
    
    base_cost = base_costs.get(building_type.lower(), 150.0)
    city_index = _get_city_index(zip_code)
    adjusted_cost = base_cost * (city_index / 100.0)
    total = adjusted_cost * area_sqft
    
    return {
        "building_type": building_type,
        "area_sqft": area_sqft,
        "zip_code": zip_code,
        "city_cost_index": city_index,
        "cost_per_sqft": adjusted_cost,
        "total_cost": total,
        "estimate_type": "quick"
    }


# Budget Management Endpoints

@router.post("/budgets")
async def create_budget(
    request: BudgetCreateRequest,
    current_user = Depends(get_current_user)
):
    """Create project budget"""
    budget_id = f"bud_{datetime.utcnow().timestamp()}"
    
    budget = {
        "id": budget_id,
        "project_id": request.project_id,
        "name": request.name,
        "description": request.description,
        "total_budget": request.total_budget,
        "spent": 0.0,
        "remaining": request.total_budget,
        "created_at": datetime.utcnow().isoformat(),
        "line_items": []
    }
    
    _budgets[budget_id] = budget
    
    return budget


@router.get("/budgets")
async def list_budgets(
    project_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """List budgets"""
    budgets = list(_budgets.values())
    
    if project_id:
        budgets = [b for b in budgets if b["project_id"] == project_id]
    
    return {"budgets": budgets, "count": len(budgets)}


@router.get("/budgets/{budget_id}")
async def get_budget(
    budget_id: str,
    current_user = Depends(get_current_user)
):
    """Get budget details"""
    if budget_id not in _budgets:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    return _budgets[budget_id]


@router.put("/budgets/{budget_id}")
async def update_budget(
    budget_id: str,
    updates: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """Update budget"""
    if budget_id not in _budgets:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    budget = _budgets[budget_id]
    
    if "total_budget" in updates:
        budget["total_budget"] = updates["total_budget"]
        budget["remaining"] = budget["total_budget"] - budget["spent"]
    
    if "name" in updates:
        budget["name"] = updates["name"]
    
    if "description" in updates:
        budget["description"] = updates["description"]
    
    budget["updated_at"] = datetime.utcnow().isoformat()
    
    return budget


@router.delete("/budgets/{budget_id}")
async def delete_budget(
    budget_id: str,
    current_user = Depends(get_current_user)
):
    """Delete budget"""
    if budget_id not in _budgets:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    del _budgets[budget_id]
    return {"message": "Budget deleted"}


# Budget Line Items

@router.post("/budgets/{budget_id}/line-items")
async def add_budget_line_item(
    budget_id: str,
    item: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """Add line item to budget"""
    if budget_id not in _budgets:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    budget = _budgets[budget_id]
    
    line_item = {
        "id": f"li_{len(budget['line_items'])}",
        "description": item.get("description", ""),
        "rsmeans_id": item.get("rsmeans_id"),
        "quantity": item.get("quantity", 0),
        "unit_cost": item.get("unit_cost", 0),
        "total_cost": item.get("quantity", 0) * item.get("unit_cost", 0),
        "category": item.get("category", "General")
    }
    
    budget["line_items"].append(line_item)
    budget["spent"] += line_item["total_cost"]
    budget["remaining"] = budget["total_budget"] - budget["spent"]
    
    return line_item


@router.get("/budgets/{budget_id}/line-items")
async def list_budget_line_items(
    budget_id: str,
    current_user = Depends(get_current_user)
):
    """List budget line items"""
    if budget_id not in _budgets:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    return {"line_items": _budgets[budget_id]["line_items"]}


@router.put("/budgets/{budget_id}/line-items/{line_item_id}")
async def update_budget_line_item(
    budget_id: str,
    line_item_id: str,
    updates: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """Update budget line item"""
    if budget_id not in _budgets:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    budget = _budgets[budget_id]
    
    for item in budget["line_items"]:
        if item["id"] == line_item_id:
            # Recalculate spent
            budget["spent"] -= item["total_cost"]
            
            if "quantity" in updates:
                item["quantity"] = updates["quantity"]
            if "unit_cost" in updates:
                item["unit_cost"] = updates["unit_cost"]
            
            item["total_cost"] = item["quantity"] * item["unit_cost"]
            budget["spent"] += item["total_cost"]
            budget["remaining"] = budget["total_budget"] - budget["spent"]
            
            return item
    
    raise HTTPException(status_code=404, detail="Line item not found")


# Cost Index Endpoints

@router.get("/cost-index/{zip_code}")
async def get_cost_index(
    zip_code: str,
    current_user = Depends(get_current_user)
):
    """Get location cost index"""
    if zip_code in MOCK_CITY_INDEX:
        return MOCK_CITY_INDEX[zip_code]
    
    return {
        "zip_code": zip_code,
        "city": "Unknown",
        "state": "Unknown",
        "index": 100.0,
        "note": "Using national average"
    }


@router.get("/cost-index/history")
async def get_cost_index_history(
    zip_code: str,
    years: int = Query(default=5, ge=1, le=20),
    current_user = Depends(get_current_user)
):
    """Get historical cost index data"""
    # Mock historical data
    base_index = MOCK_CITY_INDEX.get(zip_code, {}).get("index", 100.0)
    
    history = []
    for i in range(years):
        year = datetime.utcnow().year - i
        # Simulate 2-4% annual increase
        import random
        growth = 1 + (random.uniform(0.02, 0.04) * i)
        history.append({
            "year": year,
            "index": round(base_index / growth, 2)
        })
    
    return {"zip_code": zip_code, "history": history}


__all__ = ["router"]
