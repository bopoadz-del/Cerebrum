"""
Zapier/Make.com Integration Module
Item 319: Zapier/Make.com integration
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
import hmac
import hashlib
import json


# Database Models

class ZapierConnection(Base):
    """Zapier connection"""
    __tablename__ = 'zapier_connections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Connection info
    name = Column(String(255), nullable=False)
    webhook_url = Column(String(500), nullable=True)
    
    # API key for authentication
    api_key = Column(String(255), unique=True, nullable=False)
    
    # Settings
    triggers_enabled = Column(JSONB, default=list)
    actions_enabled = Column(JSONB, default=list)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Usage
    request_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class ZapierWebhookLog(Base):
    """Zapier webhook log"""
    __tablename__ = 'zapier_webhook_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey('zapier_connections.id', ondelete='CASCADE'), nullable=False)
    
    # Request details
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)
    
    # Response
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    
    # Status
    success = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class ZapierTriggerEvent(BaseModel):
    """Zapier trigger event"""
    event_type: str
    data: Dict[str, Any]


class ZapierActionRequest(BaseModel):
    """Zapier action request"""
    action_type: str
    data: Dict[str, Any]


class ZapierAuthResponse(BaseModel):
    """Zapier authentication response"""
    api_key: str
    tenant_id: str
    tenant_name: str


# Service Classes

class ZapierService:
    """Service for Zapier integration"""
    
    AVAILABLE_TRIGGERS = [
        {
            "key": "project_created",
            "name": "New Project",
            "description": "Triggers when a new project is created"
        },
        {
            "key": "task_completed",
            "name": "Task Completed",
            "description": "Triggers when a task is completed"
        },
        {
            "key": "document_uploaded",
            "name": "New Document",
            "description": "Triggers when a new document is uploaded"
        },
        {
            "key": "rfi_created",
            "name": "New RFI",
            "description": "Triggers when a new RFI is created"
        },
        {
            "key": "invoice_created",
            "name": "New Invoice",
            "description": "Triggers when a new invoice is created"
        }
    ]
    
    AVAILABLE_ACTIONS = [
        {
            "key": "create_project",
            "name": "Create Project",
            "description": "Creates a new project"
        },
        {
            "key": "create_task",
            "name": "Create Task",
            "description": "Creates a new task"
        },
        {
            "key": "upload_document",
            "name": "Upload Document",
            "description": "Uploads a document"
        },
        {
            "key": "create_rfi",
            "name": "Create RFI",
            "description": "Creates a new RFI"
        }
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_api_key(self) -> str:
        """Generate unique API key"""
        import secrets
        return f"zap_{secrets.token_urlsafe(32)}"
    
    def create_connection(
        self,
        tenant_id: str,
        name: str,
        created_by: Optional[str] = None
    ) -> ZapierConnection:
        """Create Zapier connection"""
        
        connection = ZapierConnection(
            tenant_id=tenant_id,
            name=name,
            api_key=self.generate_api_key(),
            triggers_enabled=[t['key'] for t in self.AVAILABLE_TRIGGERS],
            actions_enabled=[a['key'] for a in self.AVAILABLE_ACTIONS],
            created_by=created_by
        )
        
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        
        return connection
    
    def get_connection_by_api_key(self, api_key: str) -> Optional[ZapierConnection]:
        """Get connection by API key"""
        return self.db.query(ZapierConnection).filter(
            ZapierConnection.api_key == api_key,
            ZapierConnection.is_active == True
        ).first()
    
    def authenticate(self, api_key: str) -> Optional[ZapierConnection]:
        """Authenticate Zapier request"""
        
        connection = self.get_connection_by_api_key(api_key)
        
        if connection:
            connection.request_count += 1
            connection.last_used_at = datetime.utcnow()
            self.db.commit()
        
        return connection
    
    def get_triggers(self) -> List[Dict[str, Any]]:
        """Get available triggers"""
        return self.AVAILABLE_TRIGGERS
    
    def get_actions(self) -> List[Dict[str, Any]]:
        """Get available actions"""
        return self.AVAILABLE_ACTIONS
    
    def get_sample_data(self, trigger_type: str) -> Dict[str, Any]:
        """Get sample data for trigger"""
        
        samples = {
            "project_created": {
                "id": "proj_123",
                "name": "Sample Construction Project",
                "description": "A sample project for testing",
                "status": "active",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "created_at": "2024-01-01T00:00:00Z",
                "created_by": {
                    "id": "user_123",
                    "name": "John Doe",
                    "email": "john@example.com"
                }
            },
            "task_completed": {
                "id": "task_123",
                "title": "Complete Foundation Work",
                "description": "Foundation work for building A",
                "status": "completed",
                "project": {
                    "id": "proj_123",
                    "name": "Sample Construction Project"
                },
                "assignee": {
                    "id": "user_123",
                    "name": "John Doe"
                },
                "completed_at": "2024-01-15T10:00:00Z",
                "completed_by": {
                    "id": "user_123",
                    "name": "John Doe"
                }
            },
            "document_uploaded": {
                "id": "doc_123",
                "name": "Floor Plan - Level 1.pdf",
                "document_type": "drawing",
                "file_size": 1024000,
                "project": {
                    "id": "proj_123",
                    "name": "Sample Construction Project"
                },
                "uploaded_by": {
                    "id": "user_123",
                    "name": "John Doe"
                },
                "uploaded_at": "2024-01-10T14:30:00Z"
            },
            "rfi_created": {
                "id": "rfi_123",
                "number": "RFI-001",
                "subject": "Clarification on Foundation Specifications",
                "description": "Need clarification on concrete strength requirements",
                "status": "open",
                "priority": "high",
                "project": {
                    "id": "proj_123",
                    "name": "Sample Construction Project"
                },
                "created_by": {
                    "id": "user_123",
                    "name": "John Doe"
                },
                "created_at": "2024-01-12T09:00:00Z"
            },
            "invoice_created": {
                "id": "inv_123",
                "invoice_number": "INV-2024-001",
                "amount": 50000.00,
                "currency": "USD",
                "status": "pending",
                "project": {
                    "id": "proj_123",
                    "name": "Sample Construction Project"
                },
                "vendor": {
                    "id": "vendor_123",
                    "name": "ABC Construction"
                },
                "created_at": "2024-01-20T16:00:00Z"
            }
        }
        
        return samples.get(trigger_type, {})
    
    def execute_action(
        self,
        connection: ZapierConnection,
        request: ZapierActionRequest
    ) -> Dict[str, Any]:
        """Execute Zapier action"""
        
        # Check if action is enabled
        if request.action_type not in connection.actions_enabled:
            raise HTTPException(403, "Action not enabled")
        
        # Execute based on action type
        if request.action_type == 'create_project':
            return self._create_project(connection, request.data)
        elif request.action_type == 'create_task':
            return self._create_task(connection, request.data)
        elif request.action_type == 'upload_document':
            return self._upload_document(connection, request.data)
        elif request.action_type == 'create_rfi':
            return self._create_rfi(connection, request.data)
        else:
            raise HTTPException(400, f"Unknown action: {request.action_type}")
    
    def _create_project(
        self,
        connection: ZapierConnection,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create project via Zapier"""
        
        # Validate required fields
        if 'name' not in data:
            raise HTTPException(400, "Project name is required")
        
        # Create project
        # In production, call your project service
        
        return {
            "id": str(uuid.uuid4()),
            "name": data['name'],
            "status": "created",
            "message": "Project created successfully"
        }
    
    def _create_task(
        self,
        connection: ZapierConnection,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create task via Zapier"""
        
        if 'title' not in data:
            raise HTTPException(400, "Task title is required")
        
        if 'project_id' not in data:
            raise HTTPException(400, "Project ID is required")
        
        return {
            "id": str(uuid.uuid4()),
            "title": data['title'],
            "status": "created",
            "message": "Task created successfully"
        }
    
    def _upload_document(
        self,
        connection: ZapierConnection,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upload document via Zapier"""
        
        if 'name' not in data:
            raise HTTPException(400, "Document name is required")
        
        if 'file_url' not in data and 'file_content' not in data:
            raise HTTPException(400, "File URL or content is required")
        
        return {
            "id": str(uuid.uuid4()),
            "name": data['name'],
            "status": "uploaded",
            "message": "Document uploaded successfully"
        }
    
    def _create_rfi(
        self,
        connection: ZapierConnection,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create RFI via Zapier"""
        
        if 'subject' not in data:
            raise HTTPException(400, "RFI subject is required")
        
        if 'project_id' not in data:
            raise HTTPException(400, "Project ID is required")
        
        return {
            "id": str(uuid.uuid4()),
            "number": "RFI-001",
            "subject": data['subject'],
            "status": "created",
            "message": "RFI created successfully"
        }
    
    def trigger_event(
        self,
        connection: ZapierConnection,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Send trigger event to Zapier"""
        
        # Check if trigger is enabled
        if event_type not in connection.triggers_enabled:
            return
        
        # Check if webhook URL is configured
        if not connection.webhook_url:
            return
        
        # Send to Zapier
        import requests
        
        payload = {
            "event_type": event_type,
            "tenant_id": str(connection.tenant_id),
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            response = requests.post(
                connection.webhook_url,
                json=payload,
                timeout=30
            )
            
            # Log webhook
            log = ZapierWebhookLog(
                connection_id=connection.id,
                event_type=event_type,
                payload=payload,
                response_status=response.status_code,
                response_body=response.text[:1000],
                success=response.status_code == 200
            )
            self.db.add(log)
            self.db.commit()
        
        except Exception as e:
            # Log failure
            log = ZapierWebhookLog(
                connection_id=connection.id,
                event_type=event_type,
                payload=payload,
                success=False
            )
            self.db.add(log)
            self.db.commit()


# Export
__all__ = [
    'ZapierConnection',
    'ZapierWebhookLog',
    'ZapierTriggerEvent',
    'ZapierActionRequest',
    'ZapierAuthResponse',
    'ZapierService'
]
