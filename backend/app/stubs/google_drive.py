"""
Google Drive Stub

Provides a stub implementation for Google Drive service when Google OAuth
is not configured or unavailable.
"""
from typing import List, Dict, Any, Optional
from .base import BaseStub, StubResponse


class GoogleDriveStub(BaseStub):
    """Stub for Google Drive integration."""
    
    service_name = "google_drive"
    
    def list_files(self, folder_id: Optional[str] = None) -> StubResponse:
        """Return stub file listing."""
        return self._success([
            {
                "id": "stub_file_1",
                "name": "Example Document.pdf",
                "mime_type": "application/pdf",
                "size": 1024000,
                "modified_time": "2026-02-20T12:00:00Z",
                "is_folder": False,
                "web_view_link": "https://drive.google.com/file/d/stub/view"
            },
            {
                "id": "stub_folder_1",
                "name": "Example Folder",
                "mime_type": "application/vnd.google-apps.folder",
                "size": None,
                "modified_time": "2026-02-20T10:00:00Z",
                "is_folder": True,
                "web_view_link": "https://drive.google.com/drive/folders/stub"
            }
        ], meta={"folder_id": folder_id, "total": 2})
    
    def get_auth_url(self) -> StubResponse:
        """Return stub auth URL."""
        return self._success({
            "auth_url": "https://accounts.google.com/o/oauth2/stub",
            "state": "stub_state_123"
        })
    
    def is_connected(self) -> StubResponse:
        """Return not connected status."""
        return self._success({"connected": False}, meta={"note": "Google Drive not configured (stub mode)"})
