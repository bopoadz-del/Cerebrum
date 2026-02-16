"""
Data Lake Management
S3/Azure Data Lake Storage for raw data
"""

import json
import gzip
from typing import Dict, Any, List, Optional, BinaryIO
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import logging

import boto3
from azure.storage.filedatalake import DataLakeServiceClient
from google.cloud import storage

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DataLakeObject:
    """Data lake object metadata"""
    key: str
    size_bytes: int
    last_modified: datetime
    etag: str
    content_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class S3DataLake:
    """S3 Data Lake implementation"""
    
    def __init__(self, bucket: str = None, region: str = 'us-east-1'):
        self.bucket = bucket or settings.AWS_S3_BUCKET
        self.region = region
        self.client = boto3.client('s3', region_name=region)
    
    def write_object(
        self,
        key: str,
        data: bytes,
        content_type: str = 'application/json',
        metadata: Dict[str, Any] = None,
        compress: bool = True
    ) -> bool:
        """Write object to S3"""
        try:
            # Compress if requested
            if compress:
                data = gzip.compress(data)
                key = f"{key}.gz"
            
            extra_args = {
                'ContentType': content_type,
                'Metadata': metadata or {}
            }
            
            if compress:
                extra_args['ContentEncoding'] = 'gzip'
            
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                **extra_args
            )
            
            logger.info(f"Written object to s3://{self.bucket}/{key}")
            return True
        
        except Exception as e:
            logger.error(f"Error writing to S3: {e}")
            return False
    
    def read_object(self, key: str, decompress: bool = True) -> Optional[bytes]:
        """Read object from S3"""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            data = response['Body'].read()
            
            # Decompress if needed
            if decompress and key.endswith('.gz'):
                data = gzip.decompress(data)
            
            return data
        
        except Exception as e:
            logger.error(f"Error reading from S3: {e}")
            return None
    
    def list_objects(
        self,
        prefix: str = '',
        max_keys: int = 1000
    ) -> List[DataLakeObject]:
        """List objects in S3"""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = []
            for obj in response.get('Contents', []):
                objects.append(DataLakeObject(
                    key=obj['Key'],
                    size_bytes=obj['Size'],
                    last_modified=obj['LastModified'],
                    etag=obj['ETag'],
                    content_type='',
                    metadata={}
                ))
            
            return objects
        
        except Exception as e:
            logger.error(f"Error listing S3 objects: {e}")
            return []
    
    def delete_object(self, key: str) -> bool:
        """Delete object from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted object s3://{self.bucket}/{key}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting from S3: {e}")
            return False
    
    def get_object_url(self, key: str, expires_hours: int = 1) -> str:
        """Get presigned URL for object"""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expires_hours * 3600
            )
            return url
        
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return ""


class AzureDataLake:
    """Azure Data Lake Storage implementation"""
    
    def __init__(self, account_name: str = None, filesystem: str = 'raw'):
        self.account_name = account_name or settings.AZURE_STORAGE_ACCOUNT
        self.filesystem = filesystem
        
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.service_client = DataLakeServiceClient.from_connection_string(connection_string)
        self.filesystem_client = self.service_client.get_file_system_client(filesystem)
    
    def write_object(
        self,
        path: str,
        data: bytes,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Write object to ADLS"""
        try:
            file_client = self.filesystem_client.get_file_client(path)
            file_client.create_file()
            file_client.append_data(data, offset=0, length=len(data))
            file_client.flush_data(len(data))
            
            if metadata:
                file_client.set_metadata(metadata)
            
            logger.info(f"Written object to adls://{self.filesystem}/{path}")
            return True
        
        except Exception as e:
            logger.error(f"Error writing to ADLS: {e}")
            return False
    
    def read_object(self, path: str) -> Optional[bytes]:
        """Read object from ADLS"""
        try:
            file_client = self.filesystem_client.get_file_client(path)
            download = file_client.download_file()
            return download.readall()
        
        except Exception as e:
            logger.error(f"Error reading from ADLS: {e}")
            return None


class GCSDataLake:
    """Google Cloud Storage Data Lake"""
    
    def __init__(self, bucket: str = None, project: str = None):
        self.bucket = bucket or settings.GCS_BUCKET
        self.project = project or settings.GCP_PROJECT_ID
        self.client = storage.Client(project=self.project)
        self.bucket_client = self.client.bucket(self.bucket)
    
    def write_object(
        self,
        blob_name: str,
        data: bytes,
        content_type: str = 'application/json',
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Write object to GCS"""
        try:
            blob = self.bucket_client.blob(blob_name)
            blob.content_type = content_type
            
            if metadata:
                blob.metadata = metadata
            
            blob.upload_from_string(data)
            
            logger.info(f"Written object to gs://{self.bucket}/{blob_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error writing to GCS: {e}")
            return False
    
    def read_object(self, blob_name: str) -> Optional[bytes]:
        """Read object from GCS"""
        try:
            blob = self.bucket_client.blob(blob_name)
            return blob.download_as_bytes()
        
        except Exception as e:
            logger.error(f"Error reading from GCS: {e}")
            return None


class DataLakeManager:
    """Manage data lake operations"""
    
    def __init__(self):
        self.s3: Optional[S3DataLake] = None
        self.azure: Optional[AzureDataLake] = None
        self.gcs: Optional[GCSDataLake] = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize data lake clients"""
        if settings.AWS_ACCESS_KEY_ID:
            self.s3 = S3DataLake()
        
        if settings.AZURE_STORAGE_CONNECTION_STRING:
            self.azure = AzureDataLake()
        
        if settings.GCP_PROJECT_ID:
            self.gcs = GCSDataLake()
    
    def store_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        timestamp: datetime = None
    ) -> bool:
        """Store event in data lake"""
        timestamp = timestamp or datetime.utcnow()
        
        # Organize by date
        date_path = timestamp.strftime('%Y/%m/%d')
        key = f"events/{event_type}/{date_path}/{timestamp.isoformat()}.json"
        
        event_data = {
            'event_type': event_type,
            'timestamp': timestamp.isoformat(),
            'data': data
        }
        
        json_data = json.dumps(event_data, default=str).encode()
        
        # Store in primary data lake
        if self.s3:
            return self.s3.write_object(key, json_data)
        elif self.gcs:
            return self.gcs.write_object(key, json_data)
        elif self.azure:
            return self.azure.write_object(key, json_data)
        
        return False
    
    def store_raw_data(
        self,
        source: str,
        data: bytes,
        filename: str,
        content_type: str = 'application/json'
    ) -> bool:
        """Store raw data from external sources"""
        timestamp = datetime.utcnow()
        date_path = timestamp.strftime('%Y/%m/%d')
        key = f"raw/{source}/{date_path}/{filename}"
        
        if self.s3:
            return self.s3.write_object(key, data, content_type)
        elif self.gcs:
            return self.gcs.write_object(key, data, content_type)
        elif self.azure:
            return self.azure.write_object(key, data)
        
        return False
    
    def get_storage_summary(self) -> Dict[str, Any]:
        """Get data lake storage summary"""
        summary = {
            'providers': [],
            'total_size_bytes': 0,
            'total_objects': 0
        }
        
        if self.s3:
            objects = self.s3.list_objects()
            size = sum(obj.size_bytes for obj in objects)
            summary['providers'].append({
                'name': 'S3',
                'bucket': self.s3.bucket,
                'objects': len(objects),
                'size_bytes': size
            })
            summary['total_size_bytes'] += size
            summary['total_objects'] += len(objects)
        
        return summary


# Global data lake manager
data_lake = DataLakeManager()
