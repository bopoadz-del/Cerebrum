"""
Economics API Endpoints
RESTful API for cost management, budgeting, and forecasting.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, User
from app.core.logging import get_logger
from app.economics.pricing_engine import get_pricing_engine
from app.economics.forecasting import get_forecaster, RiskFactor

logger = get_logger(__name__)
router = APIRouter(prefix="/economics", tags=["Economics"])


# Pydantic Models
class CostItemRequest(BaseModel):
    rsmeans_id: str
    quantity: float = Field(gt=0)
    zip_code: Optional[str] = None


class CostItemResponse(BaseModel):
    rsmeans_id: str
    description: str
    unit: str
    quantity: float
    total_cost: float
    unit_price: float


class TakeoffRequest(BaseModel):
    items: List[CostItemRequest]
    zip_code: Optional[str] = None


class ForecastRequest(BaseModel):
    base_cost: float
    risk_factors: Optional[List[Dict[str, Any]]] = None
    num_simulations: int = Field(default=10000, ge=1000, le=50000)
    confidence_levels: List[float] = [0.80, 0.90, 0.95]


class ForecastResponse(BaseModel):
    base_cost: float
    mean_forecast: float
    median_forecast: float
    std_deviation: float
    confidence_intervals: Dict[str, Any]
    percentiles: Dict[str, float]
    risk_adjusted_cost: float


class ContingencyRequest(BaseModel):
    base_cost: float
    target_confidence: float = Field(default=0.80, ge=0.5, le=0.99)
    risk_factors: Optional[List[Dict[str, Any]]] = None


class ContingencyResponse(BaseModel):
    base_cost: float
    target_confidence: float
    recommended_contingency: float
    contingency_percent: float
    total_budget_recommendation: float
    risk_level: str


# RSMeans Integration Endpoints
@router.post("/pricing/calculate", response_model=CostItemResponse)
async def calculate_item_cost(
    request: CostItemRequest,
    current_user: User = Depends(get_current_user)
) -> CostItemResponse:
    """Calculate cost for a single RSMeans item."""
    try:
        engine = await get_pricing_engine()
        
        result = await engine.calculate_item_cost(
            request.rsmeans_id,
            Decimal(str(request.quantity)),
            request.zip_code
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return CostItemResponse(
            rsmeans_id=result["rsmeans_id"],
            description=result["description"],
            unit=result["unit"],
            quantity=result["quantity"],
            total_cost=result["total_cost"],
            unit_price=result["unit_price"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cost calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pricing/takeoff")
async def calculate_takeoff(
    request: TakeoffRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Calculate costs for quantity takeoff items."""
    try:
        engine = await get_pricing_engine()
        
        takeoff_items = [
            {"rsmeans_id": item.rsmeans_id, "quantity": item.quantity}
            for item in request.items
        ]
        
        result = await engine.calculate_takeoff_costs(
            takeoff_items,
            request.zip_code
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Takeoff calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing/search")
async def search_cost_items(
    query: str = Query(..., min_length=2),
    category: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Search RSMeans cost items."""
    try:
        engine = await get_pricing_engine()
        
        results = await engine.rsmeans.search_cost_items(
            query,
            category,
            limit
        )
        
        return [item.to_dict() for item in results]
        
    except Exception as e:
        logger.error(f"Cost item search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing/location-factor/{zip_code}")
async def get_location_factor(
    zip_code: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get location cost factor for ZIP code."""
    try:
        engine = await get_pricing_engine()
        
        factor = await engine.rsmeans.get_location_factor(zip_code)
        
        if not factor:
            raise HTTPException(status_code=404, detail="Location factor not found")
        
        return factor.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Location factor lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Forecasting Endpoints
@router.post("/forecast/monte-carlo", response_model=ForecastResponse)
async def monte_carlo_forecast(
    request: ForecastRequest,
    current_user: User = Depends(get_current_user)
) -> ForecastResponse:
    """Run Monte Carlo cost forecast."""
    try:
        forecaster = await get_forecaster()
        
        # Convert risk factors
        risks = None
        if request.risk_factors:
            risks = [
                RiskFactor(
                    name=r.get("name", "Unknown"),
                    probability=r.get("probability", 0.5),
                    impact_low=r.get("impact_low", 0),
                    impact_high=r.get("impact_high", 10)
                )
                for r in request.risk_factors
            ]
        
        result = await forecaster.simulator.simulate(
            request.base_cost,
            risks or forecaster.DEFAULT_RISKS,
            request.num_simulations,
            request.confidence_levels
        )
        
        return ForecastResponse(
            base_cost=result.base_cost,
            mean_forecast=result.mean_forecast,
            median_forecast=result.median_forecast,
            std_deviation=result.std_deviation,
            confidence_intervals=result.confidence_intervals,
            percentiles=result.percentiles,
            risk_adjusted_cost=result.risk_adjusted_cost
        )
        
    except Exception as e:
        logger.error(f"Forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecast/contingency")
async def calculate_contingency(
    request: ContingencyRequest,
    current_user: User = Depends(get_current_user)
) -> ContingencyResponse:
    """Calculate recommended contingency amount."""
    try:
        forecaster = await get_forecaster()
        
        # Convert risk factors
        risks = None
        if request.risk_factors:
            risks = [
                RiskFactor(
                    name=r.get("name", "Unknown"),
                    probability=r.get("probability", 0.5),
                    impact_low=r.get("impact_low", 0),
                    impact_high=r.get("impact_high", 10)
                )
                for r in request.risk_factors
            ]
        
        result = await forecaster.generate_contingency_recommendation(
            request.base_cost,
            risks or forecaster.DEFAULT_RISKS,
            request.target_confidence
        )
        
        return ContingencyResponse(**result)
        
    except Exception as e:
        logger.error(f"Contingency calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecast/sensitivity")
async def sensitivity_analysis(
    request: ForecastRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Perform sensitivity analysis on risk factors."""
    try:
        forecaster = await get_forecaster()
        
        # Convert risk factors
        risks = None
        if request.risk_factors:
            risks = [
                RiskFactor(
                    name=r.get("name", "Unknown"),
                    probability=r.get("probability", 0.5),
                    impact_low=r.get("impact_low", 0),
                    impact_high=r.get("impact_high", 10)
                )
                for r in request.risk_factors
            ]
        
        result = await forecaster.simulator.sensitivity_analysis(
            request.base_cost,
            risks or forecaster.DEFAULT_RISKS,
            request.num_simulations
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Sensitivity analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Budget Management Endpoints
@router.get("/budgets")
async def list_budgets(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List budgets for a project."""
    # Implementation would query database
    return []


@router.post("/budgets")
async def create_budget(
    budget_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new budget."""
    # Implementation would create budget in database
    return {"id": "new_budget_id", "status": "created"}


@router.get("/budgets/{budget_id}")
async def get_budget(
    budget_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get budget details."""
    # Implementation would query database
    return {"id": budget_id}


# Change Order Endpoints
@router.get("/change-orders")
async def list_change_orders(
    budget_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List change orders."""
    return []


@router.post("/change-orders")
async def create_change_order(
    co_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new change order."""
    return {"id": "new_co_id", "status": "created"}


# Reports Endpoints
@router.get("/reports/cost-summary/{project_id}")
async def cost_summary_report(
    project_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate cost summary report."""
    return {
        "project_id": project_id,
        "original_budget": 0,
        "revised_budget": 0,
        "committed_cost": 0,
        "actual_cost": 0,
        "forecast_cost": 0,
        "variance": 0
    }


@router.get("/reports/cash-flow/{project_id}")
async def cash_flow_report(
    project_id: str,
    months: int = Query(default=12, ge=1, le=60),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate cash flow projection."""
    return {
        "project_id": project_id,
        "projections": []
    }
