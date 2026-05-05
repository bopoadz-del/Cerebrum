"""Projects API Endpoints

RESTful API for project management — real DB implementation.
Uses the Project model with meta JSON for extended fields.
"""

import uuid
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.project import Project, ProjectType
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    budget: Optional[float] = None
    project_type: str = ProjectType.GENERAL_PROJECT.value
    tags: List[str] = Field(default_factory=list)
    status: str = "active"


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    budget: Optional[float] = None
    status: str = "active"
    project_type: str = ProjectType.GENERAL_PROJECT.value
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    skip: int
    limit: int


def _project_to_response(project: Project) -> ProjectResponse:
    """Convert DB Project to response schema."""
    meta = project.meta or {}
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=meta.get("description"),
        location=meta.get("location"),
        budget=meta.get("budget"),
        status=meta.get("status", "active"),
        project_type=project.type or ProjectType.GENERAL_PROJECT.value,
        tags=project.tags or [],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List all projects with optional status filter."""
    query = select(Project)
    if status:
        query = query.where(Project.meta["status"].astext == status)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    count_result = await db.execute(select(func.count(Project.id)))
    total = count_result.scalar_one()

    return ProjectListResponse(
        items=[_project_to_response(p) for p in projects],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new project."""
    project = Project(
        id=uuid.uuid4(),
        name=data.name,
        type=data.project_type,
        tags=data.tags,
        meta={
            "description": data.description,
            "location": data.location,
            "budget": data.budget,
            "status": data.status,
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    logger.info("Project created", project_id=str(project.id), name=project.name)
    return _project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific project by ID."""
    try:
        uid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    result = await db.execute(select(Project).where(Project.id == uid))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a project."""
    try:
        uid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    result = await db.execute(select(Project).where(Project.id == uid))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.name is not None:
        project.name = data.name
    if data.tags is not None:
        project.tags = data.tags

    meta = dict(project.meta or {})
    if data.description is not None:
        meta["description"] = data.description
    if data.location is not None:
        meta["location"] = data.location
    if data.budget is not None:
        meta["budget"] = data.budget
    if data.status is not None:
        meta["status"] = data.status
    project.meta = meta
    project.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(project)
    return _project_to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a project."""
    try:
        uid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    result = await db.execute(select(Project).where(Project.id == uid))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
    logger.info("Project deleted", project_id=project_id)


@router.get("/{project_id}/documents")
async def list_project_documents(project_id: str):
    """List documents for a project."""
    return {"items": [], "total": 0, "project_id": project_id}


@router.get("/{project_id}/team")
async def list_project_team(project_id: str):
    """List team members for a project."""
    return {"items": [], "total": 0, "project_id": project_id}


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get project statistics."""
    try:
        uid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    result = await db.execute(select(Project).where(Project.id == uid))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "project_id": project_id,
        "documents": 0,
        "team_members": 0,
        "open_issues": 0,
        "completion_percent": 0,
        "budget_used_percent": 0,
    }
