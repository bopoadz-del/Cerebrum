"""
Smartphone Drive Connector

Production connector for smartphone storage access.
Supports multiple connection modes:
- USB Mass Storage (when phone mounted as disk)
- MTP (Media Transfer Protocol) via mtp-tools
- Syncthing (sync app with local folder)
- Folder sync (Dropbox, etc. mounted as local folder)
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime
import mimetypes

from app.stubs.base import StubResponse, StubError

logger = logging.getLogger(__name__)


@dataclass
class PhoneInfo:
    """Connected phone information."""
    name: str
    model: str
    connection_type: str  # usb, mtp, syncthing, folder_sync
    available_space: int
    total_space: int
    is_connected: bool


class SmartphoneConnector:
    """
    Smartphone storage connector.
    
    Supports multiple connection methods:
    1. USB Mass Storage - phone mounted as external drive
    2. MTP - Media Transfer Protocol (most Android phones)
    3. Syncthing - Folder sync via Syncthing app
    4. Folder Sync - Any synced folder (Dropbox, OneDrive, etc.)
    
    Configuration:
    - SMARTPHONE_MODE: Connection mode (usb, mtp, syncthing, folder)
    - SMARTPHONE_PATH: Path to phone storage or sync folder
    """
    
    service_name = "smartphone"
    version = "1.0.0"
    
    # Connection modes
    MODE_USB = "usb"
    MODE_MTP = "mtp"
    MODE_SYNCTHING = "syncthing"
    MODE_FOLDER = "folder"
    
    def __init__(self, mode: Optional[str] = None, path: Optional[str] = None):
        """
        Initialize smartphone connector.
        
        Args:
            mode: Connection mode (usb, mtp, syncthing, folder)
            path: Path to phone storage or sync folder
        """
        self.logger = logging.getLogger(f"connectors.{self.service_name}")
        
        # Determine mode from parameter or environment
        self.mode = mode or os.getenv("SMARTPHONE_MODE", self.MODE_FOLDER)
        
        # Determine path from parameter or environment
        if path:
            self.phone_path = Path(path).resolve()
        elif os.getenv("SMARTPHONE_PATH"):
            self.phone_path = Path(os.getenv("SMARTPHONE_PATH")).resolve()
        else:
            # Default paths based on mode
            if self.mode == self.MODE_SYNCTHING:
                self.phone_path = Path.home() / "Syncthing" / "Phone"
            elif self.mode == self.MODE_USB:
                # Common USB mount points
                possible_paths = [
                    "/media/phone",
                    "/media/user/phone",
                    "/mnt/phone",
                    str(Path.home() / "Phone"),
                ]
                self.phone_path = self._find_existing_path(possible_paths)
            elif self.mode == self.MODE_MTP:
                # MTP mount points
                possible_paths = [
                    "/run/user/1000/gvfs",
                    str(Path.home() / "mtp"),
                ]
                self.phone_path = self._find_existing_path(possible_paths)
            else:
                # Default folder sync location
                self.phone_path = Path.home() / "PhoneSync"
        
        self._call_count = 0
        self._last_called = None
        
        # Try to detect phone on initialization
        self._phone_info: Optional[PhoneInfo] = None
        self._detect_phone()
    
    def _find_existing_path(self, paths: List[str]) -> Path:
        """Find first existing path from list, or default to first."""
        for p in paths:
            path = Path(p)
            if path.exists():
                return path
        return Path(paths[0]) if paths else Path.home() / "Phone"
    
    def _detect_phone(self):
        """Attempt to detect connected phone."""
        if not self.phone_path.exists():
            self._phone_info = None
            return
        
        # Try to read device info
        device_info = self._read_device_info()
        
        self._phone_info = PhoneInfo(
            name=device_info.get("name", "Unknown Phone"),
            model=device_info.get("model", "Unknown"),
            connection_type=self.mode,
            available_space=self._get_available_space(),
            total_space=self._get_total_space(),
            is_connected=self._is_connected(),
        )
    
    def _read_device_info(self) -> Dict[str, str]:
        """Read device information from phone storage."""
        info = {}
        
        # Look for device info file
        info_paths = [
            self.phone_path / ".device_info.json",
            self.phone_path / ".sync" / "device_info.json",
            self.phone_path / "DCIM" / ".device_info.json",
        ]
        
        for info_path in info_paths:
            if info_path.exists():
                try:
                    import json
                    with open(info_path) as f:
                        info = json.load(f)
                    break
                except Exception:
                    pass
        
        # Try to detect from folder structure
        if not info:
            if (self.phone_path / "DCIM").exists():
                info["name"] = "Android Phone"
                info["model"] = "Android"
            elif (self.phone_path / "DCIM" / "100APPLE").exists():
                info["name"] = "iPhone"
                info["model"] = "iOS"
        
        return info
    
    def _get_available_space(self) -> int:
        """Get available storage space in bytes."""
        try:
            if self.phone_path.exists():
                stat = os.statvfs(self.phone_path)
                return stat.f_bavail * stat.f_frsize
        except Exception:
            pass
        return 0
    
    def _get_total_space(self) -> int:
        """Get total storage space in bytes."""
        try:
            if self.phone_path.exists():
                stat = os.statvfs(self.phone_path)
                return stat.f_blocks * stat.f_frsize
        except Exception:
            pass
        return 0
    
    def _is_connected(self) -> bool:
        """Check if phone is connected and accessible."""
        if not self.phone_path.exists():
            return False
        
        # Check for typical phone directories
        phone_indicators = [
            "DCIM",
            "Pictures",
            "Download",
            "Documents",
            "Music",
            "Movies",
        ]
        
        for indicator in phone_indicators:
            if (self.phone_path / indicator).exists():
                return True
        
        # If folder exists but no typical directories, still consider connected
        # (might be empty sync folder)
        return True
    
    def _log_call(self, method: str, **kwargs):
        """Log connector method call."""
        self._call_count += 1
        self._last_called = datetime.utcnow().isoformat()
        self.logger.debug(f"[{self.service_name}.{method}] Call", extra=kwargs)
    
    def _validate_path(self, path: str) -> Path:
        """Validate and resolve a path, ensuring it stays within phone storage."""
        if not path.startswith('/'):
            full_path = (self.phone_path / path).resolve()
        else:
            full_path = Path(path).resolve()
        
        # Security: Ensure path is within phone storage
        try:
            full_path.relative_to(self.phone_path)
        except ValueError:
            raise ValueError(
                f"Path traversal attempt: '{path}' resolves outside phone storage"
            )
        
        return full_path
    
    def health_check(self) -> Dict[str, Any]:
        """Return connector health status."""
        self._detect_phone()
        
        return {
            "service": self.service_name,
            "status": "connected" if self.is_connected() else "disconnected",
            "healthy": self.is_connected(),
            "version": self.version,
            "mode": self.mode,
            "path": str(self.phone_path),
            "phone": self._phone_info.__dict__ if self._phone_info else None,
            "calls": self._call_count,
            "last_called": self._last_called,
        }
    
    def is_available(self) -> bool:
        """Check if phone is available."""
        self._detect_phone()
        return self._phone_info is not None and self._phone_info.is_connected
    
    def is_connected(self) -> bool:
        """Alias for is_available."""
        return self.is_available()
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed connector status."""
        self._detect_phone()
        
        return {
            "service": self.service_name,
            "mode": self.mode,
            "available": self.is_available(),
            "path": str(self.phone_path),
            "phone": self._phone_info.__dict__ if self._phone_info else None,
            "calls": self._call_count,
            "last_called": self._last_called,
            "version": self.version,
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Return connector information."""
        self._detect_phone()
        
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": self.mode,
            "path": str(self.phone_path),
            "connected": self.is_connected(),
            "phone": self._phone_info.__dict__ if self._phone_info else None,
            "capabilities": [
                "list_files",
                "list_photos",
                "read_file",
                "write_file",
                "delete_file",
                "sync_from_phone",
                "sync_to_phone",
            ],
            "supported_modes": [
                self.MODE_USB,
                self.MODE_MTP,
                self.MODE_SYNCTHING,
                self.MODE_FOLDER,
            ],
        }
    
    def list_files(self, path: str = ".", file_type: Optional[str] = None) -> StubResponse:
        """
        List files on phone storage.
        
        Args:
            path: Directory path (relative to phone root)
            file_type: Filter by type (photos, videos, music, documents, all)
            
        Returns:
            StubResponse with file list
        """
        self._log_call("list_files", path=path, file_type=file_type)
        
        if not self.is_connected():
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        try:
            # Map file types to common phone directories
            if file_type:
                path = self._get_type_path(file_type) or path
            
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return StubError(error=f"Path not found: {path}", code="NOT_FOUND")
            
            files = []
            for item in full_path.iterdir():
                if item.is_file():
                    stat = item.stat()
                    mime_type, _ = mimetypes.guess_type(str(item))
                    files.append({
                        "name": item.name,
                        "path": str(item.relative_to(self.phone_path)),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "mime_type": mime_type,
                    })
            
            files.sort(key=lambda x: x["name"].lower())
            
            return StubResponse(
                success=True,
                data={
                    "path": path,
                    "files": files,
                    "count": len(files),
                    "phone_name": self._phone_info.name if self._phone_info else "Unknown",
                },
                message=f"Listed {len(files)} files",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="LIST_ERROR")
    
    def list_photos(self, album: Optional[str] = None) -> StubResponse:
        """
        List photos from phone.
        
        Args:
            album: Specific album/folder name, or None for all photos
            
        Returns:
            StubResponse with photo list
        """
        self._log_call("list_photos", album=album)
        
        if not self.is_connected():
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        try:
            # Common photo directories
            photo_paths = [
                self.phone_path / "DCIM" / "Camera",
                self.phone_path / "DCIM",
                self.phone_path / "Pictures",
                self.phone_path / "Photos",
            ]
            
            if album:
                # Look for specific album
                album_paths = [
                    self.phone_path / "DCIM" / album,
                    self.phone_path / "Pictures" / album,
                    self.phone_path / "Photos" / album,
                ]
                photo_paths = album_paths + photo_paths
            
            photos = []
            photo_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.raw'}
            
            for photo_path in photo_paths:
                if photo_path.exists():
                    for item in photo_path.rglob("*"):
                        if item.is_file() and item.suffix.lower() in photo_extensions:
                            stat = item.stat()
                            photos.append({
                                "name": item.name,
                                "path": str(item.relative_to(self.phone_path)),
                                "album": photo_path.name,
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            })
            
            # Remove duplicates by path
            seen = set()
            unique_photos = []
            for p in photos:
                if p["path"] not in seen:
                    seen.add(p["path"])
                    unique_photos.append(p)
            
            unique_photos.sort(key=lambda x: x["modified"], reverse=True)
            
            return StubResponse(
                success=True,
                data={
                    "photos": unique_photos,
                    "count": len(unique_photos),
                    "album": album or "all",
                },
                message=f"Found {len(unique_photos)} photos",
            )
            
        except Exception as e:
            return StubError(error=str(e), code="LIST_ERROR")
    
    def read_file(self, path: str) -> StubResponse:
        """
        Read file from phone.
        
        Args:
            path: File path on phone
            
        Returns:
            StubResponse with file content (base64 encoded for binary)
        """
        self._log_call("read_file", path=path)
        
        if not self.is_connected():
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return StubError(error=f"File not found: {path}", code="NOT_FOUND")
            
            if full_path.is_dir():
                return StubError(error=f"Path is a directory: {path}", code="IS_DIRECTORY")
            
            # Read as binary and encode as base64
            import base64
            content = base64.b64encode(full_path.read_bytes()).decode('ascii')
            mime_type, _ = mimetypes.guess_type(str(full_path))
            
            return StubResponse(
                success=True,
                data={
                    "path": path,
                    "content": content,
                    "content_type": "base64",
                    "mime_type": mime_type,
                    "size": full_path.stat().st_size,
                },
                message="File read successfully",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="READ_ERROR")
    
    def write_file(self, path: str, content: str, 
                   content_type: str = "base64") -> StubResponse:
        """
        Write file to phone.
        
        Args:
            path: Destination path on phone
            content: File content (base64 encoded)
            content_type: "base64" or "text"
            
        Returns:
            StubResponse with write result
        """
        self._log_call("write_file", path=path, content_type=content_type)
        
        if not self.is_connected():
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        try:
            full_path = self._validate_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
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
                message=f"File written to phone: {path}",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="WRITE_ERROR")
    
    def delete_file(self, path: str) -> StubResponse:
        """
        Delete file from phone.
        
        Args:
            path: File path to delete
            
        Returns:
            StubResponse with deletion result
        """
        self._log_call("delete_file", path=path)
        
        if not self.is_connected():
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return StubError(error=f"File not found: {path}", code="NOT_FOUND")
            
            if full_path.is_dir():
                import shutil
                shutil.rmtree(full_path)
            else:
                full_path.unlink()
            
            return StubResponse(
                success=True,
                data={"path": path, "deleted": True},
                message=f"Deleted from phone: {path}",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="DELETE_ERROR")
    
    def sync_to_phone(self, local_path: str, phone_path: str) -> StubResponse:
        """
        Sync file from local to phone.
        
        Args:
            local_path: Source path on local filesystem
            phone_path: Destination path on phone
            
        Returns:
            StubResponse with sync result
        """
        self._log_call("sync_to_phone", local_path=local_path, phone_path=phone_path)
        
        if not self.is_connected():
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        try:
            import shutil
            src = Path(local_path)
            dst = self._validate_path(phone_path)
            
            if not src.exists():
                return StubError(error=f"Source not found: {local_path}", code="NOT_FOUND")
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            
            return StubResponse(
                success=True,
                data={"local_path": local_path, "phone_path": phone_path},
                message="Synced to phone",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="SYNC_ERROR")
    
    def sync_from_phone(self, phone_path: str, local_path: str) -> StubResponse:
        """
        Sync file from phone to local.
        
        Args:
            phone_path: Source path on phone
            local_path: Destination path on local filesystem
            
        Returns:
            StubResponse with sync result
        """
        self._log_call("sync_from_phone", phone_path=phone_path, local_path=local_path)
        
        if not self.is_connected():
            return StubError(error="Phone not connected", code="NOT_CONNECTED")
        
        try:
            import shutil
            src = self._validate_path(phone_path)
            dst = Path(local_path)
            
            if not src.exists():
                return StubError(error=f"Source not found: {phone_path}", code="NOT_FOUND")
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            
            return StubResponse(
                success=True,
                data={"phone_path": phone_path, "local_path": local_path},
                message="Synced from phone",
            )
            
        except ValueError as e:
            return StubError(error=str(e), code="INVALID_PATH")
        except Exception as e:
            return StubError(error=str(e), code="SYNC_ERROR")
    
    def _get_type_path(self, file_type: str) -> Optional[str]:
        """Map file type to common directory paths."""
        type_map = {
            "photos": "DCIM/Camera",
            "videos": "Movies",
            "music": "Music",
            "documents": "Documents",
            "downloads": "Download",
            "all": ".",
        }
        return type_map.get(file_type.lower())
    
    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
