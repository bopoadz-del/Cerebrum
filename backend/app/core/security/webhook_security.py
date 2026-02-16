"""
HMAC-SHA256 Webhook Signature Verification
Implements secure webhook delivery with signature verification.
"""
import hmac
import hashlib
import base64
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Standard webhook events."""
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    PROJECT_SHARED = "project.shared"
    
    # Model events
    MODEL_UPLOADED = "model.uploaded"
    MODEL_CONVERTED = "model.converted"
    MODEL_UPDATED = "model.updated"
    MODEL_DELETED = "model.deleted"
    
    # VDC events
    CLASH_DETECTED = "vdc.clash_detected"
    CLASH_RESOLVED = "vdc.clash_resolved"
    SCHEDULE_UPDATED = "vdc.schedule_updated"
    COST_UPDATED = "vdc.cost_updated"
    
    # User events
    USER_INVITED = "user.invited"
    USER_JOINED = "user.joined"
    USER_LEFT = "user.left"
    
    # System events
    EXPORT_COMPLETED = "export.completed"
    ANALYSIS_COMPLETED = "analysis.completed"
    BACKUP_COMPLETED = "backup.completed"


@dataclass
class WebhookEndpoint:
    """Represents a webhook endpoint configuration."""
    id: str
    tenant_id: str
    url: str
    secret: str
    events: List[WebhookEvent]
    is_active: bool = True
    created_at: datetime = None
    last_delivered_at: Optional[datetime] = None
    delivery_attempts: int = 0
    failed_attempts: int = 0
    headers: Dict[str, str] = None
    retry_policy: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.headers is None:
            self.headers = {}
        if self.retry_policy is None:
            self.retry_policy = {
                'max_retries': 3,
                'backoff_seconds': [1, 5, 25],
                'timeout_seconds': 30
            }


@dataclass
class WebhookDelivery:
    """Represents a webhook delivery attempt."""
    id: str
    endpoint_id: str
    event: WebhookEvent
    payload: Dict[str, Any]
    signature: str
    timestamp: datetime
    status: str  # 'pending', 'delivered', 'failed'
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    attempt_number: int = 1
    error_message: Optional[str] = None


class WebhookSignature:
    """HMAC-SHA256 webhook signature utilities."""
    
    SIGNATURE_VERSION = "v1"
    TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes
    
    @classmethod
    def generate_secret(cls) -> str:
        """Generate a new webhook secret."""
        return "whsec_" + secrets.token_urlsafe(32)
    
    @classmethod
    def sign_payload(cls, payload: Dict[str, Any], secret: str,
                     timestamp: Optional[int] = None) -> str:
        """Sign a webhook payload using HMAC-SHA256."""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create signed payload
        signed_payload = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        
        # Create signature base string
        signature_base = f"{timestamp}.{signed_payload}"
        
        # Generate HMAC
        secret_bytes = secret.encode('utf-8')
        signature = hmac.new(
            secret_bytes,
            signature_base.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"t={timestamp},{cls.SIGNATURE_VERSION}={signature}"
    
    @classmethod
    def verify_signature(cls, payload: Dict[str, Any], signature_header: str,
                         secret: str) -> bool:
        """Verify a webhook signature."""
        try:
            # Parse signature header
            timestamp, signature = cls._parse_signature_header(signature_header)
            
            # Verify timestamp (prevent replay attacks)
            current_time = int(time.time())
            if abs(current_time - timestamp) > cls.TIMESTAMP_TOLERANCE_SECONDS:
                logger.warning(f"Webhook timestamp too old: {timestamp}")
                return False
            
            # Recreate signature
            expected_signature = cls.sign_payload(payload, secret, timestamp)
            _, expected_sig = cls._parse_signature_header(expected_signature)
            
            # Constant-time comparison
            return hmac.compare_digest(signature, expected_sig)
        
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    @classmethod
    def _parse_signature_header(cls, header: str) -> tuple:
        """Parse signature header into timestamp and signature."""
        parts = header.split(',')
        
        timestamp = None
        signature = None
        
        for part in parts:
            if part.startswith('t='):
                timestamp = int(part[2:])
            elif part.startswith(f"{cls.SIGNATURE_VERSION}="):
                signature = part[len(cls.SIGNATURE_VERSION) + 1:]
        
        if timestamp is None or signature is None:
            raise ValueError("Invalid signature header format")
        
        return timestamp, signature


class WebhookManager:
    """Manages webhook endpoints and deliveries."""
    
    def __init__(self, storage_backend=None, http_client=None):
        self.storage = storage_backend
        self.http_client = http_client
        self.signature = WebhookSignature()
    
    def register_endpoint(self, tenant_id: str, url: str, 
                         events: List[WebhookEvent],
                         headers: Optional[Dict[str, str]] = None,
                         retry_policy: Optional[Dict[str, Any]] = None) -> WebhookEndpoint:
        """Register a new webhook endpoint."""
        endpoint = WebhookEndpoint(
            id=secrets.token_hex(16),
            tenant_id=tenant_id,
            url=url,
            secret=self.signature.generate_secret(),
            events=events,
            headers=headers or {},
            retry_policy=retry_policy
        )
        
        if self.storage:
            self.storage.store_endpoint(endpoint)
        
        logger.info(f"Registered webhook endpoint {endpoint.id} for tenant {tenant_id}")
        return endpoint
    
    def unregister_endpoint(self, endpoint_id: str) -> bool:
        """Unregister a webhook endpoint."""
        if self.storage:
            return self.storage.delete_endpoint(endpoint_id)
        return False
    
    def send_webhook(self, endpoint: WebhookEndpoint, event: WebhookEvent,
                     data: Dict[str, Any]) -> WebhookDelivery:
        """Send a webhook to an endpoint."""
        # Build payload
        payload = {
            'id': secrets.token_hex(16),
            'event': event.value,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        # Sign payload
        signature = self.signature.sign_payload(payload, endpoint.secret)
        
        # Create delivery record
        delivery = WebhookDelivery(
            id=secrets.token_hex(16),
            endpoint_id=endpoint.id,
            event=event,
            payload=payload,
            signature=signature,
            timestamp=datetime.utcnow(),
            status='pending'
        )
        
        # Send webhook
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-ID': delivery.id,
            'X-Webhook-Event': event.value,
            'User-Agent': 'Cerebrum-Webhook/1.0'
        }
        headers.update(endpoint.headers)
        
        try:
            if self.http_client:
                response = self.http_client.post(
                    endpoint.url,
                    json=payload,
                    headers=headers,
                    timeout=endpoint.retry_policy.get('timeout_seconds', 30)
                )
                
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:1000]  # Limit response size
                
                if 200 <= response.status_code < 300:
                    delivery.status = 'delivered'
                    endpoint.last_delivered_at = datetime.utcnow()
                else:
                    delivery.status = 'failed'
                    delivery.error_message = f"HTTP {response.status_code}"
            else:
                delivery.status = 'failed'
                delivery.error_message = "No HTTP client configured"
        
        except Exception as e:
            delivery.status = 'failed'
            delivery.error_message = str(e)
        
        # Update stats
        endpoint.delivery_attempts += 1
        if delivery.status == 'failed':
            endpoint.failed_attempts += 1
        
        # Store delivery
        if self.storage:
            self.storage.store_delivery(delivery)
            self.storage.update_endpoint(endpoint)
        
        return delivery
    
    def retry_failed_deliveries(self, max_age_hours: int = 24) -> List[WebhookDelivery]:
        """Retry failed webhook deliveries."""
        if not self.storage:
            return []
        
        failed = self.storage.get_failed_deliveries(max_age_hours)
        retried = []
        
        for delivery in failed:
            endpoint = self.storage.get_endpoint(delivery.endpoint_id)
            if not endpoint or not endpoint.is_active:
                continue
            
            max_retries = endpoint.retry_policy.get('max_retries', 3)
            if delivery.attempt_number >= max_retries:
                continue
            
            delivery.attempt_number += 1
            delivery.timestamp = datetime.utcnow()
            delivery.status = 'pending'
            
            # Retry with exponential backoff
            retry_result = self.send_webhook(endpoint, delivery.event, delivery.payload['data'])
            retried.append(retry_result)
        
        return retried
    
    def verify_incoming_webhook(self, payload: Dict[str, Any], 
                                 signature_header: str,
                                 secret: str) -> bool:
        """Verify an incoming webhook signature."""
        return self.signature.verify_signature(payload, signature_header, secret)


class WebhookMiddleware:
    """Middleware for webhook signature verification."""
    
    def __init__(self, get_response=None):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is a webhook endpoint
        if request.path.startswith('/webhooks/'):
            signature = request.headers.get('X-Webhook-Signature')
            if not signature:
                return self._error_response("Missing signature", 401)
            
            # Get endpoint secret (implementation depends on your storage)
            endpoint_id = request.path.split('/')[-1]
            secret = self._get_endpoint_secret(endpoint_id)
            
            if not secret:
                return self._error_response("Invalid endpoint", 404)
            
            # Verify signature
            try:
                payload = json.loads(request.body)
                if not WebhookSignature.verify_signature(payload, signature, secret):
                    return self._error_response("Invalid signature", 401)
            except json.JSONDecodeError:
                return self._error_response("Invalid payload", 400)
        
        return self.get_response(request)
    
    def _get_endpoint_secret(self, endpoint_id: str) -> Optional[str]:
        """Get secret for endpoint (implement based on your storage)."""
        # This would typically query your database
        return None
    
    def _error_response(self, message: str, status: int):
        """Return error response."""
        from django.http import JsonResponse
        return JsonResponse({'error': message}, status=status)
