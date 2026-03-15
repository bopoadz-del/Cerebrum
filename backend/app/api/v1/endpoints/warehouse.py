"""
Data Warehouse API Endpoints (Stub)
Full implementation requires warehouse modules
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

try:
    from app.api.deps import get_db, get_current_user
except ImportError:
    from app.core.deps import get_db, get_current_user

router = APIRouter()


# Stub responses
WAREHOUSE_NOT_AVAILABLE = {
    "detail": "Data warehouse features are not available in this deployment."
}


@router.get("/dashboard/executive")
async def get_executive_dashboard():
    """Get executive dashboard data"""
    raise HTTPException(status_code=503, **WAREHOUSE_NOT_AVAILABLE)


@router.get("/dashboard/kpis")
async def get_kpi_cards():
    """Get KPI cards data"""
    raise HTTPException(status_code=503, **WAREHOUSE_NOT_AVAILABLE)


@router.get("/query/natural")
async def natural_language_query(q: str = Query(..., description="Natural language query")):
    """Execute natural language query against data warehouse"""
    raise HTTPException(status_code=503, **WAREHOUSE_NOT_AVAILABLE)


@router.get("/analytics/predictive")
async def get_predictive_analytics(
    metric: str = Query(..., description="Metric to predict"),
    days: int = Query(default=30, ge=1, le=365)
):
    """Get predictive analytics for a metric"""
    raise HTTPException(status_code=503, **WAREHOUSE_NOT_AVAILABLE)


@router.get("/reports/custom")
async def get_custom_report():
    """Generate custom report"""
    raise HTTPException(status_code=503, **WAREHOUSE_NOT_AVAILABLE)


__all__ = ["router"]
