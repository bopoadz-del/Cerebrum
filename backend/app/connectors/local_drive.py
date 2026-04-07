"""
Local Drive Connector

Production connector for local filesystem access.
Provides read/write operations on local directories with security checks.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime
import mimetypes
import hashlib

from app.stubs.base import StubResponse, StubError

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """File/directory metadata."""
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime
    created: datetime
    mime_type: Optional[str] = None
    hash: Optional[str] = None


class LocalDriveConnector:
    """
    Local filesystem connector.
    
    Provides:
    - File/folder listing
    - File reading
    - File writing
    - Directory creation
    - File deletion
    - File watching (change detection)
    
    Security:
    - Root directory restriction (chroot-like behavior)
    - Path traversal protection
    """
    
    service_name = "local_drive"
    version = "1.0.0"
    
    def __init__(self, root_path: Optional[str] = None):
        """
        Initialize local drive connector.
        
        Args:
            root_path: Root directory for all operations.
                      Defaults to LOCAL_DRIVE_ROOT env var or ./local_drive
        """
        self.logger = logging.getLogger(f"connectors.{self.service_name}")
        
        # Set root path with fallback chain
        if root_path:
            self.root_path = Path(root_path).resolve()
        elif os.getenv("LOCAL_DRIVE_ROOT"):
            self.root_path = Path(os.getenv("LOCAL_DRIVE_ROOT")).resolve()
        else:
            # Default to a 'local_drive' folder in the project
            self.root_path = Path(__file__).parent.parent.parent.parent / "local_drive"
            self.root_path = self.root_path.resolve()
        
        # Ensure root exists
        self.root_path.mkdir(parents=True, exist_ok=True)
        
        # Whitelist of allowed file extensions for reading
        self.allowed_extensions = {
            '.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.css',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
            '.mp3', '.mp4', '.wav', '.avi', '.mov',
            '.zip', '.tar', '.gz', '.rar',
            '.log', '.yml', '.yaml', '.xml', '.sql', '.sh', '.bat'
        }
        
        # Maximum file size (100 MB)
        self.max_file_size = 100 * 1024 * 1024
        
        self._call_count = 0
        self._last_called = None
    
    def _log_call(self, method: str, **kwargs):
        """Log connector method call."""
        self._call_count += 1
        self._last_called = datetime.utcnow().isoformat()
        self.logger.debug(f"[{self.service_name}.{method}] Call", extra=kwargs)
    
    def _validate_path(self, path: str) -> Path:
        """
        Validate and resolve a path, ensuring it stays within root.
        
        Args:
            path: Relative or absolute path
            
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If path attempts traversal outside root
        """
        # Handle relative paths
        if not path.startswith('/'):
            full_path = (self.root_path / path).resolve()
        else:
            # Absolute path - must be within root
            full_path = Path(path).resolve()
        
        # Security: Ensure path is within root
        try:
            full_path.relative_to(self.root_path)
        except ValueError:
            raise ValueError(
                f"Path traversal attempt: '{path}' resolves outside root directory"
            )
        
        return full_path
    
    def health_check(self) -> Dict[str, Any]:
        """Return connector health status."""
        return {
            "service": self.service_name,
            "status": "healthy",
            "healthy": True,
            "version": self.version,
            "root_path": str(self.root_path),
            "root_exists": self.root_path.exists(),
            "root_writable": os.access(self.root_path, os.W_OK),
            "calls": self._call_count,
            "last_called": self._last_called,
        }
    
    def is_available(self) -> bool:
        """Check if local drive is available."""
        return self.root_path.exists() and os.access(self.root_path, os.R_OK)
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed connector status."""
        return {
            "service": self.service_name,
            "mode": "production",
            "available": self.is_available(),
            "root_path": str(self.root_path),
            "calls": self._call_count,
            "last_called": self._last_called,
            "version": self.version,
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Return connector information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "production",
            "root_path": str(self.root_path),
            "capabilities": [
                "list_files",
                "read_file",
                "write_file",
                "create_directory",
                "delete",
                "get_file_info",
            ],
        }
    
    def list_files(self, path: str = ".", recursive: bool = False) -> StubResponse:
        """
        List files and directories.
        
        Args:
            path: Directory path (relative to root)
            recursive: Whether to list recursively
            
        Returns:
            StubResponse with list of FileInfo objects
        """
        self._log_call("list_files", path=path, recursive=recursive)
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return StubError(error=f"Path not found: {path}", code="NOT_FOUND")
            
            if not full_path.is_dir():
                return StubError(error=f"Path is not a directory: {path}", code="NOT_DIRECTORY")
            
            files = []
            
            if recursive:
                for item in full_path.rglob("*"):
                    files.append(self._get_file_info(item))
            else:
                for item in full_path.iterdir():
                    files.append(self._get_file_info(item))
            
            # Sort: directories first, then alphabetically
            files.sort(key=lambda x: (not x.is_dir, x.name.lower()))
            
            return StubResponse(
                success=True,
                data={
                    "path": path,
                    "files": [self._file_info_to_dict(f) for f in files],
                    "count": len(files),
                },
                message=f"Listed {len(files)} items",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            self.logger.error(f"Error listing files: {e}")
            return StubError(error=str(e), code="LIST_ERROR")
    
    def get_file_info(self, path: str) -> StubResponse:
        """
        Get file/directory information.
        
        Args:
            path: File or directory path
            
        Returns:
            StubResponse with FileInfo
        """
        self._log_call("get_file_info", path=path)
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return StubError(error=f"Path not found: {path}", code="NOT_FOUND")
            
            info = self._get_file_info(full_path)
            
            return StubResponse(
                success=True,
                data=self._file_info_to_dict(info),
                message="File info retrieved",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="INFO_ERROR")
    
    def read_file(self, path: str, as_text: bool = True) -> StubResponse:
        """
        Read file contents.
        
        Args:
            path: File path
            as_text: If True, return text content; if False, return base64
            
        Returns:
            StubResponse with file content
        """
        self._log_call("read_file", path=path, as_text=as_text)
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return StubError(error=f"File not found: {path}", code="NOT_FOUND")
            
            if full_path.is_dir():
                return StubError(error=f"Path is a directory: {path}", code="IS_DIRECTORY")
            
            # Check file size
            size = full_path.stat().st_size
            if size > self.max_file_size:
                return StubError(
                    error=f"File too large: {size} bytes (max {self.max_file_size})",
                    code="FILE_TOO_LARGE"
                )
            
            # Check extension
            ext = full_path.suffix.lower()
            if ext and ext not in self.allowed_extensions:
                return StubError(
                    error=f"File type not allowed: {ext}",
                    code="FILE_TYPE_NOT_ALLOWED"
                )
            
            # Read file
            if as_text:
                try:
                    content = full_path.read_text(encoding='utf-8')
                    content_type = "text"
                except UnicodeDecodeError:
                    # Binary file, return base64
                    import base64
                    content = base64.b64encode(full_path.read_bytes()).decode('ascii')
                    content_type = "base64"
            else:
                import base64
                content = base64.b64encode(full_path.read_bytes()).decode('ascii')
                content_type = "base64"
            
            return StubResponse(
                success=True,
                data={
                    "path": path,
                    "content": content,
                    "content_type": content_type,
                    "size": size,
                    "name": full_path.name,
                },
                message="File read successfully",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="READ_ERROR")
    
    def write_file(self, path: str, content: str, 
                   content_type: str = "text") -> StubResponse:
        """
        Write file contents.
        
        Args:
            path: File path
            content: File content
            content_type: "text" or "base64"
            
        Returns:
            StubResponse with write result
        """
        self._log_call("write_file", path=path, content_type=content_type)
        
        try:
            full_path = self._validate_path(path)
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            if content_type == "base64":
                import base64
                full_path.write_bytes(base64.b64decode(content))
            else:
                full_path.write_text(content, encoding='utf-8')
            
            return StubResponse(
                success=True,
                data={
                    "path": path,
                    "size": full_path.stat().st_size,
                    "written": True,
                },
                message=f"File written: {path}",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="WRITE_ERROR")
    
    def create_directory(self, path: str) -> StubResponse:
        """
        Create a directory.
        
        Args:
            path: Directory path
            
        Returns:
            StubResponse with creation result
        """
        self._log_call("create_directory", path=path)
        
        try:
            full_path = self._validate_path(path)
            
            full_path.mkdir(parents=True, exist_ok=True)
            
            return StubResponse(
                success=True,
                data={"path": path, "created": True},
                message=f"Directory created: {path}",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="CREATE_ERROR")
    
    def delete(self, path: str, recursive: bool = False) -> StubResponse:
        """
        Delete a file or directory.
        
        Args:
            path: Path to delete
            recursive: Whether to delete directories recursively
            
        Returns:
            StubResponse with deletion result
        """
        self._log_call("delete", path=path, recursive=recursive)
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return StubError(error=f"Path not found: {path}", code="NOT_FOUND")
            
            if full_path.is_dir():
                if recursive:
                    import shutil
                    shutil.rmtree(full_path)
                else:
                    full_path.rmdir()
            else:
                full_path.unlink()
            
            return StubResponse(
                success=True,
                data={"path": path, "deleted": True},
                message=f"Deleted: {path}",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="DELETE_ERROR")
    
    def search_files(self, pattern: str, path: str = ".") -> StubResponse:
        """
        Search for files matching a pattern.
        
        Args:
            pattern: Glob pattern (e.g., "*.py", "**/test_*.py")
            path: Starting directory
            
        Returns:
            StubResponse with matching files
        """
        self._log_call("search_files", pattern=pattern, path=path)
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return StubError(error=f"Path not found: {path}", code="NOT_FOUND")
            
            matches = list(full_path.rglob(pattern))
            files = [self._get_file_info(m) for m in matches]
            
            return StubResponse(
                success=True,
                data={
                    "pattern": pattern,
                    "path": path,
                    "files": [self._file_info_to_dict(f) for f in files],
                    "count": len(files),
                },
                message=f"Found {len(files)} matches",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="SEARCH_ERROR")
    
    def _get_file_info(self, path: Path) -> FileInfo:
        """Get FileInfo for a path."""
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))
        
        # Calculate hash for small files
        file_hash = None
        if path.is_file() and stat.st_size < 10 * 1024 * 1024:  # < 10MB
            try:
                file_hash = hashlib.md5(path.read_bytes()).hexdigest()
            except Exception:
                pass
        
        return FileInfo(
            name=path.name,
            path=str(path.relative_to(self.root_path)),
            is_dir=path.is_dir(),
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            created=datetime.fromtimestamp(stat.st_ctime),
            mime_type=mime_type,
            hash=file_hash,
        )
    
    def _file_info_to_dict(self, info: FileInfo) -> Dict[str, Any]:
        """Convert FileInfo to dictionary."""
        return {
            "name": info.name,
            "path": info.path,
            "is_dir": info.is_dir,
            "size": info.size,
            "size_human": self._human_readable_size(info.size),
            "modified": info.modified.isoformat(),
            "created": info.created.isoformat(),
            "mime_type": info.mime_type,
            "hash": info.hash,
        }
    
    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
