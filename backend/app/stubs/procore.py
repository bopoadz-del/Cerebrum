"""
Procore API Stub

Stub implementation for Procore construction management platform.
"""

from typing import Any, Dict, List, Optional
from .base import BaseStub, StubResponse


class ProcoreStub(BaseStub):
    """
    Stub for Procore API.
    
    Provides mock data for:
    - Projects
    - RFIs
    - Submittals
    - Drawings
    - Documents
    """
    
    service_name = "procore"
    version = "2.0.0-stub"
    
    # Mock data stores
    _projects = [
        {"id": 1, "name": "Downtown Tower", "active": True, "city": "New York"},
        {"id": 2, "name": "Riverside Complex", "active": True, "city": "Chicago"},
        {"id": 3, "name": "Metro Station", "active": False, "city": "Los Angeles"},
    ]
    
    _rfis = [
        {"id": 101, "subject": "Foundation depth", "status": "open", "project_id": 1},
        {"id": 102, "subject": "Steel grade", "status": "closed", "project_id": 1},
    ]
    
    _submittals = [
        {"id": 201, "title": "Concrete mix design", "status": "approved", "project_id": 1},
        {"id": 202, "title": "Rebar certification", "status": "pending", "project_id": 2},
    ]
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "endpoints": ["projects", "rfis", "submittals", "drawings"],
        }
    
    def get_projects(self) -> StubResponse:
        """Get mock projects."""
        self._log_call("get_projects")
        return self._success_response(
            data=self._projects,
            message="Retrieved 3 projects (stub)",
        )
    
    def get_project(self, project_id: int) -> StubResponse:
        """Get mock project by ID."""
        self._log_call("get_project", project_id=project_id)
        project = next((p for p in self._projects if p["id"] == project_id), None)
        if project:
            return self._success_response(data=project)
        return self._error_response(f"Project {project_id} not found", "NOT_FOUND")
    
    def get_rfis(self, project_id: Optional[int] = None) -> StubResponse:
        """Get mock RFIs."""
        self._log_call("get_rfis", project_id=project_id)
        rfis = self._rfis
        if project_id:
            rfis = [r for r in rfis if r["project_id"] == project_id]
        return self._success_response(data=rfis, message=f"Retrieved {len(rfis)} RFIs (stub)")
    
    def get_submittals(self, project_id: Optional[int] = None) -> StubResponse:
        """Get mock submittals."""
        self._log_call("get_submittals", project_id=project_id)
        submittals = self._submittals
        if project_id:
            submittals = [s for s in submittals if s["project_id"] == project_id]
        return self._success_response(
            data=submittals,
            message=f"Retrieved {len(submittals)} submittals (stub)",
        )
    
    def create_rfi(self, project_id: int, subject: str, **kwargs) -> StubResponse:
        """Create mock RFI."""
        self._log_call("create_rfi", project_id=project_id, subject=subject)
        new_rfi = {
            "id": 999,
            "subject": subject,
            "status": "open",
            "project_id": project_id,
            "stub_created": True,
        }
        return self._success_response(
            data=new_rfi,
            message="RFI created (stub - no actual API call)",
        )
    
    def sync_project(self, project_id: int) -> StubResponse:
        """Mock project sync."""
        self._log_call("sync_project", project_id=project_id)
        return self._success_response(
            data={"project_id": project_id, "synced": True, "records": 42},
            message="Project synced (stub)",
        )
