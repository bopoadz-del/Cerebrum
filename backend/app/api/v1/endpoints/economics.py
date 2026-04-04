"""
Economics API Endpoints
Uses enhanced mock data when RSMeans API is not available
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings

# Try to import mock data, fall back to empty stubs
try:
    from app.economics.mock_data import (
        CSI_DIVISIONS,
        RSMEANS_MOCK_ITEMS,
        INFRASTRUCTURE_ITEMS,
        ROADWORK_ITEMS,
        SITEWORK_ITEMS,
        CITY_COST_INDICES,
        BUILDING_TYPES,
        CONSTRUCTION_FORMULAS,
        get_all_items,
        get_items_by_division,
        get_item_by_id,
        estimate_building_cost,
        apply_location_factor,
    )
    MOCK_DATA_AVAILABLE = True
except ImportError:
    MOCK_DATA_AVAILABLE = False
    CSI_DIVISIONS = {}
    RSMEANS_MOCK_ITEMS = {}
    INFRASTRUCTURE_ITEMS = {}
    ROADWORK_ITEMS = []
    SITEWORK_ITEMS = []
    CITY_COST_INDICES = {}
    BUILDING_TYPES = {}
    CONSTRUCTION_FORMULAS = {}

try:
    from app.api.deps import get_current_user, User
except ImportError:
    from app.core.deps import get_current_user
    User = dict

router = APIRouter(prefix="/economics", tags=["Economics"])


# Pydantic Models
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


# =============================================================================
# RSMeans Data Endpoints
# =============================================================================

@router.get("/rsmeans/search")
async def search_rsmeans(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100)
):
    """Search RSMeans cost database"""
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    all_items = get_all_items()
    query = q.lower()
    
    # Search by description, ID, or category
    results = [
        item for item in all_items
        if query in item.get("description", "").lower()
        or query in item.get("id", "").lower()
        or query in item.get("category", "").lower()
    ]
    
    if category:
        results = [r for r in results if r.get("category") == category]
    
    return {
        "query": q,
        "results": results[:limit],
        "total": len(results),
    }


@router.get("/rsmeans/{rsmeans_id}")
async def get_rsmeans_item(rsmeans_id: str):
    """Get RSMeans item details"""
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    item = get_item_by_id(rsmeans_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {rsmeans_id} not found")
    
    return item


@router.get("/rsmeans/categories")
async def list_rsmeans_categories():
    """List RSMeans categories"""
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    return {
        "divisions": [
            {
                "code": code,
                "name": data["name"],
                "description": data["description"],
                "item_count": len(RSMEANS_MOCK_ITEMS.get(code, [])),
            }
            for code, data in CSI_DIVISIONS.items()
        ],
        "count": len(CSI_DIVISIONS),
    }


# =============================================================================
# CSI Divisions Endpoints
# =============================================================================

@router.get("/csi-divisions")
async def list_csi_divisions():
    """
    Get list of CSI MasterFormat divisions.
    Returns division codes, names, and descriptions.
    """
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    return {
        "divisions": [
            {
                "code": code,
                "name": data["name"],
                "description": data["description"],
                "item_count": len(RSMEANS_MOCK_ITEMS.get(code, [])),
            }
            for code, data in CSI_DIVISIONS.items()
        ],
        "count": len(CSI_DIVISIONS),
    }


@router.get("/csi-divisions/{code}/items")
async def get_division_items(code: str):
    """
    Get all cost items for a specific CSI division.
    
    - **code**: CSI division code (e.g., "03" for Concrete, "09" for Finishes)
    """
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    division = CSI_DIVISIONS.get(code)
    if not division:
        raise HTTPException(status_code=404, detail=f"Division '{code}' not found")
    
    items = get_items_by_division(code)
    
    return {
        "division_code": code,
        "division_name": division["name"],
        "description": division["description"],
        "items": items,
        "count": len(items),
    }


# =============================================================================
# Building Types & Estimates
# =============================================================================

@router.get("/building-types")
async def list_building_types():
    """
    Get list of building types for quick estimates.
    Returns building type codes, names, and typical costs per sq ft.
    """
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    return {
        "building_types": [
            {
                "code": code,
                "name": data["name"],
                "cost_per_sf": data["cost_per_sf"],
                "typical_size_sf": data["typical_size_sf"],
                "description": data["description"],
            }
            for code, data in BUILDING_TYPES.items()
        ],
        "count": len(BUILDING_TYPES),
    }


@router.post("/estimate/quick")
async def quick_building_estimate(
    building_type: str,
    size_sf: float = Query(..., gt=0, description="Building size in square feet"),
    city: str = "National Average",
):
    """
    Quick building cost estimate based on building type and location.
    
    - **building_type**: Building type code (use /building-types to list)
    - **size_sf**: Building size in square feet
    - **city**: City for location adjustment (default: National Average)
    """
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    result = estimate_building_cost(building_type, size_sf, city)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# =============================================================================
# Cost Estimation Endpoints
# =============================================================================

@router.post("/estimate")
async def create_cost_estimate(request: CostEstimateRequest):
    """Create detailed cost estimate"""
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    line_items = []
    subtotal = 0.0
    
    for item in request.items:
        rsmeans_item = get_item_by_id(item.rsmeans_id)
        if not rsmeans_item:
            raise HTTPException(status_code=404, detail=f"Item {item.rsmeans_id} not found")
        
        # Apply location factor if city provided
        unit_cost = rsmeans_item["base_cost"]
        if item.zip_code:
            # Simple zip-to-city mapping or use provided city
            unit_cost = apply_location_factor(unit_cost, item.zip_code)
        
        total = unit_cost * item.quantity
        subtotal += total
        
        line_items.append(CostItemResponse(
            rsmeans_id=item.rsmeans_id,
            description=rsmeans_item["description"],
            unit_cost=round(unit_cost, 2),
            total_cost=round(total, 2),
            city_cost_index=1.0,
        ))
    
    contingency = subtotal * (request.contingency_percent / 100)
    total = subtotal + contingency
    
    return CostEstimateResponse(
        total_cost=round(total, 2),
        subtotal=round(subtotal, 2),
        contingency=round(contingency, 2),
        line_items=line_items,
    )


# =============================================================================
# Infrastructure Endpoints
# =============================================================================

@router.get("/infrastructure/items")
async def list_infrastructure_items(category: Optional[str] = None):
    """
    Get infrastructure construction items (utilities, drainage, etc.)
    
    - **category**: Optional filter (manholes, sanitary, storm, water, irrigation, roadwork, sitework)
    """
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    items = []
    
    # Add infrastructure items
    for cat, cat_items in INFRASTRUCTURE_ITEMS.items():
        for item in cat_items:
            item_copy = item.copy()
            item_copy["category"] = cat.replace("33-", "")
            items.append(item_copy)
    
    # Add roadwork items
    for item in ROADWORK_ITEMS:
        item_copy = item.copy()
        item_copy["category"] = "roadwork"
        items.append(item_copy)
    
    # Add sitework items
    for item in SITEWORK_ITEMS:
        item_copy = item.copy()
        item_copy["category"] = "sitework"
        items.append(item_copy)
    
    if category:
        items = [i for i in items if i.get("category") == category.lower()]
    
    return {
        "items": items,
        "count": len(items),
    }


# =============================================================================
# City Cost Indices
# =============================================================================

@router.get("/city-indices")
async def list_city_indices(region: Optional[str] = None):
    """
    Get city cost indices for location adjustment.
    
    - **region**: Optional filter by region (e.g., "West", "Northeast", "Middle East")
    """
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    cities = [
        {"city": city, **data}
        for city, data in CITY_COST_INDICES.items()
    ]
    
    if region:
        cities = [c for c in cities if c.get("region") == region]
    
    return {
        "cities": cities,
        "count": len(cities),
    }


# =============================================================================
# Construction Formulas
# =============================================================================

@router.get("/formulas")
async def list_formulas(category: Optional[str] = None):
    """
    List available construction calculation formulas.
    
    - **category**: Filter by category (Concrete, Structural, Cost, Financial, Construction, Infrastructure)
    """
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    formulas = [
        {
            "id": key,
            "name": data["name"],
            "category": data["category"],
            "formula": data["formula"],
            "inputs": data["inputs"],
            "unit": data["unit"],
            "description": data["description"],
        }
        for key, data in CONSTRUCTION_FORMULAS.items()
    ]
    
    if category:
        formulas = [f for f in formulas if f["category"].lower() == category.lower()]
    
    return {
        "formulas": formulas,
        "count": len(formulas),
    }


@router.post("/formulas/{formula_id}/calculate")
async def calculate_formula(formula_id: str, inputs: Dict[str, float]):
    """
    Execute a construction formula with provided inputs.
    
    - **formula_id**: Formula identifier from /formulas list
    - **inputs**: Dictionary of input values matching the formula's required inputs
    """
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    formula = CONSTRUCTION_FORMULAS.get(formula_id)
    if not formula:
        raise HTTPException(status_code=404, detail=f"Formula '{formula_id}' not found")
    
    # Check all required inputs are provided
    missing = [inp for inp in formula["inputs"] if inp not in inputs]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing inputs: {missing}")
    
    # Simple formula evaluation (safe - no exec/eval of arbitrary code)
    try:
        result = evaluate_formula(formula["formula"], inputs)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")
    
    return {
        "formula_id": formula_id,
        "formula_name": formula["name"],
        "inputs": inputs,
        "result": result,
        "unit": formula["unit"],
    }


def evaluate_formula(formula: str, inputs: Dict[str, float]) -> float:
    """Safely evaluate a mathematical formula with given inputs."""
    # Replace variable names with values
    expression = formula
    for key, value in inputs.items():
        expression = expression.replace(key, str(value))
    
    # Safe evaluation - only allow math operations
    allowed_names = {
        "pi": 3.14159265359,
        "sqrt": lambda x: x ** 0.5,
    }
    
    # Simple parser for basic math
    try:
        # Replace ^ with ** for exponentiation
        expression = expression.replace("^", "**")
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return round(result, 4)
    except:
        return 0.0


# =============================================================================
# Budget Management (Stub - requires database)
# =============================================================================

@router.post("/budgets")
async def create_budget(request: BudgetCreateRequest):
    """Create project budget"""
    raise HTTPException(status_code=501, detail="Budget management requires database integration")


@router.get("/budgets")
async def list_budgets(project_id: Optional[str] = None):
    """List budgets"""
    raise HTTPException(status_code=501, detail="Budget management requires database integration")


@router.get("/budgets/{budget_id}")
async def get_budget(budget_id: str):
    """Get budget details"""
    raise HTTPException(status_code=501, detail="Budget management requires database integration")


@router.put("/budgets/{budget_id}")
async def update_budget(budget_id: str, updates: Dict[str, Any]):
    """Update budget"""
    raise HTTPException(status_code=501, detail="Budget management requires database integration")


@router.delete("/budgets/{budget_id}")
async def delete_budget(budget_id: str):
    """Delete budget"""
    raise HTTPException(status_code=501, detail="Budget management requires database integration")


# =============================================================================
# Forecasting (Stub - requires database)
# =============================================================================

@router.post("/forecast")
async def create_forecast(
    budget_id: str,
    months: int = Query(default=12, ge=1, le=60)
):
    """Create cost forecast"""
    raise HTTPException(status_code=501, detail="Forecasting requires database integration")


@router.get("/forecast/{forecast_id}")
async def get_forecast(forecast_id: str):
    """Get forecast details"""
    raise HTTPException(status_code=501, detail="Forecasting requires database integration")


@router.post("/forecast/{forecast_id}/scenarios")
async def run_scenario_analysis(forecast_id: str):
    """Run what-if scenario analysis"""
    raise HTTPException(status_code=501, detail="Forecasting requires database integration")


# =============================================================================
# Cost Index (Stub - uses mock data)
# =============================================================================

@router.get("/cost-index/{zip_code}")
async def get_cost_index(zip_code: str):
    """Get location cost index"""
    if not MOCK_DATA_AVAILABLE:
        raise HTTPException(status_code=503, detail="Economics mock data not available")
    
    # Simple mapping - in real app would map zip to city
    return {
        "zip_code": zip_code,
        "city": "National Average",
        "index": 1.0,
        "note": "Use /city-indices for detailed location factors",
    }


@router.get("/cost-index/history")
async def get_cost_index_history(
    zip_code: str,
    years: int = Query(default=5, ge=1, le=20)
):
    """Get historical cost index data"""
    raise HTTPException(status_code=501, detail="Historical data requires external API")


# =============================================================================
# Reporting (Stub - requires database)
# =============================================================================

@router.get("/reports/budget-vs-actual")
async def get_budget_vs_actual_report(project_id: str):
    """Get budget vs actual report"""
    raise HTTPException(status_code=501, detail="Reporting requires database integration")


@router.get("/reports/cost-breakdown")
async def get_cost_breakdown_report(project_id: str):
    """Get cost breakdown report"""
    raise HTTPException(status_code=501, detail="Reporting requires database integration")


__all__ = ["router"]
