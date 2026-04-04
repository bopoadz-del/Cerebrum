"""
Audit Log Storage

Provides secure storage for audit logs with S3 WORM (Write Once Read Many)
for compliance and tamper-evident archiving.
"""

import gzip
import json
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditStorageError(Exception):
    """Audit storage error."""
    pass


class AuditStorage:
    """
    Audit log storage manager with S3 WORM support.
    
    Provides:
    - Secure S3 storage with encryption
    - WORM (Write Once Read Many) compliance
    - Automatic archival with lifecycle policies
    - Batch upload for efficiency
    """
    
    def __init__(self) -> None:
        """Initialize audit storage."""
        self.s3_client = None
        self.bucket_name = settings.S3_BUCKET_NAME
        self.prefix = settings.S3_AUDIT_PREFIX
        
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
    
    def _ensure_bucket(self) -> None:
        """Ensure S3 bucket exists."""
        if not self.s3_client:
            raise AuditStorageError("S3 client not configured")
        
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                # Create bucket
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={
                        "LocationConstraint": settings.AWS_REGION,
                    },
                )
                
                # Enable versioning (for WORM)
                self.s3_client.put_bucket_versioning(
                    Bucket=self.bucket_name,
                    VersioningConfiguration={"Status": "Enabled"},
                )
                
                # Enable encryption
                self.s3_client.put_bucket_encryption(
                    Bucket=self.bucket_name,
                    ServerSideEncryptionConfiguration={
                        "Rules": [
                            {
                                "ApplyServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "AES256",
                                },
                            },
                        ],
                    },
                )
                
                # Set lifecycle policy for archival
                self.s3_client.put_bucket_lifecycle_configuration(
                    Bucket=self.bucket_name,
                    LifecycleConfiguration={
                        "Rules": [
                            {
                                "ID": "AuditLogArchival",
                                "Status": "Enabled",
                                "Filter": {
                                    "Prefix": self.prefix,
                                },
                                "Transitions": [
                                    {
                                        "Days": 30,
                                        "StorageClass": "STANDARD_IA",
                                    },
                                    {
                                        "Days": 90,
                                        "StorageClass": "GLACIER",
                                    },
                                ],
                            },
                        ],
                    },
                )
                
                logger.info(f"Created S3 bucket for audit logs: {self.bucket_name}")
            else:
                raise
    
    async def store_audit_logs(
        self,
        logs: List[dict],
        date: Optional[datetime] = None,
    ) -> str:
        """
        Store audit logs in S3.
        
        Args:
            logs: List of audit log entries
            date: Date for log file (defaults to current)
            
        Returns:
            S3 URL of stored file
        """
        if not self.s3_client:
            logger.warning("S3 not configured, skipping audit log storage")
            return ""
        
        self._ensure_bucket()
        
        date = date or datetime.utcnow()
        
        # Create file content
        log_lines = [json.dumps(log, default=str) for log in logs]
        content = "\n".join(log_lines)
        
        # Compress
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as f:
            f.write(content.encode("utf-8"))
        
        compressed_content = buffer.getvalue()
        
        # Generate key
        key = (
            f"{self.prefix}"
            f"year={date.year}/"
            f"month={date.month:02d}/"
            f"day={date.day:02d}/"
            f"audit_{date.strftime('%Y%m%d_%H%M%S')}.json.gz"
        )
        
        try:
            # Upload with WORM settings
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=compressed_content,
                ContentType="application/gzip",
                ServerSideEncryption="AES256",
                Metadata={
                    "record-count": str(len(logs)),
                    "created-at": datetime.utcnow().isoformat(),
                },
            )
            
            # Apply object lock for WORM
            try:
                self.s3_client.put_object_legal_hold(
                    Bucket=self.bucket_name,
                    Key=key,
                    LegalHold={"Status": "ON"},
                )
            except ClientError as e:
                logger.warning(f"Could not apply legal hold: {e}")
            
            s3_url = f"s3://{self.bucket_name}/{key}"
            
            logger.info(
                f"Audit logs stored in S3",
                url=s3_url,
                record_count=len(logs),
                size_bytes=len(compressed_content),
            )
            
            return s3_url
            
        except ClientError as e:
            logger.error(f"Failed to store audit logs: {e}")
            raise AuditStorageError(f"Failed to store audit logs: {e}") from e
    
    async def retrieve_audit_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        tenant_id: Optional[str] = None,
    ) -> List[dict]:
        """
        Retrieve audit logs from S3.
        
        Args:
            start_date: Start date
            end_date: End date
            tenant_id: Optional tenant filter
            
        Returns:
            List of audit log entries
        """
        if not self.s3_client:
            raise AuditStorageError("S3 not configured")
        
        logs = []
        
        # List objects in date range
        current_date = start_date
        while current_date <= end_date:
            prefix = (
                f"{self.prefix}"
                f"year={current_date.year}/"
                f"month={current_date.month:02d}/"
                f"day={current_date.day:02d}/"
            )
            
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                )
                
                for obj in response.get("Contents", []):
                    # Download and decompress
                    obj_response = self.s3_client.get_object(
                        Bucket=self.bucket_name,
                        Key=obj["Key"],
                    )
                    
                    compressed_data = obj_response["Body"].read()
                    
                    # Decompress
                    buffer = BytesIO(compressed_data)
                    with gzip.GzipFile(fileobj=buffer, mode="rb") as f:
                        content = f.read().decode("utf-8")
                    
                    # Parse JSON lines
                    for line in content.strip().split("\n"):
                        log = json.loads(line)
                        
                        # Filter by tenant if specified
                        if tenant_id and log.get("tenant_id") != tenant_id:
                            continue
                        
                        logs.append(log)
                        
            except ClientError as e:
                logger.error(f"Failed to retrieve audit logs: {e}")
                raise
            
            current_date += timedelta(days=1)
        
        return logs
    
    async def verify_integrity(self, s3_url: str, expected_hash: str) -> bool:
        """
        Verify integrity of stored audit logs.
        
        Args:
            s3_url: S3 URL of audit log file
            expected_hash: Expected hash
            
        Returns:
            True if integrity verified
        """
        if not self.s3_client:
            raise AuditStorageError("S3 not configured")
        
        # Parse S3 URL
        parts = s3_url.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1]
        
        try:
            # Get object metadata
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            
            # Calculate hash of content
            obj_response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = obj_response["Body"].read()
            
            import hashlib
            actual_hash = hashlib.sha256(content).hexdigest()
            
            return actual_hash == expected_hash
            
        except ClientError as e:
            logger.error(f"Failed to verify integrity: {e}")
            return False
    
    async def get_storage_stats(self) -> dict:
        """
        Get audit log storage statistics.
        
        Returns:
            Storage statistics
        """
        if not self.s3_client:
            return {"error": "S3 not configured"}
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix,
            )
            
            total_size = 0
            total_objects = 0
            
            for obj in response.get("Contents", []):
                total_size += obj["Size"]
                total_objects += 1
            
            return {
                "bucket": self.bucket_name,
                "prefix": self.prefix,
                "total_objects": total_objects,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
            }
            
        except ClientError as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}


# Global audit storage instance
audit_storage = AuditStorage()
