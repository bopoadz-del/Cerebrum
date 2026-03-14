"""Registry API Endpoints (Stub)

Component and asset registry for construction elements.
This is a stub implementation - replace with full implementation as needed.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

router = APIRouter()


# Pydantic Models
class ComponentCreateRequest(BaseModel):
    name: str
    category: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    unit_cost: Optional[float] = None


class ComponentResponse(BaseModel):
    id: str
    name: str
    category: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    unit_cost: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ComponentListResponse(BaseModel):
    items: List[ComponentResponse]
    total: int


# Stub data
STUB_COMPONENTS = [
    {
        "id": "1",
        "name": "Steel Beam - W12x26",
        "category": "structural",
        "manufacturer": "Nucor",
        "model_number": "W12x26-A992",
        "specifications": {"weight": "26 lb/ft", "depth": "12.2 in"},
        "unit_cost": 45.50,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "id": "2",
        "name": "Concrete Block - 8x8x16",
        "category": "masonry",
        "manufacturer": "Oldcastle",
        "model_number": "CMU-8-16",
        "specifications": {"compressive_strength": "1900 psi"},
        "unit_cost": 2.25,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
]


@router.get("/components", response_model=ComponentListResponse)
async def list_components(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all registry components."""
    components = STUB_COMPONENTS
    if category:
        components = [c for c in components if c["category"] == category]
    if search:
        components = [c for c in components if search.lower() in c["name"].lower()]
    return ComponentListResponse(
        items=[ComponentResponse(**c) for c in components],
        total=len(components)
    )


@router.post("/components", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_component(data: ComponentCreateRequest):
    """Create a new registry component."""
    new_component = {
        "id": str(len(STUB_COMPONENTS) + 1),
        **data.model_dump(),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    STUB_COMPONENTS.append(new_component)
    return ComponentResponse(**new_component)


@router.get("/components/{component_id}", response_model=ComponentResponse)
async def get_component(component_id: str):
    """Get a specific component by ID."""
    for component in STUB_COMPONENTS:
        if component["id"] == component_id:
            return ComponentResponse(**component)
    raise HTTPException(status_code=404, detail="Component not found")


@router.patch("/components/{component_id}", response_model=ComponentResponse)
async def update_component(component_id: str, data: ComponentCreateRequest):
    """Update a component."""
    for component in STUB_COMPONENTS:
        if component["id"] == component_id:
            for key, value in data.model_dump().items():
                if value is not None:
                    component[key] = value
            component["updated_at"] = datetime.now()
            return ComponentResponse(**component)
    raise HTTPException(status_code=404, detail="Component not found")


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_component(component_id: str):
    """Delete a component."""
    for i, component in enumerate(STUB_COMPONENTS):
        if component["id"] == component_id:
            STUB_COMPONENTS.pop(i)
            return
    raise HTTPException(status_code=404, detail="Component not found")


@router.get("/categories")
async def list_categories():
    """List all component categories."""
    categories = list(set(c["category"] for c in STUB_COMPONENTS))
    return {"categories": categories}
