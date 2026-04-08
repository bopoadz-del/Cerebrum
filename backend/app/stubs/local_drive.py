"""
Local Drive Stub

Stub implementation for local filesystem connector.
Provides mock data for testing without actual filesystem access.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from .base import BaseStub, StubResponse, StubError


class LocalDriveStub(BaseStub):
    """
    Stub for Local Drive connector.
    
    Provides mock data for:
    - File listings
    - File contents
    - Directory structures
    """
    
    service_name = "local_drive"
    version = "1.0.0-stub"
    
    # Mock file system structure
    _mock_files = {
        "documents": {
            "project_plan.pdf": {"size": 2048000, "type": "application/pdf"},
            "budget.xlsx": {"size": 45000, "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            "meeting_notes.txt": {"size": 2500, "type": "text/plain", "content": "Meeting Notes\n\nDate: 2024-01-15\nAttendees: John, Sarah, Mike\n\n1. Project timeline approved\n2. Budget increased by 10%\n3. Next meeting: Feb 1"},
            "report.docx": {"size": 125000, "type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        },
        "images": {
            "site_photo_01.jpg": {"size": 3500000, "type": "image/jpeg"},
            "site_photo_02.jpg": {"size": 4200000, "type": "image/jpeg"},
            "blueprint.png": {"size": 8900000, "type": "image/png"},
        },
        "data": {
            "measurements.csv": {"size": 15000, "type": "text/csv", "content": "date,measurement,unit\n2024-01-01,12.5,m\n2024-01-02,13.2,m\n2024-01-03,11.8,m"},
            "config.json": {"size": 800, "type": "application/json", "content": '{"project": "Downtown Tower", "version": "2.0", "settings": {"auto_save": true}}'},
        }
    }
    
    def __init__(self):
        super().__init__()
        self._root_path = "/mock/local_drive"
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "root_path": self._root_path,
            "capabilities": [
                "list_files",
                "read_file",
                "write_file",
                "create_directory",
                "delete",
                "get_file_info",
            ],
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Return stub health status."""
        return {
            "service": self.service_name,
            "status": "healthy (stub)",
            "healthy": True,
            "version": self.version,
            "root_path": self._root_path,
            "root_exists": True,
            "root_writable": True,
            "calls": self._call_count,
            "last_called": self._last_called,
        }
    
    def is_available(self) -> bool:
        """Stub is always available."""
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed stub status."""
        return {
            "service": self.service_name,
            "mode": "stub",
            "available": True,
            "root_path": self._root_path,
            "calls": self._call_count,
            "last_called": self._last_called,
            "version": self.version,
        }
    
    def list_files(self, path: str = ".", recursive: bool = False) -> StubResponse:
        """Get mock file listing."""
        self._log_call("list_files", path=path, recursive=recursive)
        
        files = []
        
        if path == "." or path == "":
            # List root directories
            for dir_name in self._mock_files.keys():
                files.append({
                    "name": dir_name,
                    "path": dir_name,
                    "is_dir": True,
                    "size": 0,
                    "size_human": "0 B",
                    "modified": datetime.now().isoformat(),
                    "created": datetime.now().isoformat(),
                    "mime_type": None,
                    "hash": None,
                })
        elif path in self._mock_files:
            # List files in directory
            dir_files = self._mock_files[path]
            for name, info in dir_files.items():
                files.append({
                    "name": name,
                    "path": f"{path}/{name}",
                    "is_dir": False,
                    "size": info["size"],
                    "size_human": self._human_readable_size(info["size"]),
                    "modified": datetime.now().isoformat(),
                    "created": datetime.now().isoformat(),
                    "mime_type": info.get("type"),
                    "hash": f"mock_hash_{name}",
                })
        
        if recursive and path in [".", ""]:
            for dir_name, dir_files in self._mock_files.items():
                for name, info in dir_files.items():
                    files.append({
                        "name": name,
                        "path": f"{dir_name}/{name}",
                        "is_dir": False,
                        "size": info["size"],
                        "size_human": self._human_readable_size(info["size"]),
                        "modified": datetime.now().isoformat(),
                        "created": datetime.now().isoformat(),
                        "mime_type": info.get("type"),
                        "hash": f"mock_hash_{name}",
                    })
        
        return self._success_response(
            data={
                "path": path,
                "files": files,
                "count": len(files),
            },
            message=f"Listed {len(files)} items (stub)",
        )
    
    def get_file_info(self, path: str) -> StubResponse:
        """Get mock file info."""
        self._log_call("get_file_info", path=path)
        
        # Parse path
        parts = path.split("/")
        if len(parts) == 2 and parts[0] in self._mock_files:
            dir_name, file_name = parts
            if file_name in self._mock_files[dir_name]:
                info = self._mock_files[dir_name][file_name]
                return self._success_response(
                    data={
                        "name": file_name,
                        "path": path,
                        "is_dir": False,
                        "size": info["size"],
                        "size_human": self._human_readable_size(info["size"]),
                        "modified": datetime.now().isoformat(),
                        "created": datetime.now().isoformat(),
                        "mime_type": info.get("type"),
                        "hash": f"mock_hash_{file_name}",
                    },
                    message="File info retrieved (stub)",
                )
        
        return StubError(error=f"File not found: {path}", code="NOT_FOUND")
    
    def read_file(self, path: str, as_text: bool = True) -> StubResponse:
        """Read mock file content."""
        self._log_call("read_file", path=path, as_text=as_text)
        
        # Parse path
        parts = path.split("/")
        if len(parts) == 2 and parts[0] in self._mock_files:
            dir_name, file_name = parts
            if file_name in self._mock_files[dir_name]:
                info = self._mock_files[dir_name][file_name]
                content = info.get("content", f"[Mock content for {file_name}]")
                
                return self._success_response(
                    data={
                        "path": path,
                        "content": content if as_text else "[base64 mock content]",
                        "content_type": "text" if as_text else "base64",
                        "size": info["size"],
                        "name": file_name,
                    },
                    message="File read successfully (stub)",
                )
        
        return StubError(error=f"File not found: {path}", code="NOT_FOUND")
    
    def write_file(self, path: str, content: str, 
                   content_type: str = "text") -> StubResponse:
        """Mock write file."""
        self._log_call("write_file", path=path, content_type=content_type)
        
        return self._success_response(
            data={
                "path": path,
                "size": len(content),
                "written": True,
            },
            message=f"File written: {path} (stub - no actual write)",
        )
    
    def create_directory(self, path: str) -> StubResponse:
        """Mock create directory."""
        self._log_call("create_directory", path=path)
        
        return self._success_response(
            data={"path": path, "created": True},
            message=f"Directory created: {path} (stub)",
        )
    
    def delete(self, path: str, recursive: bool = False) -> StubResponse:
        """Mock delete."""
        self._log_call("delete", path=path, recursive=recursive)
        
        return self._success_response(
            data={"path": path, "deleted": True},
            message=f"Deleted: {path} (stub)",
        )
    
    def search_files(self, pattern: str, path: str = ".") -> StubResponse:
        """Mock file search."""
        self._log_call("search_files", pattern=pattern, path=path)
        
        # Simple pattern matching
        matches = []
        for dir_name, dir_files in self._mock_files.items():
            for file_name in dir_files.keys():
                if pattern.replace("*", "") in file_name:
                    matches.append({
                        "name": file_name,
                        "path": f"{dir_name}/{file_name}",
                        "is_dir": False,
                        "size": dir_files[file_name]["size"],
                        "size_human": self._human_readable_size(dir_files[file_name]["size"]),
                        "modified": datetime.now().isoformat(),
                        "created": datetime.now().isoformat(),
                        "mime_type": dir_files[file_name].get("type"),
                    })
        
        return self._success_response(
            data={
                "pattern": pattern,
                "path": path,
                "files": matches,
                "count": len(matches),
            },
            message=f"Found {len(matches)} matches (stub)",
        )
    
    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
