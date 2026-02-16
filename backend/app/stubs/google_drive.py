"""
Google Drive Stub

Stub implementation for Google Drive API.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from .base import BaseStub, StubResponse


class GoogleDriveStub(BaseStub):
    """
    Stub for Google Drive API.
    
    Provides mock data for:
    - Files
    - Folders
    - Permissions
    - Uploads/Downloads
    """
    
    service_name = "google_drive"
    version = "v3-stub"
    
    _files = [
        {
            "id": "file_001",
            "name": "Project Specifications.pdf",
            "mimeType": "application/pdf",
            "size": "2048000",
            "createdTime": datetime.utcnow().isoformat(),
            "parents": ["folder_001"],
        },
        {
            "id": "file_002",
            "name": "Budget.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "size": "512000",
            "createdTime": datetime.utcnow().isoformat(),
            "parents": ["folder_001"],
        },
    ]
    
    _folders = [
        {"id": "folder_001", "name": "Project Alpha", "mimeType": "application/vnd.google-apps.folder"},
        {"id": "folder_002", "name": "Archive", "mimeType": "application/vnd.google-apps.folder"},
    ]
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "endpoints": ["files", "permissions", "uploads"],
        }
    
    def list_files(self, folder_id: Optional[str] = None) -> StubResponse:
        """Get mock files."""
        self._log_call("list_files", folder_id=folder_id)
        files = self._files
        if folder_id:
            files = [f for f in files if folder_id in f.get("parents", [])]
        return self._success_response(
            data={"files": files, "nextPageToken": None},
            message=f"Retrieved {len(files)} files (stub)",
        )
    
    def get_file(self, file_id: str) -> StubResponse:
        """Get mock file by ID."""
        self._log_call("get_file", file_id=file_id)
        file = next((f for f in self._files if f["id"] == file_id), None)
        if file:
            return self._success_response(data=file)
        return self._error_response(f"File {file_id} not found", "NOT_FOUND")
    
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> StubResponse:
        """Mock folder creation."""
        self._log_call("create_folder", name=name, parent_id=parent_id)
        new_folder = {
            "id": "folder_999",
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "created": True,
            "stub": True,
        }
        return self._success_response(
            data=new_folder,
            message=f"Folder '{name}' created (stub)",
        )
    
    def upload_file(self, name: str, content_type: str, **kwargs) -> StubResponse:
        """Mock file upload."""
        self._log_call("upload_file", name=name, content_type=content_type)
        new_file = {
            "id": "file_999",
            "name": name,
            "mimeType": content_type,
            "size": "1024",
            "uploaded": True,
            "stub": True,
        }
        return self._success_response(
            data=new_file,
            message=f"File '{name}' uploaded (stub - not stored)",
        )
    
    def share_file(self, file_id: str, email: str, role: str = "reader") -> StubResponse:
        """Mock file sharing."""
        self._log_call("share_file", file_id=file_id, email=email, role=role)
        return self._success_response(
            data={
                "file_id": file_id,
                "permission_id": "perm_999",
                "email": email,
                "role": role,
                "shared": True,
            },
            message="File shared (stub)",
        )
    
    def drive_stubbed(self) -> bool:
        """Return True to indicate this is a stub."""
        return True
    
    def credentials_available(self) -> bool:
        """Stub always reports credentials as available."""
        return True
