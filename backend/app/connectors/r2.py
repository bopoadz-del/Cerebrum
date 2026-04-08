"""
Cloudflare R2 Connector

Production connector for Cloudflare R2 object storage.
R2 is S3-compatible API using boto3.

Environment Variables:
    R2_ACCESS_KEY_ID: R2 access key ID
    R2_SECRET_ACCESS_KEY: R2 secret access key
    R2_ACCOUNT_ID: Cloudflare account ID
    R2_BUCKET_NAME: Default bucket name (optional)
"""

import os
import logging
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.stubs.base import StubResponse, StubError

logger = logging.getLogger(__name__)


@dataclass
class R2Object:
    """R2 object metadata."""
    key: str
    size: int
    last_modified: datetime
    etag: str
    content_type: Optional[str] = None


class R2Connector:
    """
    Cloudflare R2 object storage connector.
    
    Provides:
    - File upload/download
    - Object listing
    - Object deletion
    - Presigned URL generation
    
    Uses boto3 with R2's S3-compatible API.
    """
    
    service_name = "r2"
    version = "1.0.0"
    
    def __init__(self, 
                 access_key_id: Optional[str] = None,
                 secret_access_key: Optional[str] = None,
                 account_id: Optional[str] = None,
                 default_bucket: Optional[str] = None):
        """
        Initialize R2 connector.
        
        Args:
            access_key_id: R2 access key ID (or R2_ACCESS_KEY_ID env var)
            secret_access_key: R2 secret access key (or R2_SECRET_ACCESS_KEY env var)
            account_id: Cloudflare account ID (or R2_ACCOUNT_ID env var)
            default_bucket: Default bucket name (or R2_BUCKET_NAME env var)
        """
        self.logger = logging.getLogger(f"connectors.{self.service_name}")
        
        # Get credentials from args or environment
        self.access_key_id = access_key_id or os.getenv("R2_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY")
        self.account_id = account_id or os.getenv("R2_ACCOUNT_ID")
        self.default_bucket = default_bucket or os.getenv("R2_BUCKET_NAME")
        
        if not all([self.access_key_id, self.secret_access_key, self.account_id]):
            raise ValueError(
                "R2 credentials required. Set R2_ACCESS_KEY_ID, "
                "R2_SECRET_ACCESS_KEY, and R2_ACCOUNT_ID environment variables."
            )
        
        # Construct R2 endpoint URL
        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
        
        # Initialize S3 client with R2 configuration
        self._client = None
        self._call_count = 0
        self._last_called = None
    
    def _get_client(self):
        """Get or create boto3 S3 client."""
        if self._client is None:
            config = Config(
                signature_version='s3v4',
                retries={'max_attempts': 3}
            )
            self._client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=config,
                region_name='auto'  # R2 doesn't use regions
            )
        return self._client
    
    def _log_call(self, method: str, **kwargs):
        """Log connector method call."""
        self._call_count += 1
        self._last_called = datetime.utcnow().isoformat()
        self.logger.debug(f"[{self.service_name}.{method}] Call", extra=kwargs)
    
    def _get_bucket(self, bucket: Optional[str]) -> str:
        """Get bucket name, using default if not specified."""
        bucket = bucket or self.default_bucket
        if not bucket:
            raise ValueError("Bucket name required. Provide bucket parameter or set R2_BUCKET_NAME.")
        return bucket
    
    def health_check(self) -> Dict[str, Any]:
        """Check R2 connection health."""
        try:
            client = self._get_client()
            # List buckets to verify connection
            response = client.list_buckets()
            buckets = [b['Name'] for b in response.get('Buckets', [])]
            
            return {
                "service": self.service_name,
                "status": "healthy",
                "healthy": True,
                "version": self.version,
                "endpoint": self.endpoint_url,
                "account_id": self.account_id,
                "buckets": buckets,
                "bucket_count": len(buckets),
                "calls": self._call_count,
                "last_called": self._last_called,
            }
        except ClientError as e:
            return {
                "service": self.service_name,
                "status": "unhealthy",
                "healthy": False,
                "version": self.version,
                "endpoint": self.endpoint_url,
                "error": str(e),
                "error_code": e.response.get('Error', {}).get('Code', 'Unknown'),
            }
    
    def is_available(self) -> bool:
        """Check if R2 connection is available."""
        try:
            health = self.health_check()
            return health.get("healthy", False)
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed connector status."""
        return {
            "service": self.service_name,
            "mode": "production",
            "available": self.is_available(),
            "endpoint": self.endpoint_url,
            "account_id": self.account_id,
            "default_bucket": self.default_bucket,
            "has_credentials": all([
                self.access_key_id,
                self.secret_access_key,
                self.account_id
            ]),
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
    
    def upload_file(self, 
                   file_path: Union[str, Path], 
                   bucket: Optional[str] = None,
                   key: Optional[str] = None,
                   content_type: Optional[str] = None) -> StubResponse:
        """
        Upload a file to R2.
        
        Args:
            file_path: Path to local file
            bucket: Target bucket (uses default if not specified)
            key: Object key in R2 (uses filename if not specified)
            content_type: MIME type (auto-detected if not specified)
            
        Returns:
            StubResponse with upload result
        """
        self._log_call("upload_file", file_path=str(file_path), bucket=bucket, key=key)
        
        file_path = Path(file_path)
        bucket = self._get_bucket(bucket)
        key = key or file_path.name
        
        if not file_path.exists():
            return StubError(error=f"File not found: {file_path}", code="FILE_NOT_FOUND")
        
        try:
            client = self._get_client()
            
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            client.upload_file(
                Filename=str(file_path),
                Bucket=bucket,
                Key=key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            return StubResponse(
                success=True,
                data={
                    "bucket": bucket,
                    "key": key,
                    "file_path": str(file_path),
                    "size": file_path.stat().st_size,
                },
                message=f"File uploaded: {key}",
            )
        except ClientError as e:
            return StubError(
                error=f"Upload failed: {e}",
                code=e.response.get('Error', {}).get('Code', 'UPLOAD_ERROR')
            )
    
    def download_file(self,
                     bucket: Optional[str],
                     key: str,
                     destination: Union[str, Path]) -> StubResponse:
        """
        Download a file from R2.
        
        Args:
            bucket: Source bucket (uses default if not specified)
            key: Object key in R2
            destination: Local path to save file
            
        Returns:
            StubResponse with download result
        """
        self._log_call("download_file", bucket=bucket, key=key, destination=str(destination))
        
        bucket = self._get_bucket(bucket)
        destination = Path(destination)
        
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            client = self._get_client()
            client.download_file(Bucket=bucket, Key=key, Filename=str(destination))
            
            return StubResponse(
                success=True,
                data={
                    "bucket": bucket,
                    "key": key,
                    "destination": str(destination),
                    "size": destination.stat().st_size if destination.exists() else 0,
                },
                message=f"File downloaded: {key}",
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'DOWNLOAD_ERROR')
            if error_code == '404' or 'Not Found' in str(e):
                return StubError(error=f"Object not found: {key}", code="NOT_FOUND")
            return StubError(error=f"Download failed: {e}", code=error_code)
    
    def list_objects(self,
                    bucket: Optional[str] = None,
                    prefix: str = "",
                    max_keys: int = 1000) -> StubResponse:
        """
        List objects in R2 bucket.
        
        Args:
            bucket: Bucket to list (uses default if not specified)
            prefix: Key prefix filter
            max_keys: Maximum number of keys to return
            
        Returns:
            StubResponse with list of objects
        """
        self._log_call("list_objects", bucket=bucket, prefix=prefix, max_keys=max_keys)
        
        bucket = self._get_bucket(bucket)
        
        try:
            client = self._get_client()
            
            kwargs = {
                'Bucket': bucket,
                'MaxKeys': max_keys,
            }
            if prefix:
                kwargs['Prefix'] = prefix
            
            response = client.list_objects_v2(**kwargs)
            
            objects = []
            for obj in response.get('Contents', []):
                objects.append(R2Object(
                    key=obj['Key'],
                    size=obj['Size'],
                    last_modified=obj['LastModified'],
                    etag=obj['ETag'],
                ).__dict__)
            
            return StubResponse(
                success=True,
                data={
                    "bucket": bucket,
                    "prefix": prefix,
                    "objects": objects,
                    "count": len(objects),
                    "is_truncated": response.get('IsTruncated', False),
                },
                message=f"Listed {len(objects)} objects",
            )
        except ClientError as e:
            return StubError(
                error=f"List failed: {e}",
                code=e.response.get('Error', {}).get('Code', 'LIST_ERROR')
            )
    
    def delete_object(self,
                     bucket: Optional[str],
                     key: str) -> StubResponse:
        """
        Delete an object from R2.
        
        Args:
            bucket: Bucket containing object (uses default if not specified)
            key: Object key to delete
            
        Returns:
            StubResponse with deletion result
        """
        self._log_call("delete_object", bucket=bucket, key=key)
        
        bucket = self._get_bucket(bucket)
        
        try:
            client = self._get_client()
            client.delete_object(Bucket=bucket, Key=key)
            
            return StubResponse(
                success=True,
                data={
                    "bucket": bucket,
                    "key": key,
                    "deleted": True,
                },
                message=f"Object deleted: {key}",
            )
        except ClientError as e:
            return StubError(
                error=f"Delete failed: {e}",
                code=e.response.get('Error', {}).get('Code', 'DELETE_ERROR')
            )
    
    def generate_presigned_url(self,
                              bucket: Optional[str],
                              key: str,
                              expiration: int = 3600,
                              operation: str = 'get_object') -> StubResponse:
        """
        Generate a presigned URL for R2 object.
        
        Args:
            bucket: Bucket containing object (uses default if not specified)
            key: Object key
            expiration: URL expiration time in seconds (default: 1 hour)
            operation: S3 operation ('get_object' or 'put_object')
            
        Returns:
            StubResponse with presigned URL
        """
        self._log_call("generate_presigned_url", bucket=bucket, key=key, 
                      expiration=expiration, operation=operation)
        
        bucket = self._get_bucket(bucket)
        
        try:
            client = self._get_client()
            url = client.generate_presigned_url(
                ClientMethod=operation,
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            
            expires_at = datetime.utcnow() + timedelta(seconds=expiration)
            
            return StubResponse(
                success=True,
                data={
                    "bucket": bucket,
                    "key": key,
                    "url": url,
                    "expiration": expiration,
                    "expires_at": expires_at.isoformat(),
                    "operation": operation,
                },
                message="Presigned URL generated",
            )
        except ClientError as e:
            return StubError(
                error=f"URL generation failed: {e}",
                code=e.response.get('Error', {}).get('Code', 'URL_ERROR')
            )
    
    def object_exists(self,
                     bucket: Optional[str],
                     key: str) -> bool:
        """
        Check if an object exists in R2.
        
        Args:
            bucket: Bucket to check (uses default if not specified)
            key: Object key to check
            
        Returns:
            True if object exists, False otherwise
        """
        self._log_call("object_exists", bucket=bucket, key=key)
        
        bucket = self._get_bucket(bucket)
        
        try:
            client = self._get_client()
            client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
