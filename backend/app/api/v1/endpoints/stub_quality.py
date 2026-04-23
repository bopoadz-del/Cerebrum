"""Quality API Endpoints — real DB implementation.

Inspections, compliance tracking, and quality standards.
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum

from app.db.session import get_db_session
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class InspectionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"


# ─── Schemas ────────────────────────────────────────────────────────────────

class InspectionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    project_id: Optional[str] = None
    inspection_type: str
    description: Optional[str] = None
    scheduled_date: Optional[datetime] = None


class InspectionCompleteRequest(BaseModel):
    status: InspectionStatus
    findings: Optional[List[Dict[str, Any]]] = None
    checklist_results: Optional[Dict[str, Any]] = None


class InspectionResponse(BaseModel):
    id: str
    title: str
    project_id: Optional[str] = None
    inspection_type: str
    description: Optional[str] = None
    status: str
    inspector_id: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    findings: Optional[List[Dict[str, Any]]] = None
    checklist_results: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class InspectionListResponse(BaseModel):
    items: List[InspectionResponse]
    total: int
    skip: int
    limit: int


class ChecklistItem(BaseModel):
    id: str
    description: str
    required: bool = True
    category: Optional[str] = None


class QualityStandardResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    category: str
    checklist_items: List[Dict[str, Any]] = Field(default_factory=list)


def _row_to_inspection(row) -> InspectionResponse:
    return InspectionResponse(
        id=str(row.id),
        title=row.title,
        project_id=str(row.project_id) if row.project_id else None,
        inspection_type=row.inspection_type,
        description=row.description,
        status=row.status,
        inspector_id=str(row.inspector_id) if row.inspector_id else None,
        scheduled_date=row.scheduled_date,
        completed_date=row.completed_date,
        findings=row.findings,
        checklist_results=row.checklist_results,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ─── Lazy model import (table created by migration 009) ─────────────────────

def _get_models():
    try:
        from app.models.quality import QualityInspection, QualityStandard
        return QualityInspection, QualityStandard
    except ImportError:
        raise HTTPException(status_code=503, detail="Quality module not yet migrated. Run migration 009.")


# ─── Inspection Routes ───────────────────────────────────────────────────────

@router.get("/inspections", response_model=InspectionListResponse)
async def list_inspections(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    project_id: Optional[str] = None,
    inspection_status: Optional[InspectionStatus] = Query(None, alias="status"),
    inspection_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List all quality inspections with filters."""
    QualityInspection, _ = _get_models()
    query = select(QualityInspection)
    if project_id:
        query = query.where(QualityInspection.project_id == uuid.UUID(project_id))
    if inspection_status:
        query = query.where(QualityInspection.status == inspection_status.value)
    if inspection_type:
        query = query.where(QualityInspection.inspection_type == inspection_type)

    total_result = await db.execute(select(func.count(QualityInspection.id)))
    total = total_result.scalar_one()

    result = await db.execute(query.order_by(QualityInspection.created_at.desc()).offset(skip).limit(limit))
    rows = result.scalars().all()
    return InspectionListResponse(items=[_row_to_inspection(r) for r in rows], total=total, skip=skip, limit=limit)


@router.post("/inspections", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    data: InspectionCreateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new quality inspection."""
    QualityInspection, _ = _get_models()
    inspection = QualityInspection(
        id=uuid.uuid4(),
        title=data.title,
        project_id=uuid.UUID(data.project_id) if data.project_id else None,
        inspection_type=data.inspection_type,
        description=data.description,
        status=InspectionStatus.PENDING.value,
        scheduled_date=data.scheduled_date,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)
    logger.info("Inspection created", id=str(inspection.id), title=inspection.title)
    return _row_to_inspection(inspection)


@router.get("/inspections/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(inspection_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a specific inspection."""
    QualityInspection, _ = _get_models()
    result = await db.execute(select(QualityInspection).where(QualityInspection.id == uuid.UUID(inspection_id)))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return _row_to_inspection(row)


@router.post("/inspections/{inspection_id}/complete", response_model=InspectionResponse)
async def complete_inspection(
    inspection_id: str,
    data: InspectionCompleteRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Complete an inspection with results and findings."""
    QualityInspection, _ = _get_models()
    result = await db.execute(select(QualityInspection).where(QualityInspection.id == uuid.UUID(inspection_id)))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")

    row.status = data.status.value
    row.findings = data.findings or []
    row.checklist_results = data.checklist_results
    row.completed_date = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    logger.info("Inspection completed", id=inspection_id, status=data.status.value)
    return _row_to_inspection(row)


@router.delete("/inspections/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inspection(inspection_id: str, db: AsyncSession = Depends(get_db_session)):
    """Delete an inspection."""
    QualityInspection, _ = _get_models()
    result = await db.execute(select(QualityInspection).where(QualityInspection.id == uuid.UUID(inspection_id)))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")
    await db.delete(row)
    await db.commit()


# ─── Standards Routes ────────────────────────────────────────────────────────

@router.get("/standards", response_model=Dict[str, Any])
async def list_standards(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List quality standards and checklists."""
    _, QualityStandard = _get_models()
    query = select(QualityStandard)
    if category:
        query = query.where(QualityStandard.category == category)
    result = await db.execute(query)
    rows = result.scalars().all()
    items = [{"id": str(r.id), "name": r.name, "code": r.code,
               "description": r.description, "category": r.category,
               "checklist_items": r.checklist_items} for r in rows]
    return {"items": items, "total": len(items)}


@router.get("/standards/{standard_id}")
async def get_standard(standard_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a specific quality standard."""
    _, QualityStandard = _get_models()
    result = await db.execute(select(QualityStandard).where(QualityStandard.id == uuid.UUID(standard_id)))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Standard not found")
    return {"id": str(row.id), "name": row.name, "code": row.code,
            "description": row.description, "category": row.category,
            "checklist_items": row.checklist_items}


# ─── Reports ────────────────────────────────────────────────────────────────

@router.get("/reports/summary")
async def get_quality_summary(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Get quality metrics summary."""
    QualityInspection, _ = _get_models()
    query = select(QualityInspection)
    if project_id:
        query = query.where(QualityInspection.project_id == uuid.UUID(project_id))

    result = await db.execute(query)
    inspections = result.scalars().all()
    total = len(inspections)
    by_status = {s.value: 0 for s in InspectionStatus}
    for i in inspections:
        if i.status in by_status:
            by_status[i.status] += 1

    return {
        "total_inspections": total,
        "passed": by_status["passed"],
        "failed": by_status["failed"],
        "pending": by_status["pending"],
        "in_progress": by_status["in_progress"],
        "pass_rate": round(by_status["passed"] / total, 2) if total > 0 else 0,
        "project_id": project_id,
    }
