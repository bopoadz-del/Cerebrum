"""
Custom Integrations Module - Webhook Management and Custom APIs
Item 292: Custom integrations, webhooks, and API management
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
import hmac
import hashlib
import json

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, HttpUrl
from fastapi import HTTPException, Request, Header
import requests
from enum import Enum


class WebhookEvent(str, Enum):
    """Available webhook events"""
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    
    # Document events
    DOCUMENT_CREATED = "document.created"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"
    
    # User events
    USER_INVITED = "user.invited"
    USER_JOINED = "user.joined"
    USER_REMOVED = "user.removed"
    
    # Financial events
    INVOICE_CREATED = "invoice.created"
    PAYMENT_RECEIVED = "payment.received"
    
    # Custom events
    CUSTOM = "custom"


class WebhookStatus(str, Enum):
    """Webhook subscription status"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    FAILED = "failed"


# Database Models

class WebhookSubscription(Base):
    """Webhook subscription"""
    __tablename__ = 'webhook_subscriptions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Subscription details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Endpoint
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)
    
    # Events
    events = Column(JSONB, default=list)
    event_filters = Column(JSONB, default=dict)
    
    # Status
    status = Column(String(50), default=WebhookStatus.ACTIVE.value)
    
    # Retry settings
    max_retries = Column(Integer, default=3)
    retry_interval_seconds = Column(Integer, default=60)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_webhooks_tenant_status', 'tenant_id', 'status'),
    )


class WebhookDelivery(Base):
    """Webhook delivery attempts"""
    __tablename__ = 'webhook_deliveries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('webhook_subscriptions.id', ondelete='CASCADE'), nullable=False)
    
    # Event details
    event_type = Column(String(100), nullable=False)
    event_id = Column(String(255), nullable=False)
    
    # Request
    payload = Column(JSONB, nullable=False)
    headers = Column(JSONB, default=dict)
    
    # Response
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSONB, nullable=True)
    
    # Delivery status
    status = Column(String(50), default='pending')  # pending, success, failed, retrying
    attempt_number = Column(Integer, default=1)
    
    # Timing
    requested_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    
    # Error
    error_message = Column(Text, nullable=True)


class CustomAPIEndpoint(Base):
    """Custom API endpoint definitions"""
    __tablename__ = 'custom_api_endpoints'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Endpoint details
    name = Column(String(255), nullable=False)
    path = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, PATCH
    
    # Configuration
    description = Column(Text, nullable=True)
    request_schema = Column(JSONB, nullable=True)
    response_schema = Column(JSONB, nullable=True)
    
    # Handler
    handler_type = Column(String(50), default='webhook')  # webhook, lambda, function
    handler_config = Column(JSONB, default=dict)
    
    # Security
    auth_required = Column(Boolean, default=True)
    required_permissions = Column(JSONB, default=list)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=100)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class APIKey(Base):
    """API key management"""
    __tablename__ = 'api_keys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Key details
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(10), nullable=False)
    key_hash = Column(String(255), nullable=False)
    
    # Permissions
    scopes = Column(JSONB, default=list)
    allowed_ips = Column(JSONB, default=list)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=1000)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    revoked_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


# Pydantic Schemas

class CreateWebhookRequest(BaseModel):
    """Create webhook subscription"""
    name: str
    description: Optional[str] = None
    url: HttpUrl
    events: List[str]
    event_filters: Dict[str, Any] = Field(default_factory=dict)
    max_retries: int = 3
    secret: Optional[str] = None


class UpdateWebhookRequest(BaseModel):
    """Update webhook subscription"""
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    status: Optional[WebhookStatus] = None


class WebhookResponse(BaseModel):
    """Webhook subscription response"""
    id: str
    name: str
    url: str
    events: List[str]
    status: str
    created_at: datetime


class CreateAPIKeyRequest(BaseModel):
    """Create API key request"""
    name: str
    scopes: List[str] = Field(default_factory=list)
    allowed_ips: List[str] = Field(default_factory=list)
    expires_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response"""
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]


class CustomEndpointRequest(BaseModel):
    """Create custom endpoint"""
    name: str
    path: str
    method: str
    description: Optional[str] = None
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    handler_type: str = 'webhook'
    handler_config: Dict[str, Any] = Field(default_factory=dict)


# Service Classes

class WebhookService:
    """Service for webhook management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_subscription(
        self,
        tenant_id: str,
        request: CreateWebhookRequest,
        created_by: Optional[str] = None
    ) -> WebhookSubscription:
        """Create webhook subscription"""
        
        # Validate events
        valid_events = [e.value for e in WebhookEvent]
        for event in request.events:
            if event not in valid_events and not event.startswith('custom.'):
                raise HTTPException(400, f"Invalid event: {event}")
        
        # Generate secret if not provided
        secret = request.secret or self._generate_secret()
        
        subscription = WebhookSubscription(
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            url=str(request.url),
            secret=secret,
            events=request.events,
            event_filters=request.event_filters,
            max_retries=request.max_retries,
            created_by=created_by
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def _generate_secret(self) -> str:
        """Generate webhook secret"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def get_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Get webhook subscription"""
        return self.db.query(WebhookSubscription).filter(
            WebhookSubscription.id == subscription_id
        ).first()
    
    def list_subscriptions(
        self,
        tenant_id: str,
        status: Optional[WebhookStatus] = None
    ) -> List[WebhookSubscription]:
        """List webhook subscriptions"""
        
        query = self.db.query(WebhookSubscription).filter(
            WebhookSubscription.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(WebhookSubscription.status == status.value)
        
        return query.order_by(WebhookSubscription.created_at.desc()).all()
    
    def update_subscription(
        self,
        subscription_id: str,
        request: UpdateWebhookRequest
    ) -> WebhookSubscription:
        """Update webhook subscription"""
        
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(404, "Webhook subscription not found")
        
        if request.name:
            subscription.name = request.name
        
        if request.url:
            subscription.url = str(request.url)
        
        if request.events:
            subscription.events = request.events
        
        if request.status:
            subscription.status = request.status.value
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def delete_subscription(self, subscription_id: str):
        """Delete webhook subscription"""
        
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(404, "Webhook subscription not found")
        
        self.db.delete(subscription)
        self.db.commit()
    
    def trigger_event(
        self,
        tenant_id: str,
        event_type: str,
        payload: Dict[str, Any],
        event_id: Optional[str] = None
    ) -> List[WebhookDelivery]:
        """Trigger webhook event"""
        
        event_id = event_id or str(uuid.uuid4())
        
        # Find matching subscriptions
        subscriptions = self.db.query(WebhookSubscription).filter(
            WebhookSubscription.tenant_id == tenant_id,
            WebhookSubscription.status == WebhookStatus.ACTIVE.value
        ).all()
        
        deliveries = []
        
        for subscription in subscriptions:
            # Check if subscription listens to this event
            if event_type not in subscription.events and '*' not in subscription.events:
                continue
            
            # Check event filters
            if not self._matches_filters(payload, subscription.event_filters):
                continue
            
            # Create delivery record
            delivery = WebhookDelivery(
                subscription_id=subscription.id,
                event_type=event_type,
                event_id=event_id,
                payload=payload,
                headers={
                    'X-Webhook-Event': event_type,
                    'X-Webhook-ID': event_id,
                    'X-Webhook-Timestamp': datetime.utcnow().isoformat()
                }
            )
            
            self.db.add(delivery)
            deliveries.append(delivery)
        
        self.db.commit()
        
        # Send webhooks asynchronously
        for delivery in deliveries:
            self._send_webhook(delivery)
        
        return deliveries
    
    def _matches_filters(
        self,
        payload: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """Check if payload matches event filters"""
        
        if not filters:
            return True
        
        for key, value in filters.items():
            payload_value = payload.get(key)
            
            if isinstance(value, list):
                if payload_value not in value:
                    return False
            elif payload_value != value:
                return False
        
        return True
    
    def _send_webhook(self, delivery: WebhookDelivery):
        """Send webhook delivery"""
        
        subscription = self.get_subscription(str(delivery.subscription_id))
        
        if not subscription:
            return
        
        # Generate signature
        signature = self._generate_signature(
            subscription.secret,
            delivery.payload
        )
        
        headers = {
            **delivery.headers,
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature
        }
        
        try:
            response = requests.post(
                subscription.url,
                headers=headers,
                json=delivery.payload,
                timeout=30
            )
            
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:10000]  # Limit size
            delivery.response_headers = dict(response.headers)
            delivery.delivered_at = datetime.utcnow()
            
            if 200 <= response.status_code < 300:
                delivery.status = 'success'
            else:
                delivery.status = 'failed'
                delivery.error_message = f"HTTP {response.status_code}"
                
                # Schedule retry
                if delivery.attempt_number < subscription.max_retries:
                    self._schedule_retry(delivery)
            
        except Exception as e:
            delivery.status = 'failed'
            delivery.error_message = str(e)[:500]
            
            # Schedule retry
            if delivery.attempt_number < subscription.max_retries:
                self._schedule_retry(delivery)
        
        self.db.commit()
    
    def _generate_signature(self, secret: str, payload: Dict[str, Any]) -> str:
        """Generate HMAC signature for webhook"""
        
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def _schedule_retry(self, delivery: WebhookDelivery):
        """Schedule webhook retry"""
        
        # In production, use a task queue like Celery
        # For now, just increment attempt number
        delivery.attempt_number += 1
        delivery.status = 'retrying'
    
    def verify_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature"""
        
        expected = self._generate_signature(secret, json.loads(payload))
        
        return hmac.compare_digest(signature, expected)


class APIKeyService:
    """Service for API key management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_api_key(
        self,
        tenant_id: str,
        request: CreateAPIKeyRequest,
        created_by: Optional[str] = None
    ) -> tuple:
        """Create new API key"""
        
        # Generate key
        import secrets
        api_key = f"cbr_{secrets.token_urlsafe(32)}"
        key_prefix = api_key[:10]
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Calculate expiration
        expires_at = None
        if request.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
        
        key_record = APIKey(
            tenant_id=tenant_id,
            name=request.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=request.scopes,
            allowed_ips=request.allowed_ips,
            expires_at=expires_at,
            created_by=created_by
        )
        
        self.db.add(key_record)
        self.db.commit()
        self.db.refresh(key_record)
        
        return key_record, api_key
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key"""
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        key_record = self.db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not key_record:
            return None
        
        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.utcnow():
            return None
        
        # Update usage
        key_record.last_used_at = datetime.utcnow()
        key_record.usage_count += 1
        
        self.db.commit()
        
        return key_record
    
    def revoke_api_key(
        self,
        key_id: str,
        revoked_by: str,
        reason: Optional[str] = None
    ):
        """Revoke API key"""
        
        key = self.db.query(APIKey).filter(APIKey.id == key_id).first()
        
        if not key:
            raise HTTPException(404, "API key not found")
        
        key.is_active = False
        key.revoked_at = datetime.utcnow()
        key.revoked_by = revoked_by
        key.revoked_reason = reason
        
        self.db.commit()


class CustomIntegrationService:
    """Service for custom integrations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_endpoint(
        self,
        tenant_id: str,
        request: CustomEndpointRequest,
        created_by: Optional[str] = None
    ) -> CustomAPIEndpoint:
        """Create custom API endpoint"""
        
        # Validate path is unique for tenant
        existing = self.db.query(CustomAPIEndpoint).filter(
            CustomAPIEndpoint.tenant_id == tenant_id,
            CustomAPIEndpoint.path == request.path,
            CustomAPIEndpoint.method == request.method
        ).first()
        
        if existing:
            raise HTTPException(409, "Endpoint with this path and method already exists")
        
        endpoint = CustomAPIEndpoint(
            tenant_id=tenant_id,
            name=request.name,
            path=request.path,
            method=request.method.upper(),
            description=request.description,
            request_schema=request.request_schema,
            response_schema=request.response_schema,
            handler_type=request.handler_type,
            handler_config=request.handler_config,
            created_by=created_by
        )
        
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        
        return endpoint


# Export
__all__ = [
    'WebhookEvent',
    'WebhookStatus',
    'WebhookSubscription',
    'WebhookDelivery',
    'CustomAPIEndpoint',
    'APIKey',
    'CreateWebhookRequest',
    'UpdateWebhookRequest',
    'WebhookResponse',
    'CreateAPIKeyRequest',
    'APIKeyResponse',
    'CustomEndpointRequest',
    'WebhookService',
    'APIKeyService',
    'CustomIntegrationService'
]
