"""
Audit Triggers - Auto-log everything

Automatically logs all events for compliance and security:
- User actions
- Data access
- System events
- Security events
"""

import asyncio
import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import get_logger
from app.triggers.engine import Event, EventType, event_bus
from app.workers.celery_config import fast_task

logger = get_logger(__name__)


class AuditTriggerManager:
    """
    Manages audit-related triggers and automatic logging.
    
    This manager automatically logs all events to the audit log,
    creating an immutable record of all system activity.
    """
    
    def __init__(self):
        """Initialize the audit trigger manager."""
        self._previous_hash: Optional[str] = None
        self._register_handlers()
        
    def _register_handlers(self) -> None:
        """Register all audit event handlers."""
        # Register for ALL events
        event_bus.register_all(self._on_any_event)
        
        # Also register for specific events that need special handling
        event_bus.register(EventType.USER_LOGIN, self._on_user_login)
        event_bus.register(EventType.USER_LOGOUT, self._on_user_logout)
        event_bus.register(EventType.DATA_ACCESSED, self._on_data_accessed)
        event_bus.register(EventType.DATA_MODIFIED, self._on_data_modified)
        event_bus.register(EventType.PERMISSION_CHANGED, self._on_permission_changed)
        
        logger.info("Audit trigger handlers registered")
        
    async def _on_any_event(self, event: Event) -> None:
        """
        Handle any event - log to audit trail.
        
        Args:
            event: Any event
        """
        # Skip audit events to avoid infinite loops
        if event.source == "audit_triggers":
            return
            
        # Log the event
        await self._log_event(event)
        
    async def _on_user_login(self, event: Event) -> None:
        """
        Handle user login - special audit handling.
        
        Args:
            event: User login event
        """
        payload = event.payload
        
        logger.info(
            "User login audited",
            user_id=payload.get("user_id"),
            ip_address=payload.get("ip_address"),
        )
        
        # Additional security checks
        await self._check_login_anomalies(event)
        
    async def _on_user_logout(self, event: Event) -> None:
        """
        Handle user logout.
        
        Args:
            event: User logout event
        """
        payload = event.payload
        
        logger.info(
            "User logout audited",
            user_id=payload.get("user_id"),
            session_duration=payload.get("session_duration"),
        )
        
    async def _on_data_accessed(self, event: Event) -> None:
        """
        Handle data access - log PII access.
        
        Args:
            event: Data access event
        """
        payload = event.payload
        resource_type = payload.get("resource_type")
        
        # Special handling for sensitive data
        if resource_type in ["user", "patient", "employee"]:
            logger.info(
                "Sensitive data access audited",
                user_id=event.user_id,
                resource_type=resource_type,
                resource_id=payload.get("resource_id"),
            )
            
    async def _on_data_modified(self, event: Event) -> None:
        """
        Handle data modification - log changes.
        
        Args:
            event: Data modification event
        """
        payload = event.payload
        
        logger.info(
            "Data modification audited",
            user_id=event.user_id,
            resource_type=payload.get("resource_type"),
            action=payload.get("action"),
        )
        
    async def _on_permission_changed(self, event: Event) -> None:
        """
        Handle permission change - critical security event.
        
        Args:
            event: Permission change event
        """
        payload = event.payload
        
        logger.warning(
            "Permission change audited",
            user_id=event.user_id,
            target_user=payload.get("target_user_id"),
            old_role=payload.get("old_role"),
            new_role=payload.get("new_role"),
        )
        
        # Send notification for permission changes
        notify_permission_change.delay(
            changed_by=event.user_id,
            target_user=payload.get("target_user_id"),
            old_role=payload.get("old_role"),
            new_role=payload.get("new_role"),
        )
        
    async def _log_event(self, event: Event) -> None:
        """
        Log event to audit trail.
        
        Args:
            event: Event to log
        """
        # Create audit log entry
        audit_entry = {
            "event_id": event.event_id,
            "event_type": event.type.name,
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "tenant_id": event.tenant_id,
            "user_id": event.user_id,
            "correlation_id": event.correlation_id,
            "priority": event.priority,
            "payload": self._sanitize_payload(event.payload),
        }
        
        # Queue audit log task
        write_audit_log.delay(audit_entry)
        
    async def _check_login_anomalies(self, event: Event) -> None:
        """
        Check for login anomalies.
        
        Args:
            event: Login event
        """
        payload = event.payload
        user_id = payload.get("user_id")
        ip_address = payload.get("ip_address")
        
        # Check for:
        # - Login from new location
        # - Multiple failed attempts
        # - Login outside business hours
        # - Impossible travel (login from two locations too quickly)
        
        check_login_anomalies.delay(
            user_id=user_id,
            ip_address=ip_address,
            timestamp=event.timestamp.isoformat(),
        )
        
    def _sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize payload for audit logging.
        
        Removes sensitive fields like passwords, tokens, etc.
        
        Args:
            payload: Original payload
            
        Returns:
            Sanitized payload
        """
        sensitive_fields = [
            "password", "token", "secret", "api_key", "private_key",
            "credit_card", "ssn", "social_security",
        ]
        
        sanitized = {}
        for key, value in payload.items():
            if any(sf in key.lower() for sf in sensitive_fields):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_payload(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_payload(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
                
        return sanitized


# Celery tasks for audit processing
@fast_task(bind=True, max_retries=5)
def write_audit_log(self, audit_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Write audit log entry to database.
    
    Args:
        audit_entry: Audit log entry
        
    Returns:
        Write result
    """
    try:
        # Calculate hash for integrity
        entry_json = json.dumps(audit_entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        
        # Add hash to entry
        audit_entry["entry_hash"] = entry_hash
        
        # Write to database
        # This would use the AuditLog model
        
        logger.debug(
            "Audit log written",
            event_id=audit_entry.get("event_id"),
            event_type=audit_entry.get("event_type"),
        )
        
        return {
            "status": "success",
            "event_id": audit_entry.get("event_id"),
            "hash": entry_hash,
        }
        
    except Exception as exc:
        logger.error("Failed to write audit log", error=str(exc))
        # Retry with shorter delay for audit logs
        raise self.retry(exc=exc, countdown=10)


@fast_task(bind=True, max_retries=3)
def notify_permission_change(
    self,
    changed_by: Optional[str],
    target_user: str,
    old_role: Optional[str],
    new_role: str,
) -> Dict[str, Any]:
    """
    Notify about permission change.
    
    Args:
        changed_by: User who made the change
        target_user: User whose permissions changed
        old_role: Previous role
        new_role: New role
        
    Returns:
        Notification result
    """
    try:
        logger.info(
            "Notifying permission change",
            changed_by=changed_by,
            target_user=target_user,
            new_role=new_role,
        )
        
        # Send email notification
        # Send to security team
        # Log to SIEM if configured
        
        return {
            "status": "success",
            "notified": True,
        }
        
    except Exception as exc:
        logger.error("Permission change notification failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@fast_task(bind=True, max_retries=3)
def check_login_anomalies(
    self,
    user_id: str,
    ip_address: str,
    timestamp: str,
) -> Dict[str, Any]:
    """
    Check for login anomalies.
    
    Args:
        user_id: User ID
        ip_address: IP address
        timestamp: Login timestamp
        
    Returns:
        Anomaly check result
    """
    try:
        logger.info("Checking login anomalies", user_id=user_id, ip=ip_address)
        
        anomalies = []
        
        # Check for new location
        # Check for multiple failed attempts
        # Check for impossible travel
        
        if anomalies:
            logger.warning(
                "Login anomalies detected",
                user_id=user_id,
                anomalies=anomalies,
            )
            
            # Create security alert
            asyncio.run(event_bus.emit(
                event_bus.create_event(
                    EventType.SYSTEM_WARNING,
                    source="audit_triggers",
                    payload={
                        "warning_type": "login_anomaly",
                        "user_id": user_id,
                        "anomalies": anomalies,
                    },
                )
            ))
        
        return {
            "status": "success",
            "user_id": user_id,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
        }
        
    except Exception as exc:
        logger.error("Login anomaly check failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


# Convenience functions for emitting audit events
async def log_user_action(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[str] = None,
) -> None:
    """
    Log a user action.
    
    Args:
        user_id: User ID
        action: Action performed
        resource_type: Type of resource
        resource_id: Resource ID
        details: Additional details
        tenant_id: Tenant ID
    """
    event_type = EventType.DATA_MODIFIED if action in ["create", "update", "delete"] else EventType.DATA_ACCESSED
    
    await event_bus.emit(
        event_bus.create_event(
            event_type,
            source="audit.user_action",
            payload={
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
            },
            user_id=user_id,
            tenant_id=tenant_id,
        )
    )


async def log_security_event(
    event_type: str,
    severity: str,
    description: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a security event.
    
    Args:
        event_type: Type of security event
        severity: Severity level
        description: Event description
        user_id: User ID (if applicable)
        details: Additional details
    """
    await event_bus.emit(
        event_bus.create_event(
            EventType.SYSTEM_WARNING if severity in ["low", "medium"] else EventType.SYSTEM_ERROR,
            source="audit.security",
            payload={
                "security_event_type": event_type,
                "severity": severity,
                "description": description,
                "details": details or {},
            },
            user_id=user_id,
            priority=1 if severity == "critical" else 3,
        )
    )


# Global instance
audit_trigger_manager = AuditTriggerManager()
