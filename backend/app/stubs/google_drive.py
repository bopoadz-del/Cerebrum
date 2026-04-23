"""
Google Drive Stub Implementation

Provides safe fallback for Google Drive operations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseStub, StubResponse, StubError


class GoogleDriveStub(BaseStub):
    """Stub implementation for Google Drive connector."""

    service_name = "google_drive"
    version = "1.0.0"

    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "mode": "stub",
            "available": True,
            "version": self.version,
        }

    def list_files(self, folder_id: Optional[str] = None) -> StubResponse:
        """Return stub file list."""
        self._log_call("list_files", folder_id=folder_id)
        return self._success_response(
            data={
                "files": [
                    {
                        "id": "stub-file-1",
                        "name": "Example Document.pdf",
                        "mimeType": "application/pdf",
                        "modifiedTime": datetime.utcnow().isoformat(),
                    },
                    {
                        "id": "stub-file-2",
                        "name": "Spreadsheet.xlsx",
                        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "modifiedTime": datetime.utcnow().isoformat(),
                    },
                ]
            },
            message="Google Drive file list (stubbed)",
        )

    def search_files(self, query: str) -> StubResponse:
        """Return stub search results."""
        self._log_call("search_files", query=query)
        return self._success_response(
            data={"files": []},
            message=f"Google Drive search for '{query}' (stubbed)",
        )

    def get_file(self, file_id: str) -> StubResponse:
        """Return stub file metadata."""
        self._log_call("get_file", file_id=file_id)
        return self._success_response(
            data={
                "id": file_id,
                "name": "Stub File.pdf",
                "mimeType": "application/pdf",
                "size": "1024",
            },
            message="Google Drive file metadata (stubbed)",
        )

    def upload_file(self, name: str, mime_type: str, folder_id: Optional[str] = None) -> StubResponse:
        """Return stub upload result."""
        self._log_call("upload_file", name=name, mime_type=mime_type, folder_id=folder_id)
        return self._success_response(
            data={"id": "stub-upload-1", "name": name, "uploaded": True},
            message="Google Drive file upload (stubbed)",
        )

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> StubResponse:
        """Return stub folder creation result."""
        self._log_call("create_folder", name=name, parent_id=parent_id)
        return self._success_response(
            data={"id": "stub-folder-1", "name": name},
            message="Google Drive folder creation (stubbed)",
        )

    def drive_stubbed(self) -> bool:
        """Return True to indicate stub mode."""
        return True

    def credentials_available(self) -> bool:
        """Return True to indicate credentials are available."""
        return True
