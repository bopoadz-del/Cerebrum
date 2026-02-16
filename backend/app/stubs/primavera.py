"""
Oracle Primavera P6 Stub

Stub implementation for Oracle Primavera P6 project management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from .base import BaseStub, StubResponse


class PrimaveraStub(BaseStub):
    """
    Stub for Oracle Primavera P6 API.
    
    Provides mock data for:
    - Projects
    - Activities
    - Resources
    - Schedules
    """
    
    service_name = "primavera"
    version = "21.12-stub"
    
    _projects = [
        {
            "id": "PRJ001",
            "name": "Highway Expansion",
            "start_date": datetime.utcnow().isoformat(),
            "finish_date": (datetime.utcnow() + timedelta(days=365)).isoformat(),
            "status": "Active",
        },
        {
            "id": "PRJ002",
            "name": "Bridge Construction",
            "start_date": datetime.utcnow().isoformat(),
            "finish_date": (datetime.utcnow() + timedelta(days=180)).isoformat(),
            "status": "Planned",
        },
    ]
    
    _activities = [
        {"id": "ACT001", "name": "Site Preparation", "duration": 10, "project_id": "PRJ001"},
        {"id": "ACT002", "name": "Foundation Work", "duration": 20, "project_id": "PRJ001"},
        {"id": "ACT003", "name": "Steel Erection", "duration": 30, "project_id": "PRJ001"},
    ]
    
    _resources = [
        {"id": "RES001", "name": "Project Manager", "type": "Labor", "rate": 150.0},
        {"id": "RES002", "name": "Crane Operator", "type": "Labor", "rate": 75.0},
        {"id": "RES003", "name": "Concrete Mixer", "type": "Equipment", "rate": 200.0},
    ]
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "endpoints": ["projects", "activities", "resources", "schedules", "wbs"],
        }
    
    def get_projects(self) -> StubResponse:
        """Get mock projects."""
        self._log_call("get_projects")
        return self._success_response(
            data=self._projects,
            message=f"Retrieved {len(self._projects)} projects (stub)",
        )
    
    def get_project(self, project_id: str) -> StubResponse:
        """Get mock project by ID."""
        self._log_call("get_project", project_id=project_id)
        project = next((p for p in self._projects if p["id"] == project_id), None)
        if project:
            return self._success_response(data=project)
        return self._error_response(f"Project {project_id} not found", "NOT_FOUND")
    
    def get_activities(self, project_id: Optional[str] = None) -> StubResponse:
        """Get mock activities."""
        self._log_call("get_activities", project_id=project_id)
        activities = self._activities
        if project_id:
            activities = [a for a in activities if a.get("project_id") == project_id]
        return self._success_response(
            data=activities,
            message=f"Retrieved {len(activities)} activities (stub)",
        )
    
    def get_resources(self) -> StubResponse:
        """Get mock resources."""
        self._log_call("get_resources")
        return self._success_response(
            data=self._resources,
            message=f"Retrieved {len(self._resources)} resources (stub)",
        )
    
    def get_schedule(self, project_id: str) -> StubResponse:
        """Get mock schedule."""
        self._log_call("get_schedule", project_id=project_id)
        schedule = {
            "project_id": project_id,
            "activities": self._activities,
            "critical_path": ["ACT001", "ACT002"],
            "total_float": 5,
            "schedule_type": "CPM",
        }
        return self._success_response(data=schedule, message="Schedule retrieved (stub)")
    
    def update_activity(self, activity_id: str, **updates) -> StubResponse:
        """Mock activity update."""
        self._log_call("update_activity", activity_id=activity_id, **updates)
        return self._success_response(
            data={"activity_id": activity_id, "updated": True, "fields": list(updates.keys())},
            message="Activity updated (stub)",
        )
