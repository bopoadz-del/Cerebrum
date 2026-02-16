"""
Data Warehouse API Endpoints
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.warehouse.executive_dashboard import executive_dashboard
from app.warehouse.nl_queries import nl_query_engine
from app.warehouse.predictive_analytics import predictive_analytics

router = APIRouter()


@router.get("/dashboard/executive")
async def get_executive_dashboard(
    current_user = Depends(get_current_user)
):
    """Get executive dashboard data"""
    return await executive_dashboard.get_full_dashboard()


@router.get("/dashboard/kpis")
async def get_kpi_cards(
    current_user = Depends(get_current_user)
):
    """Get KPI cards"""
    return await executive_dashboard.get_kpi_cards()


@router.post("/query/natural-language")
async def natural_language_query(
    query: str,
    current_user = Depends(get_current_user)
):
    """Execute natural language query"""
    result = await nl_query_engine.query(query)
    return {
        'query': result.query,
        'sql': result.sql,
        'results': result.results,
        'execution_time_ms': result.execution_time_ms,
        'row_count': result.row_count,
        'explanation': result.explanation,
        'suggested_queries': result.suggested_queries
    }


@router.get("/predict/project/{project_id}")
async def predict_project_outcome(
    project_id: str,
    current_user = Depends(get_current_user)
):
    """Get predictions for a project"""
    # This would fetch project data and run predictions
    project = {'id': project_id}  # Placeholder
    return predictive_analytics.analyze_project(project)


@router.get("/analytics/revenue")
async def get_revenue_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(get_current_user)
):
    """Get revenue analytics"""
    return await executive_dashboard.get_revenue_metrics(days)


@router.get("/analytics/customers")
async def get_customer_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(get_current_user)
):
    """Get customer analytics"""
    return await executive_dashboard.get_customer_metrics(days)


@router.get("/portfolio/overview")
async def get_portfolio_overview(
    current_user = Depends(get_current_user)
):
    """Get portfolio overview"""
    return await executive_dashboard.get_portfolio_overview()
