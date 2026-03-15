"""
Subcontractor Portal API Endpoints (Stub)
Full implementation requires portal modules
"""

from typing import List, Optional
from datetime import datetime, date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

try:
    from app.core.deps import get_db, get_current_user, require_permissions
except ImportError:
    from app.core.deps import get_db, get_current_user
    def require_permissions(perms):
        return get_current_user

router = APIRouter(prefix="/portal", tags=["subcontractor-portal"])


# Stub responses
PORTAL_NOT_AVAILABLE = {
    "detail": "Subcontractor portal features are not available in this deployment. Portal modules not installed."
}


# Subcontractor Company Endpoints

@router.post("/companies")
async def create_subcontractor_company():
    """Create subcontractor company"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/companies")
async def list_subcontractor_companies():
    """List subcontractor companies"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/companies/{company_id}")
async def get_subcontractor_company(company_id: UUID):
    """Get subcontractor company details"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.put("/companies/{company_id}")
async def update_subcontractor_company(company_id: UUID):
    """Update subcontractor company"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.delete("/companies/{company_id}")
async def delete_subcontractor_company(company_id: UUID):
    """Delete subcontractor company"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


# Subcontractor User Endpoints

@router.post("/companies/{company_id}/users")
async def create_subcontractor_user(company_id: UUID):
    """Add user to subcontractor company"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/companies/{company_id}/users")
async def list_subcontractor_users(company_id: UUID):
    """List users in subcontractor company"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


# Invitation to Bid (ITB) Endpoints

@router.post("/projects/{project_id}/itbs")
async def create_itb(project_id: UUID):
    """Create Invitation to Bid"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/projects/{project_id}/itbs")
async def list_itbs(project_id: UUID):
    """List ITBs for project"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/itbs/{itb_id}")
async def get_itb(itb_id: UUID):
    """Get ITB details"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.post("/itbs/{itb_id}/send")
async def send_itb(itb_id: UUID):
    """Send ITB to subcontractors"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


# Bid Management Endpoints

@router.post("/itbs/{itb_id}/bids")
async def submit_bid(itb_id: UUID):
    """Submit bid for ITB"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/itbs/{itb_id}/bids")
async def list_bids(itb_id: UUID):
    """List bids for ITB"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/bids/{bid_id}")
async def get_bid(bid_id: UUID):
    """Get bid details"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.post("/bids/{bid_id}/award")
async def award_bid(bid_id: UUID):
    """Award bid"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.post("/bids/{bid_id}/reject")
async def reject_bid(bid_id: UUID):
    """Reject bid"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


# Schedule of Values (SOV) Endpoints

@router.post("/projects/{project_id}/sov")
async def create_sov(project_id: UUID):
    """Create Schedule of Values"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/projects/{project_id}/sov")
async def get_sov(project_id: UUID):
    """Get Schedule of Values"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.put("/sov/{sov_id}/line-items/{line_item_id}")
async def update_sov_line_item(sov_id: UUID, line_item_id: UUID):
    """Update SOV line item"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


# Payment Application Endpoints

@router.post("/contracts/{contract_id}/payment-apps")
async def create_payment_application(contract_id: UUID):
    """Create payment application"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/contracts/{contract_id}/payment-apps")
async def list_payment_applications(contract_id: UUID):
    """List payment applications"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/payment-apps/{app_id}")
async def get_payment_application(app_id: UUID):
    """Get payment application details"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.post("/payment-apps/{app_id}/submit")
async def submit_payment_application(app_id: UUID):
    """Submit payment application"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.post("/payment-apps/{app_id}/approve")
async def approve_payment_application(app_id: UUID):
    """Approve payment application"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.post("/payment-apps/{app_id}/reject")
async def reject_payment_application(app_id: UUID):
    """Reject payment application"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


# Daily Report Endpoints

@router.post("/projects/{project_id}/daily-reports")
async def create_daily_report(project_id: UUID):
    """Create daily report"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/projects/{project_id}/daily-reports")
async def list_daily_reports(project_id: UUID):
    """List daily reports"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/daily-reports/{report_id}")
async def get_daily_report(report_id: UUID):
    """Get daily report"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.put("/daily-reports/{report_id}")
async def update_daily_report(report_id: UUID):
    """Update daily report"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


# Scoped Access Endpoints

@router.get("/companies/{company_id}/projects")
async def list_company_projects(company_id: UUID):
    """List projects accessible to company"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/companies/{company_id}/documents")
async def list_company_documents(company_id: UUID):
    """List documents accessible to company"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


@router.get("/me/permissions")
async def get_my_permissions():
    """Get current user's scoped permissions"""
    raise HTTPException(status_code=503, **PORTAL_NOT_AVAILABLE)


__all__ = ["router"]
