"""
File Storage Integration Module
Handles Box, Dropbox, Google Drive, and OneDrive integration.
"""
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.database import Base


class FileStorageConnection(Base):
    """File storage connection record."""
    __tablename__ = 'file_storage_connections'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'))
    
    provider = Column(String(50), nullable=False)  # box, dropbox, googledrive, onedrive
    
    account_id = Column(String(255))
    account_email = Column(String(255))
    
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    
    root_folder_id = Column(String(255))
    root_folder_path = Column(String(1000))
    
    is_active = Column(Boolean, default=True)
    connected_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    connected_at = Column(DateTime, default=datetime.utcnow)
    
    last_sync_at = Column(DateTime)
    sync_settings = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models

class FolderCreateRequest(BaseModel):
    name: str
    parent_id: Optional[str] = None
    parent_path: Optional[str] = None


class FileUploadRequest(BaseModel):
    file_name: str
    file_content: bytes
    folder_id: Optional[str] = None
    folder_path: Optional[str] = None
    description: Optional[str] = None


class FileMetadata(BaseModel):
    id: str
    name: str
    type: str  # file, folder
    size: Optional[int] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    download_url: Optional[str] = None
    parent_id: Optional[str] = None


class BoxService:
    """Service for Box integration."""
    
    API_BASE_URL = "https://api.box.com/2.0"
    
    def __init__(self, db_session, client_id: str, client_secret: str):
        self.db = db_session
        self.client_id = client_id
        self.client_secret = client_secret
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_token(self, connection: FileStorageConnection) -> str:
        """Refresh Box access token."""
        url = "https://api.box.com/oauth2/token"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        connection.access_token = token_data["access_token"]
        connection.refresh_token = token_data.get("refresh_token", connection.refresh_token)
        connection.token_expires_at = datetime.utcnow().timestamp() + token_data["expires_in"]
        
        self.db.commit()
        
        return connection.access_token
    
    def _make_request(
        self,
        connection: FileStorageConnection,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Box API."""
        # Check token expiration
        if datetime.utcnow().timestamp() >= connection.token_expires_at:
            access_token = self._refresh_token(connection)
        else:
            access_token = connection.access_token
        
        url = f"{self.API_BASE_URL}{endpoint}"
        headers = self._get_headers(access_token)
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if files:
                response = requests.post(url, headers={"Authorization": headers["Authorization"]}, files=files)
            else:
                response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def create_folder(
        self,
        connection: FileStorageConnection,
        request: FolderCreateRequest
    ) -> FileMetadata:
        """Create a folder in Box."""
        data = {
            "name": request.name,
            "parent": {"id": request.parent_id or "0"}
        }
        
        result = self._make_request(connection, "POST", "/folders", data)
        
        return FileMetadata(
            id=result.get("id"),
            name=result.get("name"),
            type="folder",
            created_at=datetime.fromisoformat(result.get("created_at").replace('Z', '+00:00')),
            modified_at=datetime.fromisoformat(result.get("modified_at").replace('Z', '+00:00')),
            parent_id=result.get("parent", {}).get("id")
        )
    
    def upload_file(
        self,
        connection: FileStorageConnection,
        request: FileUploadRequest
    ) -> FileMetadata:
        """Upload a file to Box."""
        folder_id = request.folder_id or connection.root_folder_id or "0"
        
        files = {
            "file": (request.file_name, request.file_content),
            "attributes": (None, f'{{"name": "{request.file_name}", "parent": {{"id": "{folder_id}"}}}}')
        }
        
        result = self._make_request(connection, "POST", "/files/content", files=files)
        
        entry = result.get("entries", [{}])[0]
        
        return FileMetadata(
            id=entry.get("id"),
            name=entry.get("name"),
            type="file",
            size=entry.get("size"),
            created_at=datetime.fromisoformat(entry.get("created_at").replace('Z', '+00:00')),
            modified_at=datetime.fromisoformat(entry.get("modified_at").replace('Z', '+00:00')),
            parent_id=entry.get("parent", {}).get("id")
        )
    
    def list_folder_contents(
        self,
        connection: FileStorageConnection,
        folder_id: Optional[str] = None
    ) -> List[FileMetadata]:
        """List folder contents."""
        folder_id = folder_id or connection.root_folder_id or "0"
        
        result = self._make_request(connection, "GET", f"/folders/{folder_id}/items")
        
        items = []
        for entry in result.get("entries", []):
            items.append(FileMetadata(
                id=entry.get("id"),
                name=entry.get("name"),
                type=entry.get("type"),
                size=entry.get("size"),
                modified_at=datetime.fromisoformat(entry.get("modified_at").replace('Z', '+00:00')) if entry.get("modified_at") else None
            ))
        
        return items
    
    def get_download_url(
        self,
        connection: FileStorageConnection,
        file_id: str
    ) -> str:
        """Get file download URL."""
        result = self._make_request(connection, "GET", f"/files/{file_id}")
        return result.get("shared_link", {}).get("download_url") or f"{self.API_BASE_URL}/files/{file_id}/content"


class DropboxService:
    """Service for Dropbox integration."""
    
    API_BASE_URL = "https://api.dropboxapi.com/2"
    CONTENT_BASE_URL = "https://content.dropboxapi.com/2"
    
    def __init__(self, db_session, app_key: str, app_secret: str):
        self.db = db_session
        self.app_key = app_key
        self.app_secret = app_secret
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_token(self, connection: FileStorageConnection) -> str:
        """Refresh Dropbox access token."""
        url = "https://api.dropboxapi.com/oauth2/token"
        
        auth = (self.app_key, self.app_secret)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token
        }
        
        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        connection.access_token = token_data["access_token"]
        connection.token_expires_at = datetime.utcnow().timestamp() + token_data["expires_in"]
        
        self.db.commit()
        
        return connection.access_token
    
    def _make_request(
        self,
        connection: FileStorageConnection,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        content_request: bool = False
    ) -> Dict[str, Any]:
        """Make authenticated request to Dropbox API."""
        # Check token expiration
        if datetime.utcnow().timestamp() >= connection.token_expires_at:
            access_token = self._refresh_token(connection)
        else:
            access_token = connection.access_token
        
        base_url = self.CONTENT_BASE_URL if content_request else self.API_BASE_URL
        url = f"{base_url}{endpoint}"
        headers = self._get_headers(access_token)
        
        if method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def create_folder(
        self,
        connection: FileStorageConnection,
        request: FolderCreateRequest
    ) -> FileMetadata:
        """Create a folder in Dropbox."""
        path = f"{request.parent_path or connection.root_folder_path or ''}/{request.name}"
        
        data = {
            "path": path,
            "autorename": False
        }
        
        result = self._make_request(connection, "POST", "/files/create_folder_v2", data)
        
        metadata = result.get("metadata", {})
        
        return FileMetadata(
            id=metadata.get("id"),
            name=metadata.get("name"),
            type="folder",
            modified_at=datetime.strptime(metadata.get("server_modified"), "%Y-%m-%dT%H:%M:%SZ") if metadata.get("server_modified") else None
        )
    
    def upload_file(
        self,
        connection: FileStorageConnection,
        request: FileUploadRequest
    ) -> FileMetadata:
        """Upload a file to Dropbox."""
        path = f"{request.folder_path or connection.root_folder_path or ''}/{request.file_name}"
        
        url = f"{self.CONTENT_BASE_URL}/files/upload"
        headers = {
            "Authorization": f"Bearer {connection.access_token}",
            "Dropbox-API-Arg": f'{{"path": "{path}", "mode": "add", "autorename": true}}',
            "Content-Type": "application/octet-stream"
        }
        
        response = requests.post(url, headers=headers, data=request.file_content)
        response.raise_for_status()
        
        result = response.json()
        
        return FileMetadata(
            id=result.get("id"),
            name=result.get("name"),
            type="file",
            size=result.get("size"),
            modified_at=datetime.strptime(result.get("server_modified"), "%Y-%m-%dT%H:%M:%SZ") if result.get("server_modified") else None
        )


class FileStorageService:
    """Unified file storage service."""
    
    def __init__(self, db_session, box_config: Dict = None, dropbox_config: Dict = None):
        self.db = db_session
        self.box = BoxService(db_session, **box_config) if box_config else None
        self.dropbox = DropboxService(db_session, **dropbox_config) if dropbox_config else None
    
    def get_service(self, provider: str):
        """Get the appropriate file storage service."""
        if provider == "box":
            return self.box
        elif provider == "dropbox":
            return self.dropbox
        else:
            raise ValueError(f"Unsupported file storage provider: {provider}")
