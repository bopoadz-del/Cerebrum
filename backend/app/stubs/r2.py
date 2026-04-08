"""
Cloudflare R2 Stub

Stub implementation for R2 object storage connector.
Provides mock data for testing without actual R2 access.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .base import BaseStub, StubResponse, StubError


class R2Stub(BaseStub):
    """
    Stub for Cloudflare R2 connector.
    
    Provides mock data for:
    - File uploads/downloads
    - Object listings
    - Object deletions
    - Presigned URL generation
    """
    
    service_name = "r2"
    version = "1.0.0-stub"
    
    # Mock storage structure
    _mock_objects = {
        "my-bucket": {
            "documents/report.pdf": {
                "size": 2048000,
                "content_type": "application/pdf",
                "etag": '"mock-etag-001"',
            },
            "documents/notes.txt": {
                "size": 2500,
                "content_type": "text/plain",
                "etag": '"mock-etag-002"',
                "content": "Meeting notes\n\nDate: 2024-01-15\nAttendees: John, Sarah",
            },
            "images/photo1.jpg": {
                "size": 3500000,
                "content_type": "image/jpeg",
                "etag": '"mock-etag-003"',
            },
            "images/photo2.png": {
                "size": 4200000,
                "content_type": "image/png",
                "etag": '"mock-etag-004"',
            },
            "data/export.csv": {
                "size": 15000,
                "content_type": "text/csv",
                "etag": '"mock-etag-005"',
            },
        },
        "archive": {
            "backup-2024-01.zip": {
                "size": 104857600,
                "content_type": "application/zip",
                "etag": '"mock-etag-archive-001"',
            },
        }
    }
    
    def __init__(self, 
                 access_key_id: Optional[str] = None,
                 secret_access_key: Optional[str] = None,
                 account_id: Optional[str] = None,
                 default_bucket: Optional[str] = None):
        super().__init__()
        self.access_key_id = access_key_id or "mock-access-key"
        self.secret_access_key = secret_access_key or "mock-secret-key"
        self.account_id = account_id or "mock-account-id"
        self.default_bucket = default_bucket or "my-bucket"
        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
        
        # Track uploaded files
        self._uploaded_files: List[Dict[str, Any]] = []
        self._deleted_keys: List[str] = []
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "endpoint": self.endpoint_url,
            "account_id": self.account_id,
            "default_bucket": self.default_bucket,
            "capabilities": [
                "upload_file",
                "download_file",
                "list_objects",
                "delete_object",
                "generate_presigned_url",
            ],
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Return stub health status."""
        return {
            "service": self.service_name,
            "status": "healthy (stub)",
            "healthy": True,
            "version": self.version,
            "endpoint": self.endpoint_url,
            "account_id": self.account_id,
            "buckets": list(self._mock_objects.keys()),
            "bucket_count": len(self._mock_objects),
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
            "endpoint": self.endpoint_url,
            "account_id": self.account_id,
            "default_bucket": self.default_bucket,
            "has_credentials": True,
            "calls": self._call_count,
            "last_called": self._last_called,
            "version": self.version,
        }
    
    def _get_bucket(self, bucket: Optional[str]) -> str:
        """Get bucket name, using default if not specified."""
        bucket = bucket or self.default_bucket
        if not bucket:
            raise ValueError("Bucket name required")
        return bucket
    
    def upload_file(self, 
                   file_path: Any,
                   bucket: Optional[str] = None,
                   key: Optional[str] = None,
                   content_type: Optional[str] = None) -> StubResponse:
        """Mock upload a file to R2."""
        self._log_call("upload_file", file_path=str(file_path), bucket=bucket, key=key)
        
        file_path = Path(file_path) if not isinstance(file_path, Path) else file_path
        bucket = self._get_bucket(bucket)
        key = key or file_path.name
        
        # Mock size based on filename length
        mock_size = len(key) * 1000 + 500
        
        self._uploaded_files.append({
            "bucket": bucket,
            "key": key,
            "file_path": str(file_path),
            "size": mock_size,
        })
        
        return self._success_response(
            data={
                "bucket": bucket,
                "key": key,
                "file_path": str(file_path),
                "size": mock_size,
            },
            message=f"File uploaded: {key} (stub)",
        )
    
    def download_file(self,
                     bucket: Optional[str],
                     key: str,
                     destination: Any) -> StubResponse:
        """Mock download a file from R2."""
        self._log_call("download_file", bucket=bucket, key=key, destination=str(destination))
        
        bucket = self._get_bucket(bucket)
        destination = Path(destination) if not isinstance(destination, Path) else destination
        
        # Check if object exists in mock data
        bucket_data = self._mock_objects.get(bucket, {})
        if key not in bucket_data:
            return StubError(error=f"Object not found: {key}", code="NOT_FOUND")
        
        obj_info = bucket_data[key]
        
        return self._success_response(
            data={
                "bucket": bucket,
                "key": key,
                "destination": str(destination),
                "size": obj_info["size"],
            },
            message=f"File downloaded: {key} (stub)",
        )
    
    def list_objects(self,
                    bucket: Optional[str] = None,
                    prefix: str = "",
                    max_keys: int = 1000) -> StubResponse:
        """Mock list objects in R2 bucket."""
        self._log_call("list_objects", bucket=bucket, prefix=prefix, max_keys=max_keys)
        
        bucket = self._get_bucket(bucket)
        bucket_data = self._mock_objects.get(bucket, {})
        
        objects = []
        for obj_key, obj_info in bucket_data.items():
            if prefix and not obj_key.startswith(prefix):
                continue
            
            objects.append({
                "key": obj_key,
                "size": obj_info["size"],
                "last_modified": datetime.now().isoformat(),
                "etag": obj_info["etag"],
            })
            
            if len(objects) >= max_keys:
                break
        
        return self._success_response(
            data={
                "bucket": bucket,
                "prefix": prefix,
                "objects": objects,
                "count": len(objects),
                "is_truncated": False,
            },
            message=f"Listed {len(objects)} objects (stub)",
        )
    
    def delete_object(self,
                     bucket: Optional[str],
                     key: str) -> StubResponse:
        """Mock delete an object from R2."""
        self._log_call("delete_object", bucket=bucket, key=key)
        
        bucket = self._get_bucket(bucket)
        self._deleted_keys.append(f"{bucket}/{key}")
        
        return self._success_response(
            data={
                "bucket": bucket,
                "key": key,
                "deleted": True,
            },
            message=f"Object deleted: {key} (stub)",
        )
    
    def generate_presigned_url(self,
                              bucket: Optional[str],
                              key: str,
                              expiration: int = 3600,
                              operation: str = 'get_object') -> StubResponse:
        """Mock generate a presigned URL for R2 object."""
        self._log_call("generate_presigned_url", bucket=bucket, key=key, 
                      expiration=expiration, operation=operation)
        
        bucket = self._get_bucket(bucket)
        
        # Generate a mock presigned URL
        url = f"{self.endpoint_url}/{bucket}/{key}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=mock"
        
        expires_at = datetime.utcnow() + timedelta(seconds=expiration)
        
        return self._success_response(
            data={
                "bucket": bucket,
                "key": key,
                "url": url,
                "expiration": expiration,
                "expires_at": expires_at.isoformat(),
                "operation": operation,
            },
            message="Presigned URL generated (stub)",
        )
    
    def object_exists(self,
                     bucket: Optional[str],
                     key: str) -> bool:
        """Mock check if an object exists in R2."""
        self._log_call("object_exists", bucket=bucket, key=key)
        
        bucket = self._get_bucket(bucket)
        bucket_data = self._mock_objects.get(bucket, {})
        
        return key in bucket_data
