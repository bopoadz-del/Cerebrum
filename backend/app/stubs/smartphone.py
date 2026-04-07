"""
Smartphone Stub

Stub implementation for smartphone storage connector.
Provides mock data for testing without actual phone connection.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseStub, StubResponse, StubError


class SmartphoneStub(BaseStub):
    """
    Stub for Smartphone connector.
    
    Provides mock data for:
    - Phone connection status
    - File listings (photos, videos, documents)
    - Sync operations
    """
    
    service_name = "smartphone"
    version = "1.0.0-stub"
    
    # Mock phone data
    _mock_phone = {
        "name": "Mock Android Phone",
        "model": "Pixel 7 Pro",
        "connection_type": "syncthing",
        "available_space": 64 * 1024 * 1024 * 1024,  # 64 GB
        "total_space": 128 * 1024 * 1024 * 1024,  # 128 GB
    }
    
    # Mock photos
    _mock_photos = [
        {"name": "IMG_20240101_120000.jpg", "album": "Camera", "size": 3500000, "path": "DCIM/Camera/IMG_20240101_120000.jpg"},
        {"name": "IMG_20240102_143022.jpg", "album": "Camera", "size": 4200000, "path": "DCIM/Camera/IMG_20240102_143022.jpg"},
        {"name": "IMG_20240103_091500.jpg", "album": "Camera", "size": 3800000, "path": "DCIM/Camera/IMG_20240103_091500.jpg"},
        {"name": "screenshot_2024.png", "album": "Screenshots", "size": 2100000, "path": "Pictures/Screenshots/screenshot_2024.png"},
        {"name": "site_visit.jpg", "album": "Construction", "size": 5100000, "path": "Pictures/Construction/site_visit.jpg"},
    ]
    
    # Mock documents
    _mock_documents = [
        {"name": "contract_draft.pdf", "size": 1250000, "path": "Documents/contract_draft.pdf"},
        {"name": "invoice_001.pdf", "size": 85000, "path": "Documents/invoices/invoice_001.pdf"},
        {"name": "meeting_notes.txt", "size": 3500, "path": "Documents/notes/meeting_notes.txt"},
        {"name": "project_timeline.xlsx", "size": 45000, "path": "Documents/project_timeline.xlsx"},
    ]
    
    # Mock music
    _mock_music = [
        {"name": "work_playlist_01.mp3", "size": 8500000, "path": "Music/work_playlist_01.mp3"},
        {"name": "focus_beats.mp3", "size": 9200000, "path": "Music/focus_beats.mp3"},
    ]
    
    def __init__(self):
        super().__init__()
        self._connected = True
        self._sync_path = "/mock/phone_sync"
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "connected": self._connected,
            "path": self._sync_path,
            "phone": self._mock_phone,
            "capabilities": [
                "list_files",
                "list_photos",
                "read_file",
                "write_file",
                "delete_file",
                "sync_from_phone",
                "sync_to_phone",
            ],
            "supported_modes": ["usb", "mtp", "syncthing", "folder"],
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Return stub health status."""
        return {
            "service": self.service_name,
            "status": "connected (stub)" if self._connected else "disconnected (stub)",
            "healthy": self._connected,
            "version": self.version,
            "mode": self._mock_phone["connection_type"],
            "path": self._sync_path,
            "phone": self._mock_phone,
            "calls": self._call_count,
            "last_called": self._last_called,
        }
    
    def is_available(self) -> bool:
        """Stub phone is always available."""
        return self._connected
    
    def is_connected(self) -> bool:
        """Check if stub phone is connected."""
        return self._connected
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed stub status."""
        return {
            "service": self.service_name,
            "mode": "stub",
            "available": self._connected,
            "path": self._sync_path,
            "phone": self._mock_phone,
            "calls": self._call_count,
            "last_called": self._last_called,
            "version": self.version,
        }
    
    def list_files(self, path: str = ".", file_type: Optional[str] = None) -> StubResponse:
        """Get mock file listing."""
        self._log_call("list_files", path=path, file_type=file_type)
        
        if not self._connected:
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        files = []
        
        # Return appropriate mock data based on type
        if file_type == "photos" or path == "DCIM" or path == "Pictures":
            files = [
                {
                    "name": p["name"],
                    "path": p["path"],
                    "size": p["size"],
                    "modified": datetime.now().isoformat(),
                    "mime_type": "image/jpeg" if p["name"].endswith(".jpg") else "image/png",
                }
                for p in self._mock_photos[:3]
            ]
        elif file_type == "documents":
            files = [
                {
                    "name": d["name"],
                    "path": d["path"],
                    "size": d["size"],
                    "modified": datetime.now().isoformat(),
                    "mime_type": "application/pdf" if d["name"].endswith(".pdf") else "text/plain",
                }
                for d in self._mock_documents[:2]
            ]
        elif file_type == "music":
            files = [
                {
                    "name": m["name"],
                    "path": m["path"],
                    "size": m["size"],
                    "modified": datetime.now().isoformat(),
                    "mime_type": "audio/mpeg",
                }
                for m in self._mock_music
            ]
        else:
            # Mixed files
            files = [
                {
                    "name": "IMG_20240101_120000.jpg",
                    "path": "DCIM/Camera/IMG_20240101_120000.jpg",
                    "size": 3500000,
                    "modified": datetime.now().isoformat(),
                    "mime_type": "image/jpeg",
                },
                {
                    "name": "contract_draft.pdf",
                    "path": "Documents/contract_draft.pdf",
                    "size": 1250000,
                    "modified": datetime.now().isoformat(),
                    "mime_type": "application/pdf",
                },
            ]
        
        return self._success_response(
            data={
                "path": path,
                "files": files,
                "count": len(files),
                "phone_name": self._mock_phone["name"],
            },
            message=f"Listed {len(files)} files (stub)",
        )
    
    def list_photos(self, album: Optional[str] = None) -> StubResponse:
        """Get mock photos."""
        self._log_call("list_photos", album=album)
        
        if not self._connected:
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        photos = self._mock_photos
        
        if album and album != "all":
            photos = [p for p in photos if p["album"].lower() == album.lower()]
        
        photos_data = [
            {
                "name": p["name"],
                "path": p["path"],
                "album": p["album"],
                "size": p["size"],
                "modified": datetime.now().isoformat(),
            }
            for p in photos
        ]
        
        return self._success_response(
            data={
                "photos": photos_data,
                "count": len(photos_data),
                "album": album or "all",
            },
            message=f"Found {len(photos_data)} photos (stub)",
        )
    
    def read_file(self, path: str) -> StubResponse:
        """Read mock file from phone."""
        self._log_call("read_file", path=path)
        
        if not self._connected:
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        # Find file in mock data
        for photo in self._mock_photos:
            if photo["path"] == path:
                return self._success_response(
                    data={
                        "path": path,
                        "content": "[base64 image data - stub]",
                        "content_type": "base64",
                        "mime_type": "image/jpeg",
                        "size": photo["size"],
                    },
                    message="File read successfully (stub)",
                )
        
        for doc in self._mock_documents:
            if doc["path"] == path:
                return self._success_response(
                    data={
                        "path": path,
                        "content": "[base64 document data - stub]",
                        "content_type": "base64",
                        "mime_type": "application/pdf" if path.endswith(".pdf") else "text/plain",
                        "size": doc["size"],
                    },
                    message="File read successfully (stub)",
                )
        
        return StubError(error=f"File not found: {path}", code="NOT_FOUND")
    
    def write_file(self, path: str, content: str, 
                   content_type: str = "base64") -> StubResponse:
        """Mock write file to phone."""
        self._log_call("write_file", path=path, content_type=content_type)
        
        if not self._connected:
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        return self._success_response(
            data={
                "path": path,
                "size": len(content) if content_type == "text" else len(content) * 3 // 4,
                "written": True,
            },
            message=f"File written to phone: {path} (stub - no actual write)",
        )
    
    def delete_file(self, path: str) -> StubResponse:
        """Mock delete file from phone."""
        self._log_call("delete_file", path=path)
        
        if not self._connected:
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        return self._success_response(
            data={"path": path, "deleted": True},
            message=f"Deleted from phone: {path} (stub)",
        )
    
    def sync_to_phone(self, local_path: str, phone_path: str) -> StubResponse:
        """Mock sync to phone."""
        self._log_call("sync_to_phone", local_path=local_path, phone_path=phone_path)
        
        if not self._connected:
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        return self._success_response(
            data={"local_path": local_path, "phone_path": phone_path},
            message="Synced to phone (stub)",
        )
    
    def sync_from_phone(self, phone_path: str, local_path: str) -> StubResponse:
        """Mock sync from phone."""
        self._log_call("sync_from_phone", phone_path=phone_path, local_path=local_path)
        
        if not self._connected:
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        return self._success_response(
            data={"phone_path": phone_path, "local_path": local_path},
            message="Synced from phone (stub)",
        )
