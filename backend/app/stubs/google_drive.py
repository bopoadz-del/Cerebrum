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
    version = "1.0.0-stub"
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "endpoints": ["list_files", "upload_file", "get_auth_url"],
        }
    
    def list_files(self, folder_id: Optional[str] = None) -> StubResponse:
        """Return stub file listing."""
        return self._success_response(
            data={
                "files": [
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
                ],
                "folder_id": folder_id,
                "total": 2,
            },
            message="Retrieved 2 files (stub)",
        )
    
    def get_auth_url(self) -> StubResponse:
        """Return stub auth URL."""
        return self._success({
            "auth_url": "https://accounts.google.com/o/oauth2/stub",
            "state": "stub_state_123"
        })
    
    def is_connected(self) -> StubResponse:
        """Return not connected status."""
        return self._success_response(
            data={"connected": False},
            message="Google Drive not configured (stub mode)",
        )
    
    def upload_file(self, filename: str, mime_type: str, content: Optional[bytes] = None) -> StubResponse:
        """Return stub file upload."""
        return self._success_response(
            data={
                "id": "stub_upload_1",
                "name": filename,
                "mime_type": mime_type,
                "uploaded": True,
            },
            message=f"File {filename} uploaded (stub)",
        )
    
    def drive_stubbed(self) -> bool:
        """Return True to indicate stub mode."""
        return True
    
    def credentials_available(self) -> bool:
        """Return True for stub credentials."""
        return True
