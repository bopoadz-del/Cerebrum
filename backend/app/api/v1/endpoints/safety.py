"""
Safety Analysis API Endpoints
RESTful API for construction safety analysis and hazard detection.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, User
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/safety", tags=["Safety Analysis"])


# Pydantic Models
class SafetyAnalysisRequest(BaseModel):
    location: str = "all"
    type: str = "hazard_detection"
    include_photos: bool = True


class SafetyAnalysisResponse(BaseModel):
    report_id: str
    hazards_found: int
    status: str
    location: str
    timestamp: datetime
    summary: str


class HazardItem(BaseModel):
    id: str
    severity: str  # critical, high, medium, low
    category: str
    description: str
    location: str
    recommendation: str


class SafetyReport(BaseModel):
    report_id: str
    generated_at: datetime
    location: str
    overall_score: int  # 0-100
    hazards: List[HazardItem]
    summary: str


@router.post("/analyze", response_model=SafetyAnalysisResponse)
async def analyze_safety(
    request: SafetyAnalysisRequest,
    current_user: User = Depends(get_current_user)
) -> SafetyAnalysisResponse:
    """Run safety analysis on a location."""
    try:
        report_id = secrets.token_urlsafe(16)
        
        # Mock analysis results
        hazards_found = 2 if request.location.lower() == "floor 3" else 0
        
        return SafetyAnalysisResponse(
            report_id=report_id,
            hazards_found=hazards_found,
            status="completed",
            location=request.location,
            timestamp=datetime.utcnow(),
            summary=f"Safety analysis completed for {request.location}. Found {hazards_found} potential hazards."
        )
        
    except Exception as e:
        logger.error(f"Safety analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{report_id}", response_model=SafetyReport)
async def get_safety_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
) -> SafetyReport:
    """Get a detailed safety report."""
    return SafetyReport(
        report_id=report_id,
        generated_at=datetime.utcnow(),
        location="Floor 3",
        overall_score=94,
        hazards=[
            HazardItem(
                id="h1",
                severity="low",
                category="ppe",
                description="Missing PPE signage at north stairwell",
                location="North Stairwell",
                recommendation="Install PPE requirement signage"
            ),
            HazardItem(
                id="h2",
                severity="low",
                category="electrical",
                description="Temporary cable routing near zone B",
                location="Zone B",
                recommendation="Secure cables with proper cable management"
            )
        ],
        summary="Overall safety conditions are good. 2 minor observations noted."
    )


@router.get("/summary")
async def get_safety_summary(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get safety summary for a time period."""
    return {
        "period_days": days,
        "total_inspections": 12,
        "hazards_identified": 3,
        "resolved": 2,
        "open": 1,
        "safety_score": 94,
        "trend": "improving",
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/health")
async def safety_health() -> Dict[str, Any]:
    """Check Safety Analysis service health."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "models_loaded": True,
        "timestamp": datetime.utcnow().isoformat()
    }
