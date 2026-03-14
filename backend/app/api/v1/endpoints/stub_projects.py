"""Projects API Endpoints (Stub)

RESTful API for project management.
This is a stub implementation - replace with full implementation as needed.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/projects", tags=["projects"])


# Pydantic Models
class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = None
    budget: Optional[float] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    budget: Optional[float] = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int


# Stub data
STUB_PROJECTS = [
    {
        "id": "1",
        "name": "Downtown Office Tower",
        "description": "25-story commercial building",
        "location": "Downtown District",
        "budget": 50000000,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    {
        "id": "2", 
        "name": "Residential Complex A",
        "description": "200-unit apartment complex",
        "location": "Westside",
        "budget": 30000000,
        "status": "planning",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
]


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
):
    """List all projects."""
    projects = STUB_PROJECTS
    if status:
        projects = [p for p in projects if p["status"] == status]
    return ProjectListResponse(
        items=[ProjectResponse(**p) for p in projects],
        total=len(projects)
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreateRequest):
    """Create a new project."""
    new_project = {
        "id": str(len(STUB_PROJECTS) + 1),
        "name": data.name,
        "description": data.description,
        "location": data.location,
        "budget": data.budget,
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    STUB_PROJECTS.append(new_project)
    return ProjectResponse(**new_project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a specific project by ID."""
    for project in STUB_PROJECTS:
        if project["id"] == project_id:
            return ProjectResponse(**project)
    raise HTTPException(status_code=404, detail="Project not found")


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectCreateRequest):
    """Update a project."""
    for project in STUB_PROJECTS:
        if project["id"] == project_id:
            project["name"] = data.name
            project["description"] = data.description
            project["location"] = data.location
            project["budget"] = data.budget
            project["updated_at"] = datetime.now()
            return ProjectResponse(**project)
    raise HTTPException(status_code=404, detail="Project not found")


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str):
    """Delete a project."""
    for i, project in enumerate(STUB_PROJECTS):
        if project["id"] == project_id:
            STUB_PROJECTS.pop(i)
            return
    raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/documents")
async def list_project_documents(project_id: str):
    """List documents for a project."""
    return {"items": [], "total": 0}


@router.get("/{project_id}/team")
async def list_project_team(project_id: str):
    """List team members for a project."""
    return {"items": [], "total": 0}
