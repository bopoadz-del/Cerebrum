"""
Bulk Operations Module - Bulk Import and Rate Limit Management
Item 296: Bulk operations and rate limit increases
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import uuid
from app.db.base_class import Base
import io
import csv
import json

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException, UploadFile
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.enterprise.tenant_isolation import Tenant


class BulkOperationType(str, Enum):
    """Types of bulk operations"""
    IMPORT_USERS = "import_users"
    IMPORT_PROJECTS = "import_projects"
    IMPORT_TASKS = "import_tasks"
    IMPORT_DOCUMENTS = "import_documents"
    UPDATE_RECORDS = "update_records"
    DELETE_RECORDS = "delete_records"
    EXPORT_DATA = "export_data"


class BulkOperationStatus(str, Enum):
    """Bulk operation status"""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Database Models

class BulkOperation(Base):
    """Bulk operation tracking"""
    __tablename__ = 'bulk_operations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Operation details
    operation_type = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)
    
    # File info
    original_filename = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    
    # Configuration
    config = Column(JSONB, default=dict)
    field_mapping = Column(JSONB, default=dict)
    
    # Status
    status = Column(String(50), default=BulkOperationStatus.PENDING.value)
    progress_percentage = Column(Integer, default=0)
    
    # Statistics
    total_records = Column(Integer, nullable=True)
    processed_records = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    
    # Results
    results = Column(JSONB, default=dict)
    errors = Column(JSONB, default=list)
    warnings = Column(JSONB, default=list)
    
    # Output
    output_file_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Rate limiting override
    rate_limit_override = Column(Integer, nullable=True)


class RateLimitIncreaseRequest(Base):
    """Rate limit increase requests"""
    __tablename__ = 'rate_limit_increase_requests'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Current limits
    current_limit = Column(Integer, nullable=False)
    requested_limit = Column(Integer, nullable=False)
    
    # Resource type
    resource_type = Column(String(50), nullable=False)  # api_calls, storage, users, projects
    
    # Justification
    reason = Column(Text, nullable=False)
    expected_usage = Column(Text, nullable=True)
    duration_months = Column(Integer, default=12)
    
    # Status
    status = Column(String(50), default='pending')
    
    # Approval
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_limit = Column(Integer, nullable=True)
    
    # Timestamps
    requested_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class ImportTemplate(Base):
    """Import templates"""
    __tablename__ = 'import_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Template details
    entity_type = Column(String(50), nullable=False)  # users, projects, tasks, etc.
    file_format = Column(String(20), default='csv')  # csv, xlsx, json
    
    # Column definitions
    columns = Column(JSONB, default=list)
    sample_data = Column(JSONB, default=list)
    
    # Validation rules
    validation_rules = Column(JSONB, default=dict)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class CreateBulkOperationRequest(BaseModel):
    """Create bulk operation"""
    operation_type: BulkOperationType
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    field_mapping: Dict[str, str] = Field(default_factory=dict)


class RateLimitIncreaseRequestCreate(BaseModel):
    """Request rate limit increase"""
    resource_type: str
    current_limit: int
    requested_limit: int
    reason: str
    expected_usage: Optional[str] = None
    duration_months: int = 12


class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    id: str
    operation_type: str
    status: str
    progress_percentage: int
    total_records: Optional[int]
    processed_records: int
    success_count: int
    error_count: int
    created_at: datetime


class ImportValidationResult(BaseModel):
    """Import validation result"""
    valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: List[Dict[str, Any]]


# Service Classes

class BulkOperationService:
    """Service for bulk operations"""
    
    BATCH_SIZE = 100
    MAX_WORKERS = 4
    
    def __init__(self, db: Session, storage_client=None):
        self.db = db
        self.storage = storage_client
        self.executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)
    
    def create_operation(
        self,
        tenant_id: str,
        request: CreateBulkOperationRequest,
        file: Optional[UploadFile] = None,
        created_by: Optional[str] = None
    ) -> BulkOperation:
        """Create bulk operation"""
        
        operation = BulkOperation(
            tenant_id=tenant_id,
            operation_type=request.operation_type.value,
            description=request.description,
            config=request.config,
            field_mapping=request.field_mapping,
            created_by=created_by
        )
        
        if file:
            operation.original_filename = file.filename
            operation.file_size_bytes = 0  # Will be updated after upload
        
        self.db.add(operation)
        self.db.commit()
        self.db.refresh(operation)
        
        # Upload file if provided
        if file:
            self._upload_file(operation, file)
        
        return operation
    
    def _upload_file(self, operation: BulkOperation, file: UploadFile):
        """Upload file to storage"""
        
        # In production, upload to S3 or similar
        file_path = f"bulk-operations/{operation.tenant_id}/{operation.id}/{file.filename}"
        
        # Placeholder: store file info
        operation.file_url = file_path
        self.db.commit()
    
    def get_operation(self, operation_id: str) -> Optional[BulkOperation]:
        """Get bulk operation"""
        return self.db.query(BulkOperation).filter(
            BulkOperation.id == operation_id
        ).first()
    
    def list_operations(
        self,
        tenant_id: str,
        operation_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[BulkOperation]:
        """List bulk operations"""
        
        query = self.db.query(BulkOperation).filter(
            BulkOperation.tenant_id == tenant_id
        )
        
        if operation_type:
            query = query.filter(BulkOperation.operation_type == operation_type)
        
        if status:
            query = query.filter(BulkOperation.status == status)
        
        return query.order_by(BulkOperation.created_at.desc()).all()
    
    async def execute_operation(self, operation_id: str):
        """Execute bulk operation"""
        
        operation = self.get_operation(operation_id)
        if not operation:
            raise HTTPException(404, "Operation not found")
        
        operation.status = BulkOperationStatus.PROCESSING.value
        operation.started_at = datetime.utcnow()
        self.db.commit()
        
        try:
            # Execute based on operation type
            if operation.operation_type == BulkOperationType.IMPORT_USERS.value:
                await self._import_users(operation)
            elif operation.operation_type == BulkOperationType.IMPORT_PROJECTS.value:
                await self._import_projects(operation)
            elif operation.operation_type == BulkOperationType.IMPORT_TASKS.value:
                await self._import_tasks(operation)
            elif operation.operation_type == BulkOperationType.EXPORT_DATA.value:
                await self._export_data(operation)
            
            operation.status = BulkOperationStatus.COMPLETED.value
            operation.progress_percentage = 100
            operation.completed_at = datetime.utcnow()
            
        except Exception as e:
            operation.status = BulkOperationStatus.FAILED.value
            operation.errors.append({
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        
        self.db.commit()
    
    async def _import_users(self, operation: BulkOperation):
        """Import users from file"""
        
        # Read file
        records = self._read_import_file(operation)
        operation.total_records = len(records)
        self.db.commit()
        
        # Process in batches
        for i in range(0, len(records), self.BATCH_SIZE):
            batch = records[i:i + self.BATCH_SIZE]
            
            for record in batch:
                try:
                    # Validate and transform record
                    user_data = self._transform_user_record(record, operation.field_mapping)
                    
                    # Create user
                    # user = User(**user_data)
                    # self.db.add(user)
                    
                    operation.success_count += 1
                    
                except Exception as e:
                    operation.error_count += 1
                    operation.errors.append({
                        'row': i + batch.index(record) + 1,
                        'message': str(e),
                        'data': record
                    })
            
            operation.processed_records += len(batch)
            operation.progress_percentage = int(
                operation.processed_records / operation.total_records * 100
            )
            
            self.db.commit()
            
            # Small delay to prevent overwhelming the database
            await asyncio.sleep(0.1)
    
    def _transform_user_record(
        self,
        record: Dict[str, Any],
        field_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Transform import record to user data"""
        
        user_data = {}
        
        for target_field, source_field in field_mapping.items():
            if source_field in record:
                user_data[target_field] = record[source_field]
        
        # Set defaults
        user_data.setdefault('is_active', True)
        
        return user_data
    
    async def _import_projects(self, operation: BulkOperation):
        """Import projects from file"""
        # Similar to _import_users
        pass
    
    async def _import_tasks(self, operation: BulkOperation):
        """Import tasks from file"""
        # Similar to _import_users
        pass
    
    async def _export_data(self, operation: BulkOperation):
        """Export data to file"""
        
        entity_type = operation.config.get('entity_type')
        filters = operation.config.get('filters', {})
        
        # Query data
        if entity_type == 'users':
            data = self._export_users(operation.tenant_id, filters)
        elif entity_type == 'projects':
            data = self._export_projects(operation.tenant_id, filters)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        # Write to file
        output_format = operation.config.get('format', 'csv')
        
        if output_format == 'csv':
            output_file = self._write_csv(data)
        elif output_format == 'json':
            output_file = self._write_json(data)
        else:
            raise ValueError(f"Unknown format: {output_format}")
        
        # Upload output file
        operation.output_file_url = output_file
        operation.total_records = len(data)
        operation.success_count = len(data)
    
    def _export_users(
        self,
        tenant_id: str,
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Export users data"""
        
        # Query users
        # users = self.db.query(User).filter(User.tenant_id == tenant_id).all()
        
        # Transform to export format
        # return [self._user_to_dict(u) for u in users]
        return []
    
    def _export_projects(
        self,
        tenant_id: str,
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Export projects data"""
        return []
    
    def _write_csv(self, data: List[Dict[str, Any]]) -> str:
        """Write data to CSV file"""
        
        if not data:
            return ""
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        # In production, upload to S3 and return URL
        return "s3://exports/data.csv"
    
    def _write_json(self, data: List[Dict[str, Any]]) -> str:
        """Write data to JSON file"""
        
        # In production, upload to S3 and return URL
        return "s3://exports/data.json"
    
    def _read_import_file(self, operation: BulkOperation) -> List[Dict[str, Any]]:
        """Read import file"""
        
        # In production, read from S3
        # For now, return empty list
        return []
    
    def validate_import_file(
        self,
        operation_id: str
    ) -> ImportValidationResult:
        """Validate import file"""
        
        operation = self.get_operation(operation_id)
        if not operation:
            raise HTTPException(404, "Operation not found")
        
        operation.status = BulkOperationStatus.VALIDATING.value
        self.db.commit()
        
        # Read file
        records = self._read_import_file(operation)
        
        errors = []
        valid_count = 0
        
        for i, record in enumerate(records):
            record_errors = self._validate_record(record, operation.operation_type)
            
            if record_errors:
                errors.append({
                    'row': i + 1,
                    'errors': record_errors
                })
            else:
                valid_count += 1
        
        result = ImportValidationResult(
            valid=len(errors) == 0,
            total_rows=len(records),
            valid_rows=valid_count,
            invalid_rows=len(errors),
            errors=errors
        )
        
        operation.status = BulkOperationStatus.PENDING.value
        self.db.commit()
        
        return result
    
    def _validate_record(
        self,
        record: Dict[str, Any],
        operation_type: str
    ) -> List[str]:
        """Validate single record"""
        
        errors = []
        
        if operation_type == BulkOperationType.IMPORT_USERS.value:
            if not record.get('email'):
                errors.append("Email is required")
            if not record.get('first_name'):
                errors.append("First name is required")
        
        return errors
    
    def cancel_operation(self, operation_id: str) -> BulkOperation:
        """Cancel bulk operation"""
        
        operation = self.get_operation(operation_id)
        if not operation:
            raise HTTPException(404, "Operation not found")
        
        if operation.status not in [
            BulkOperationStatus.PENDING.value,
            BulkOperationStatus.VALIDATING.value
        ]:
            raise HTTPException(400, "Cannot cancel operation in current state")
        
        operation.status = BulkOperationStatus.CANCELLED.value
        self.db.commit()
        
        return operation


class RateLimitService:
    """Service for rate limit management"""
    
    DEFAULT_LIMITS = {
        'api_calls': 1000,  # per minute
        'storage': 100,  # GB
        'users': 100,
        'projects': 50,
        'webhooks': 100  # per minute
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def request_increase(
        self,
        tenant_id: str,
        request: RateLimitIncreaseRequestCreate,
        requested_by: str
    ) -> RateLimitIncreaseRequest:
        """Request rate limit increase"""
        
        increase_request = RateLimitIncreaseRequest(
            tenant_id=tenant_id,
            resource_type=request.resource_type,
            current_limit=request.current_limit,
            requested_limit=request.requested_limit,
            reason=request.reason,
            expected_usage=request.expected_usage,
            duration_months=request.duration_months,
            requested_by=requested_by
        )
        
        self.db.add(increase_request)
        self.db.commit()
        self.db.refresh(increase_request)
        
        return increase_request
    
    def approve_increase(
        self,
        request_id: str,
        approved_limit: int,
        approved_by: str
    ) -> RateLimitIncreaseRequest:
        """Approve rate limit increase"""
        
        increase_request = self.db.query(RateLimitIncreaseRequest).filter(
            RateLimitIncreaseRequest.id == request_id
        ).first()
        
        if not increase_request:
            raise HTTPException(404, "Request not found")
        
        increase_request.status = 'approved'
        increase_request.approved_limit = approved_limit
        increase_request.approved_by = approved_by
        increase_request.approved_at = datetime.utcnow()
        increase_request.reviewed_at = datetime.utcnow()
        
        self.db.commit()
        
        # Update tenant limits
        self._update_tenant_limit(
            increase_request.tenant_id,
            increase_request.resource_type,
            approved_limit
        )
        
        return increase_request
    
    def _update_tenant_limit(
        self,
        tenant_id: str,
        resource_type: str,
        new_limit: int
    ):
        """Update tenant's rate limit"""
        
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if tenant:
            limits = tenant.usage_limits or {}
            limits[resource_type] = new_limit
            tenant.usage_limits = limits
            self.db.commit()
    
    def get_current_limits(self, tenant_id: str) -> Dict[str, int]:
        """Get current rate limits for tenant"""
        
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if not tenant:
            return self.DEFAULT_LIMITS
        
        limits = tenant.usage_limits or {}
        
        # Merge with defaults
        return {**self.DEFAULT_LIMITS, **limits}


# Export
__all__ = [
    'BulkOperationType',
    'BulkOperationStatus',
    'BulkOperation',
    'RateLimitIncreaseRequest',
    'ImportTemplate',
    'CreateBulkOperationRequest',
    'RateLimitIncreaseRequestCreate',
    'BulkOperationResponse',
    'ImportValidationResult',
    'BulkOperationService',
    'RateLimitService'
]
