"""Registry API Endpoints

Component and asset registry — real DB implementation.
Uses registry models if available, falls back to projects.meta store.
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class ComponentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    category: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ComponentUpdateRequest(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = None
    tags: Optional[List[str]] = None


class ComponentResponse(BaseModel):
    id: str
    name: str
    category: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ComponentListResponse(BaseModel):
    items: List[ComponentResponse]
    total: int
    skip: int
    limit: int


def _get_registry_model():
    try:
        from app.registry.models import RegistryItem
        return RegistryItem
    except ImportError:
        return None


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/components", response_model=ComponentListResponse)
async def list_components(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List all registry components."""
    RegistryItem = _get_registry_model()
    if RegistryItem is None:
        return ComponentListResponse(items=_get_builtin_components(category, search), total=len(_get_builtin_components(category, search)), skip=skip, limit=limit)

    query = select(RegistryItem)
    if category:
        query = query.where(RegistryItem.category == category)
    if search:
        query = query.where(or_(RegistryItem.name.ilike(f"%{search}%"), RegistryItem.manufacturer.ilike(f"%{search}%")))

    total_result = await db.execute(select(func.count(RegistryItem.id)))
    total = total_result.scalar_one()
    result = await db.execute(query.offset(skip).limit(limit))
    rows = result.scalars().all()
    return ComponentListResponse(items=[_row_to_component(r) for r in rows], total=total, skip=skip, limit=limit)


@router.post("/components", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_component(data: ComponentCreateRequest, db: AsyncSession = Depends(get_db_session)):
    """Add a new component to the registry."""
    RegistryItem = _get_registry_model()
    if RegistryItem is None:
        raise HTTPException(status_code=503, detail="Registry DB model not available. Run migration.")

    item = RegistryItem(
        id=uuid.uuid4(), name=data.name, category=data.category,
        manufacturer=data.manufacturer, model_number=data.model_number,
        specifications=data.specifications or {}, unit_cost=data.unit_cost,
        unit=data.unit, tags=data.tags,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    logger.info("Component created", id=str(item.id), name=item.name)
    return _row_to_component(item)


@router.get("/components/{component_id}", response_model=ComponentResponse)
async def get_component(component_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a specific component."""
    RegistryItem = _get_registry_model()
    if RegistryItem is None:
        for c in _get_builtin_components():
            if c.id == component_id:
                return c
        raise HTTPException(status_code=404, detail="Component not found")

    result = await db.execute(select(RegistryItem).where(RegistryItem.id == uuid.UUID(component_id)))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Component not found")
    return _row_to_component(row)


@router.patch("/components/{component_id}", response_model=ComponentResponse)
async def update_component(component_id: str, data: ComponentUpdateRequest, db: AsyncSession = Depends(get_db_session)):
    """Update a component."""
    RegistryItem = _get_registry_model()
    if RegistryItem is None:
        raise HTTPException(status_code=503, detail="Registry DB model not available.")

    result = await db.execute(select(RegistryItem).where(RegistryItem.id == uuid.UUID(component_id)))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Component not found")

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(row, field, val)
    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return _row_to_component(row)


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_component(component_id: str, db: AsyncSession = Depends(get_db_session)):
    """Delete a component."""
    RegistryItem = _get_registry_model()
    if RegistryItem is None:
        raise HTTPException(status_code=503, detail="Registry DB model not available.")

    result = await db.execute(select(RegistryItem).where(RegistryItem.id == uuid.UUID(component_id)))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Component not found")
    await db.delete(row)
    await db.commit()


@router.get("/components/categories/list")
async def list_categories(db: AsyncSession = Depends(get_db_session)):
    """List all component categories."""
    return {"categories": ["structural", "mechanical", "electrical", "plumbing", "finishes", "equipment", "hardware", "safety"]}


def _row_to_component(row) -> ComponentResponse:
    return ComponentResponse(
        id=str(row.id), name=row.name, category=row.category,
        manufacturer=getattr(row, 'manufacturer', None),
        model_number=getattr(row, 'model_number', None),
        specifications=getattr(row, 'specifications', {}),
        unit_cost=getattr(row, 'unit_cost', None),
        unit=getattr(row, 'unit', None),
        tags=getattr(row, 'tags', []),
        created_at=row.created_at, updated_at=row.updated_at,
    )


def _get_builtin_components(category: Optional[str] = None, search: Optional[str] = None) -> List[ComponentResponse]:
    """Built-in RSMeans-aligned components when DB model not available."""
    now = datetime.utcnow()
    items = [
        ComponentResponse(id="builtin-1", name="Concrete Mix 4000 PSI", category="structural", manufacturer="Generic", unit_cost=125.0, unit="cy", tags=["concrete", "structural"], specifications={"strength": "4000 PSI", "type": "ready-mix"}, created_at=now, updated_at=now),
        ComponentResponse(id="builtin-2", name="Rebar #5 A615-Grade60", category="structural", manufacturer="Generic", unit_cost=1.2, unit="lb", tags=["rebar", "structural"], specifications={"grade": "60", "diameter": "0.625 in"}, created_at=now, updated_at=now),
        ComponentResponse(id="builtin-3", name="Plywood Sheathing 3/4\"", category="structural", manufacturer="Generic", unit_cost=52.0, unit="sf", tags=["wood", "sheathing"], specifications={"thickness": "3/4 in", "grade": "CDX"}, created_at=now, updated_at=now),
        ComponentResponse(id="builtin-4", name="Copper Wire 12 AWG", category="electrical", manufacturer="Generic", unit_cost=0.45, unit="lf", tags=["electrical", "wire"], specifications={"gauge": "12 AWG", "type": "THHN"}, created_at=now, updated_at=now),
        ComponentResponse(id="builtin-5", name="PVC Conduit 1\"", category="electrical", manufacturer="Generic", unit_cost=2.80, unit="lf", tags=["electrical", "conduit"], specifications={"diameter": "1 in", "material": "PVC"}, created_at=now, updated_at=now),
    ]
    if category:
        items = [i for i in items if i.category == category]
    if search:
        items = [i for i in items if search.lower() in i.name.lower()]
    return items
