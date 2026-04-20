"""
Authentication Audit Logging System

Comprehensive audit logging for authentication events with
tamper-evident hash chain integrity. Tracks login attempts, MFA usage,
role changes, permission grants, and API key usage.
"""

import uuid
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict, field
from contextvars import ContextVar

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit import AuditLog, audit_logger as base_audit_logger
from app.models.user import User

logger = get_logger(__name__)


class AuthEventType(str, Enum):
    """Authentication event types."""
    # Login events
    LOGIN_SUCCESS = "auth:login_success"
    LOGIN_FAILURE = "auth:login_failure"
    LOGIN_MFA_REQUIRED = "auth:login_mfa_required"
    LOGIN_MFA_SUCCESS = "auth:login_mfa_success"
    LOGIN_MFA_FAILURE = "auth:login_mfa_failure"
    LOGIN_BACKUP_CODE_USED = "auth:login_backup_code_used"
    
    # Logout events
    LOGOUT = "auth:logout"
    SESSION_EXPIRED = "auth:session_expired"
    SESSION_REVOKED = "auth:session_revoked"
    
    # MFA events
    MFA_ENABLED = "auth:mfa_enabled"
    MFA_DISABLED = "auth:mfa_disabled"
    MFA_SETUP_INITIATED = "auth:mfa_setup_initiated"
    MFA_BACKUP_CODES_REGENERATED = "auth:mfa_backup_codes_regenerated"
    MFA_DEVICE_TRUSTED = "auth:mfa_device_trusted"
    
    # Password events
    PASSWORD_CHANGED = "auth:password_changed"
    PASSWORD_RESET_REQUESTED = "auth:password_reset_requested"
    PASSWORD_RESET_COMPLETED = "auth:password_reset_completed"
    PASSWORD_RESET_FAILED = "auth:password_reset_failed"
    
    # Role/Permission events
    ROLE_ASSIGNED = "auth:role_assigned"
    ROLE_REMOVED = "auth:role_removed"
    ROLE_CREATED = "auth:role_created"
    ROLE_UPDATED = "auth:role_updated"
    ROLE_DELETED = "auth:role_deleted"
    PERMISSION_GRANTED = "auth:permission_granted"
    PERMISSION_REVOKED = "auth:permission_revoked"
    
    # API Key events
    API_KEY_CREATED = "auth:api_key_created"
    API_KEY_REVOKED = "auth:api_key_revoked"
    API_KEY_USED = "auth:api_key_used"
    API_KEY_EXPIRED = "auth:api_key_expired"
    
    # Account events
    ACCOUNT_CREATED = "auth:account_created"
    ACCOUNT_ACTIVATED = "auth:account_activated"
    ACCOUNT_DEACTIVATED = "auth:account_deactivated"
    ACCOUNT_LOCKED = "auth:account_locked"
    ACCOUNT_UNLOCKED = "auth:account_unlocked"
    ACCOUNT_DELETED = "auth:account_deleted"
    
    # OAuth events
    OAUTH_LOGIN_SUCCESS = "auth:oauth_login_success"
    OAUTH_LOGIN_FAILURE = "auth:oauth_login_failure"
    OAUTH_TOKEN_REFRESHED = "auth:oauth_token_refreshed"
    OAUTH_UNLINKED = "auth:oauth_unlinked"
    
    # Security events
    SUSPICIOUS_ACTIVITY = "auth:suspicious_activity"
    BRUTE_FORCE_DETECTED = "auth:brute_force_detected"
    IP_BLOCKED = "auth:ip_blocked"
    IP_UNBLOCKED = "auth:ip_unblocked"
    DEVICE_BLOCKED = "auth:device_blocked"


@dataclass
class AuthEvent:
    """Authentication event data."""
    event_type: AuthEventType
    user_id: Optional[uuid.UUID]
    tenant_id: Optional[uuid.UUID]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        if self.user_id:
            data["user_id"] = str(self.user_id)
        if self.tenant_id:
            data["tenant_id"] = str(self.tenant_id)
        if self.timestamp:
            data["timestamp"] = self.timestamp.isoformat()
        return data


# Context variable for request context
request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("request_context", default=None)


class AuthAuditLogger:
    """
    Authentication Audit Logger.
    
    Specialized logging for auth events with detailed context tracking.
    """
    
    def __init__(self):
        self._sensitive_fields = {
            "password",
            "token",
            "secret",
            "mfa_code",
            "backup_code",
            "api_key",
            "refresh_token",
            "access_token",
            "hashed_password",
        }
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive data from event details.
        
        Args:
            details: Raw event details
            
        Returns:
            Sanitized details
        """
        sanitized = {}
        for key, value in details.items():
            # Check if field name contains sensitive keywords
            if any(sensitive in key.lower() for sensitive in self._sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized
    
    async def log_event(
        self,
        db: AsyncSession,
        event_type: AuthEventType,
        user_id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an authentication event.
        
        Args:
            db: Database session
            event_type: Type of auth event
            user_id: User ID
            tenant_id: Tenant ID
            details: Event details (will be sanitized)
            ip_address: Client IP
            user_agent: User agent
            session_id: Session ID
            request_id: Request ID
            
        Returns:
            Created audit log entry
        """
        # Get context from context var if not provided
        ctx = request_context.get()
        if ctx:
            ip_address = ip_address or ctx.get("ip_address")
            user_agent = user_agent or ctx.get("user_agent")
            request_id = request_id or ctx.get("request_id")
        
        # Sanitize details
        safe_details = self._sanitize_details(details or {})
        
        # Determine resource type from event type
        resource_type = self._get_resource_type(event_type)
        
        # Create audit log
        audit_entry = await base_audit_logger.log(
            db_session=db,
            action=event_type.value,
            resource_type=resource_type,
            resource_id=str(user_id) if user_id else None,
            user_id=user_id,
            tenant_id=tenant_id,
            details=safe_details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
        )
        
        # Also log to application logger for real-time monitoring
        log_level = "warning" if "failure" in event_type.value else "info"
        getattr(logger, log_level)(
            f"Auth event: {event_type.value}",
            event_type=event_type.value,
            user_id=str(user_id) if user_id else None,
            ip_address=ip_address,
        )
        
        return audit_entry
    
    def _get_resource_type(self, event_type: AuthEventType) -> str:
        """Get resource type from event type."""
        event_prefix = event_type.value.split(":")[1] if ":" in event_type.value else "auth"
        
        if "login" in event_prefix:
            return "session"
        elif "mfa" in event_prefix:
            return "mfa"
        elif "password" in event_prefix:
            return "password"
        elif "role" in event_prefix:
            return "role"
        elif "permission" in event_prefix:
            return "permission"
        elif "api_key" in event_prefix:
            return "api_key"
        elif "account" in event_prefix:
            return "account"
        elif "oauth" in event_prefix:
            return "oauth"
        elif "session" in event_prefix:
            return "session"
        else:
            return "auth"
    
    # Convenience methods for common events
    
    async def log_login_success(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
        mfa_used: bool = False,
        mfa_type: Optional[str] = None,
        **context
    ) -> AuditLog:
        """Log successful login."""
        details = {
            "mfa_used": mfa_used,
            "mfa_type": mfa_type,
            "auth_method": context.get("auth_method", "password"),
        }
        if context.get("device_fingerprint"):
            details["device_fingerprint"] = context["device_fingerprint"]
        
        return await self.log_event(
            db=db,
            event_type=AuthEventType.LOGIN_SUCCESS,
            user_id=user_id,
            tenant_id=tenant_id,
            details=details,
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            session_id=context.get("session_id"),
            request_id=context.get("request_id"),
        )
    
    async def log_login_failure(
        self,
        db: AsyncSession,
        email: str,
        reason: str,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log failed login attempt."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.LOGIN_FAILURE,
            tenant_id=tenant_id,
            details={
                "email": email,
                "reason": reason,
                "attempt_number": context.get("attempt_number", 1),
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_mfa_setup(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        mfa_type: str,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log MFA setup."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.MFA_SETUP_INITIATED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={"mfa_type": mfa_type},
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_mfa_enabled(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        mfa_type: str,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log MFA enabled."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.MFA_ENABLED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={"mfa_type": mfa_type},
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_mfa_disabled(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        reason: str,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log MFA disabled."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.MFA_DISABLED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={"reason": reason},
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_password_change(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        changed_by: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log password change."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.PASSWORD_CHANGED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={
                "self_service": changed_by is None or changed_by == user_id,
                "changed_by": str(changed_by) if changed_by else None,
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_role_assignment(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        role_name: str,
        assigned_by: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log role assignment."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.ROLE_ASSIGNED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={
                "role_id": str(role_id),
                "role_name": role_name,
                "assigned_by": str(assigned_by),
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_role_removal(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        role_name: str,
        removed_by: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log role removal."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.ROLE_REMOVED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={
                "role_id": str(role_id),
                "role_name": role_name,
                "removed_by": str(removed_by),
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_api_key_created(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        key_id: uuid.UUID,
        key_name: str,
        scopes: List[str],
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log API key creation."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.API_KEY_CREATED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={
                "key_id": str(key_id),
                "key_name": key_name,
                "scopes": scopes,
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_api_key_revoked(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        key_id: uuid.UUID,
        key_name: str,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log API key revocation."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.API_KEY_REVOKED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={
                "key_id": str(key_id),
                "key_name": key_name,
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_api_key_usage(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        key_id: uuid.UUID,
        endpoint: str,
        method: str,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log API key usage."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.API_KEY_USED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={
                "key_id": str(key_id),
                "endpoint": endpoint,
                "method": method,
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_account_locked(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        reason: str,
        locked_until: datetime,
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log account lockout."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.ACCOUNT_LOCKED,
            user_id=user_id,
            tenant_id=tenant_id,
            details={
                "reason": reason,
                "locked_until": locked_until.isoformat(),
                "failed_attempts": context.get("failed_attempts", 0),
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def log_suspicious_activity(
        self,
        db: AsyncSession,
        user_id: Optional[uuid.UUID],
        activity_type: str,
        severity: str,
        details: Dict[str, Any],
        tenant_id: Optional[uuid.UUID] = None,
        **context
    ) -> AuditLog:
        """Log suspicious activity."""
        return await self.log_event(
            db=db,
            event_type=AuthEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            tenant_id=tenant_id,
            details={
                "activity_type": activity_type,
                "severity": severity,
                **details,
            },
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            request_id=context.get("request_id"),
        )
    
    async def search_auth_events(
        self,
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        event_types: Optional[List[AuthEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Search authentication events.
        
        Args:
            db: Database session
            user_id: Filter by user ID
            event_types: Filter by event types
            start_time: Filter by start time
            end_time: Filter by end time
            ip_address: Filter by IP address
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of audit log entries
        """
        query = select(AuditLog).where(
            AuditLog.action.like("auth:%")
        )
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        
        if event_types:
            event_values = [e.value for e in event_types]
            query = query.where(AuditLog.action.in_(event_values))
        
        if start_time:
            query = query.where(AuditLog.timestamp >= start_time)
        
        if end_time:
            query = query.where(AuditLog.timestamp <= end_time)
        
        if ip_address:
            query = query.where(AuditLog.ip_address == ip_address)
        
        query = query.order_by(AuditLog.timestamp.desc())
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_user_login_history(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
    ) -> List[AuditLog]:
        """
        Get login history for a user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum results
            
        Returns:
            List of login-related audit entries
        """
        login_events = [
            AuthEventType.LOGIN_SUCCESS,
            AuthEventType.LOGIN_FAILURE,
            AuthEventType.LOGIN_MFA_SUCCESS,
            AuthEventType.LOGIN_MFA_FAILURE,
        ]
        
        return await self.search_auth_events(
            db=db,
            user_id=user_id,
            event_types=login_events,
            limit=limit,
        )
    
    async def get_security_summary(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get security summary for a user.
        
        Args:
            db: Database session
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Security summary dictionary
        """
        from datetime import timedelta
        
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Get all auth events
        events = await self.search_auth_events(
            db=db,
            user_id=user_id,
            start_time=start_time,
            limit=1000,
        )
        
        # Analyze
        summary = {
            "period_days": days,
            "total_events": len(events),
            "successful_logins": 0,
            "failed_logins": 0,
            "mfa_attempts": 0,
            "password_changes": 0,
            "unique_ips": set(),
            "suspicious_events": 0,
        }
        
        for event in events:
            if event.action == AuthEventType.LOGIN_SUCCESS.value:
                summary["successful_logins"] += 1
            elif event.action == AuthEventType.LOGIN_FAILURE.value:
                summary["failed_logins"] += 1
            elif "mfa" in event.action:
                summary["mfa_attempts"] += 1
            elif event.action == AuthEventType.PASSWORD_CHANGED.value:
                summary["password_changes"] += 1
            elif event.action == AuthEventType.SUSPICIOUS_ACTIVITY.value:
                summary["suspicious_events"] += 1
            
            if event.ip_address:
                summary["unique_ips"].add(event.ip_address)
        
        summary["unique_ips"] = list(summary["unique_ips"])
        
        return summary


# Global auth audit logger instance
auth_audit = AuthAuditLogger()


def set_request_context(
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Set request context for audit logging.
    
    Args:
        ip_address: Client IP address
        user_agent: User agent string
        request_id: Request correlation ID
        session_id: Session ID
    """
    request_context.set({
        "ip_address": ip_address,
        "user_agent": user_agent,
        "request_id": request_id,
        "session_id": session_id,
    })


def clear_request_context() -> None:
    """Clear request context."""
    request_context.set(None)
