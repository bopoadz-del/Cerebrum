"""
Granular API Key Permissions with Scopes
Implements OAuth2-style scoped API keys for fine-grained access control.
"""
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, List, Set, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class Scope(str, Enum):
    """Standard API scopes."""
    # Read scopes
    READ_PROJECTS = "projects:read"
    READ_MODELS = "models:read"
    READ_DOCUMENTS = "documents:read"
    READ_USERS = "users:read"
    READ_ANALYTICS = "analytics:read"
    READ_VDC = "vdc:read"
    
    # Write scopes
    WRITE_PROJECTS = "projects:write"
    WRITE_MODELS = "models:write"
    WRITE_DOCUMENTS = "documents:write"
    WRITE_USERS = "users:write"
    WRITE_VDC = "vdc:write"
    
    # Admin scopes
    ADMIN_ALL = "admin:*"
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_BILLING = "admin:billing"
    
    # Webhook scopes
    WEBHOOK_READ = "webhooks:read"
    WEBHOOK_WRITE = "webhooks:write"
    
    # Special scopes
    CLASH_DETECTION = "vdc:clash"
    COST_5D = "vdc:cost"
    SCHEDULE_4D = "vdc:schedule"
    EXPORT_BCF = "vdc:export:bcf"
    EXPORT_COBIE = "vdc:export:cobie"


class Permission(str, Enum):
    """Granular permissions within scopes."""
    # Project permissions
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_SHARE = "project:share"
    
    # Model permissions
    MODEL_UPLOAD = "model:upload"
    MODEL_DOWNLOAD = "model:download"
    MODEL_CONVERT = "model:convert"
    MODEL_DELETE = "model:delete"
    
    # User permissions
    USER_INVITE = "user:invite"
    USER_MANAGE = "user:manage"
    USER_DELETE = "user:delete"


@dataclass
class APIKeyScope:
    """Represents a scoped permission."""
    scope: Scope
    permissions: List[Permission] = field(default_factory=list)
    resource_ids: Optional[List[str]] = None  # Limit to specific resources
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIKey:
    """API Key with scoped permissions."""
    id: str
    key_prefix: str
    hashed_key: str
    name: str
    tenant_id: str
    created_by: str
    scopes: List[APIKeyScope]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    rate_limit: int = 1000  # requests per hour
    ip_whitelist: Optional[List[str]] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_scope(self, scope: Scope) -> bool:
        """Check if key has a specific scope."""
        if Scope.ADMIN_ALL in [s.scope for s in self.scopes]:
            return True
        return any(s.scope == scope for s in self.scopes)
    
    def has_permission(self, scope: Scope, permission: Permission) -> bool:
        """Check if key has a specific permission within a scope."""
        if Scope.ADMIN_ALL in [s.scope for s in self.scopes]:
            return True
        
        for key_scope in self.scopes:
            if key_scope.scope == scope:
                if not key_scope.permissions or permission in key_scope.permissions:
                    return True
        return False
    
    def can_access_resource(self, scope: Scope, resource_id: str) -> bool:
        """Check if key can access a specific resource."""
        for key_scope in self.scopes:
            if key_scope.scope == scope:
                if key_scope.resource_ids is None:
                    return True
                if resource_id in key_scope.resource_ids:
                    return True
        return False
    
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)."""
        return {
            'id': self.id,
            'key_prefix': self.key_prefix,
            'name': self.name,
            'tenant_id': self.tenant_id,
            'scopes': [
                {
                    'scope': s.scope.value,
                    'permissions': [p.value for p in s.permissions],
                    'resource_ids': s.resource_ids
                }
                for s in self.scopes
            ],
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'rate_limit': self.rate_limit,
            'is_active': self.is_active
        }


class APIKeyManager:
    """Manages API key lifecycle and validation."""
    
    KEY_PREFIX = "cbr_"
    KEY_LENGTH = 48
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend
        self._rate_limits: Dict[str, List[datetime]] = {}
    
    def generate_key(self, name: str, tenant_id: str, created_by: str,
                     scopes: List[APIKeyScope],
                     expires_days: Optional[int] = None,
                     rate_limit: int = 1000,
                     ip_whitelist: Optional[List[str]] = None) -> tuple:
        """Generate a new API key."""
        # Generate secure random key
        raw_key = self.KEY_PREFIX + secrets.token_urlsafe(self.KEY_LENGTH)
        key_id = secrets.token_hex(16)
        key_prefix = raw_key[:12]
        
        # Hash the key for storage
        hashed_key = self._hash_key(raw_key)
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        api_key = APIKey(
            id=key_id,
            key_prefix=key_prefix,
            hashed_key=hashed_key,
            name=name,
            tenant_id=tenant_id,
            created_by=created_by,
            scopes=scopes,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            rate_limit=rate_limit,
            ip_whitelist=ip_whitelist
        )
        
        # Store the key
        if self.storage:
            self.storage.store_key(api_key)
        
        logger.info(f"Generated API key {key_id} for tenant {tenant_id}")
        return raw_key, api_key
    
    def validate_key(self, raw_key: str, required_scope: Optional[Scope] = None,
                     client_ip: Optional[str] = None) -> Optional[APIKey]:
        """Validate an API key."""
        if not raw_key.startswith(self.KEY_PREFIX):
            return None
        
        hashed_key = self._hash_key(raw_key)
        
        # Retrieve key from storage
        if not self.storage:
            return None
        
        api_key = self.storage.get_key_by_hash(hashed_key)
        
        if not api_key:
            return None
        
        if not api_key.is_active:
            logger.warning(f"Attempt to use inactive key: {api_key.id}")
            return None
        
        if api_key.is_expired():
            logger.warning(f"Attempt to use expired key: {api_key.id}")
            return None
        
        # Check IP whitelist
        if api_key.ip_whitelist and client_ip:
            if not self._check_ip_whitelist(client_ip, api_key.ip_whitelist):
                logger.warning(f"IP {client_ip} not in whitelist for key: {api_key.id}")
                return None
        
        # Check scope
        if required_scope and not api_key.has_scope(required_scope):
            logger.warning(f"Key {api_key.id} lacks scope {required_scope}")
            return None
        
        # Check rate limit
        if not self._check_rate_limit(api_key):
            logger.warning(f"Rate limit exceeded for key: {api_key.id}")
            return None
        
        # Update last used
        api_key.last_used_at = datetime.utcnow()
        self.storage.update_key(api_key)
        
        return api_key
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if self.storage:
            return self.storage.revoke_key(key_id)
        return False
    
    def list_keys(self, tenant_id: str) -> List[APIKey]:
        """List all API keys for a tenant."""
        if self.storage:
            return self.storage.list_keys(tenant_id)
        return []
    
    def _hash_key(self, raw_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
    
    def _check_ip_whitelist(self, client_ip: str, whitelist: List[str]) -> bool:
        """Check if client IP matches whitelist patterns."""
        for pattern in whitelist:
            if self._ip_matches_pattern(client_ip, pattern):
                return True
        return False
    
    def _ip_matches_pattern(self, ip: str, pattern: str) -> bool:
        """Check if IP matches pattern (supports CIDR notation)."""
        if '/' in pattern:
            # CIDR notation
            import ipaddress
            try:
                network = ipaddress.ip_network(pattern, strict=False)
                return ipaddress.ip_address(ip) in network
            except ValueError:
                return False
        return ip == pattern
    
    def _check_rate_limit(self, api_key: APIKey) -> bool:
        """Check if request is within rate limit."""
        now = datetime.utcnow()
        window_start = now - timedelta(hours=1)
        
        # Get or initialize request history
        if api_key.id not in self._rate_limits:
            self._rate_limits[api_key.id] = []
        
        # Clean old requests
        self._rate_limits[api_key.id] = [
            t for t in self._rate_limits[api_key.id] if t > window_start
        ]
        
        # Check limit
        if len(self._rate_limits[api_key.id]) >= api_key.rate_limit:
            return False
        
        # Record request
        self._rate_limits[api_key.id].append(now)
        return True


def require_scope(scope: Scope):
    """Decorator to require a specific scope."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract API key from request (implementation depends on framework)
            api_key = kwargs.get('api_key') or getattr(args[0], 'api_key', None)
            
            if not api_key:
                raise PermissionError("API key required")
            
            if not api_key.has_scope(scope):
                raise PermissionError(f"Required scope: {scope.value}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(scope: Scope, permission: Permission):
    """Decorator to require a specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            api_key = kwargs.get('api_key') or getattr(args[0], 'api_key', None)
            
            if not api_key:
                raise PermissionError("API key required")
            
            if not api_key.has_permission(scope, permission):
                raise PermissionError(f"Required permission: {permission.value}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Predefined scope combinations
READ_ONLY_SCOPES = [
    Scope.READ_PROJECTS,
    Scope.READ_MODELS,
    Scope.READ_DOCUMENTS,
    Scope.READ_ANALYTICS,
    Scope.READ_VDC
]

WRITE_SCOPES = READ_ONLY_SCOPES + [
    Scope.WRITE_PROJECTS,
    Scope.WRITE_MODELS,
    Scope.WRITE_DOCUMENTS,
    Scope.WRITE_VDC
]

VDC_SCOPES = [
    Scope.READ_VDC,
    Scope.WRITE_VDC,
    Scope.CLASH_DETECTION,
    Scope.COST_5D,
    Scope.SCHEDULE_4D,
    Scope.EXPORT_BCF,
    Scope.EXPORT_COBIE
]

ADMIN_SCOPES = [Scope.ADMIN_ALL]
