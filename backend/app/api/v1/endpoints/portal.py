"""
Subcontractor Portal API Endpoints
Item 340: Subcontractor portal endpoints
"""

from typing import List, Optional
from datetime import datetime, date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_permissions
from app.portal.scoped_access import ScopedAccessService, CreateSubcontractorCompanyRequest, SubcontractorUser
from app.portal.bid_management import BidManagementService, CreateITBRequest, SubmitBidRequest
from app.portal.payment_apps import PaymentApplicationService, CreateSOVRequest, CreatePaymentAppRequest
from app.portal.daily_reports import DailyReportService, CreateDailyReportRequest

router = APIRouter(prefix="/portal", tags=["subcontractor-portal"])


# Subcontractor Company Endpoints

@router.post("/companies")
async def create_subcontractor_company(
    request: CreateSubcontractorCompanyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permissions(["subcontractors:write"]))
):
    """Create subcontractor company"""
    service = ScopedAccessService(db)
    company = service.create_company(current_user["tenant_id"], request)
    
    return {
        "id": str(company.id),
        "company_name": company.company_name,
        "trades": company.trades,
        "status": company.status
    }


@router.get("/companies")
async def list_subcontractor_companies(
    trade: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List subcontractor companies"""
    service = ScopedAccessService(db)
    companies = service.list_companies(current_user["tenant_id"], trade, status)
    
    return [
        {
            "id": str(c.id),
            "company_name": c.company_name,
            "trades": c.trades,
            "primary_contact_name": c.primary_contact_name,
            "primary_contact_email": c.primary_contact_email,
            "status": c.status
        }
        for c in companies
    ]


@router.get("/companies/{company_id}")
async def get_subcontractor_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get subcontractor company details"""
    service = ScopedAccessService(db)
    company = service.get_company(str(company_id))
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "id": str(company.id),
        "company_name": company.company_name,
        "legal_name": company.legal_name,
        "trades": company.trades,
        "primary_contact": {
            "name": company.primary_contact_name,
            "email": company.primary_contact_email,
            "phone": company.primary_contact_phone
        },
        "address": {
            "address": company.address,
            "city": company.city,
            "state": company.state,
            "zip_code": company.zip_code
        },
        "license": {
            "number": company.license_number,
            "state": company.license_state,
            "expiry": company.license_expiry.isoformat() if company.license_expiry else None
        },
        "status": company.status
    }


# ITB and Bid Endpoints

@router.post("/itbs")
async def create_itb(
    request: CreateITBRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permissions(["bids:write"]))
):
    """Create Invitation to Bid"""
    service = BidManagementService(db)
    itb = service.create_itb(request, current_user["id"])
    
    return {
        "id": str(itb.id),
        "itb_number": itb.itb_number,
        "title": itb.title,
        "trade": itb.trade,
        "bid_deadline": itb.bid_deadline.isoformat(),
        "status": itb.status
    }


@router.get("/itbs")
async def list_itbs(
    project_id: Optional[str] = None,
    trade: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List ITBs"""
    service = BidManagementService(db)
    itbs = service.list_itbs(project_id, trade, status)
    
    return [
        {
            "id": str(i.id),
            "itb_number": i.itb_number,
            "title": i.title,
            "trade": i.trade,
            "bid_deadline": i.bid_deadline.isoformat() if i.bid_deadline else None,
            "status": i.status
        }
        for i in itbs
    ]


@router.post("/itbs/{itb_id}/bids")
async def submit_bid(
    itb_id: UUID,
    request: SubmitBidRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Submit bid for ITB"""
    service = BidManagementService(db)
    
    # Get user's company
    scoped_service = ScopedAccessService(db)
    sub_user = db.query(SubcontractorUser).filter(
        SubcontractorUser.user_id == current_user["id"]
    ).first()
    
    if not sub_user:
        raise HTTPException(status_code=403, detail="Not a subcontractor user")
    
    bid = service.submit_bid(str(sub_user.company_id), request, current_user["id"])
    
    return {
        "id": str(bid.id),
        "bid_number": bid.bid_number,
        "total_amount": float(bid.total_bid_amount),
        "status": bid.status,
        "submitted_at": bid.submitted_at.isoformat() if bid.submitted_at else None
    }


@router.get("/itbs/{itb_id}/bids")
async def list_bids(
    itb_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List bids for ITB"""
    service = BidManagementService(db)
    bids = service.list_bids(itb_id=str(itb_id))
    
    return [
        {
            "id": str(b.id),
            "bid_number": b.bid_number,
            "company_id": str(b.company_id),
            "total_amount": float(b.total_bid_amount),
            "status": b.status,
            "score": b.score
        }
        for b in bids
    ]


# Payment Application Endpoints

@router.post("/payment-apps/sov")
async def create_sov(
    request: CreateSOVRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permissions(["payments:write"]))
):
    """Create Schedule of Values"""
    service = PaymentApplicationService(db)
    sov = service.create_sov(request)
    
    return {
        "id": str(sov.id),
        "sov_number": sov.sov_number,
        "contract_amount": float(sov.contract_amount),
        "line_items": sov.line_items
    }


@router.get("/payment-apps/sov")
async def list_sovs(
    project_id: Optional[str] = None,
    company_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List SOVs"""
    service = PaymentApplicationService(db)
    sovs = service.list_sovs(project_id, company_id)
    
    return [
        {
            "id": str(s.id),
            "sov_number": s.sov_number,
            "contract_amount": float(s.contract_amount),
            "retention_percentage": float(s.retention_percentage)
        }
        for s in sovs
    ]


@router.post("/payment-apps")
async def create_payment_app(
    request: CreatePaymentAppRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create payment application"""
    service = PaymentApplicationService(db)
    app = service.create_payment_app(request, current_user["id"])
    
    return {
        "id": str(app.id),
        "app_number": app.app_number,
        "current_payment_due": float(app.current_payment_due),
        "status": app.status
    }


@router.get("/payment-apps")
async def list_payment_apps(
    sov_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List payment applications"""
    service = PaymentApplicationService(db)
    apps = service.list_payment_apps(sov_id, status)
    
    return [
        {
            "id": str(a.id),
            "app_number": a.app_number,
            "period_start": a.period_start.isoformat() if a.period_start else None,
            "period_end": a.period_end.isoformat() if a.period_end else None,
            "current_payment_due": float(a.current_payment_due),
            "status": a.status
        }
        for a in apps
    ]


@router.get("/payment-apps/sov/{sov_id}/summary")
async def get_payment_summary(
    sov_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get payment summary for SOV"""
    service = PaymentApplicationService(db)
    summary = service.get_payment_summary(str(sov_id))
    
    return summary


# Daily Report Endpoints

@router.post("/daily-reports")
async def create_daily_report(
    request: CreateDailyReportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create daily report"""
    service = DailyReportService(db)
    report = service.create_report(request, current_user["id"])
    
    return {
        "id": str(report.id),
        "report_number": report.report_number,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "workers_on_site": report.workers_on_site,
        "status": report.status
    }


@router.get("/daily-reports")
async def list_daily_reports(
    project_id: Optional[str] = None,
    company_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List daily reports"""
    service = DailyReportService(db)
    reports = service.list_reports(project_id, company_id, start_date, end_date)
    
    return [
        {
            "id": str(r.id),
            "report_number": r.report_number,
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "workers_on_site": r.workers_on_site,
            "hours_worked": float(r.hours_worked),
            "status": r.status
        }
        for r in reports
    ]


@router.get("/daily-reports/{report_id}")
async def get_daily_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get daily report details"""
    service = DailyReportService(db)
    report = service.get_report(str(report_id))
    
    if not report:
        raise HTTPException(status_code=404, detail="Daily report not found")
    
    return {
        "id": str(report.id),
        "report_number": report.report_number,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "weather": {
            "condition": report.weather_condition,
            "temperature_low": report.temperature_low,
            "temperature_high": report.temperature_high,
            "precipitation": float(report.precipitation) if report.precipitation else None
        },
        "work": {
            "description": report.work_description,
            "areas": report.work_areas,
            "workers_on_site": report.workers_on_site,
            "hours_worked": float(report.hours_worked)
        },
        "equipment": report.equipment_used,
        "materials": report.materials_delivered,
        "delays": report.delays,
        "safety_incidents": report.safety_incidents,
        "status": report.status
    }


# Export router
__all__ = ["router"]
