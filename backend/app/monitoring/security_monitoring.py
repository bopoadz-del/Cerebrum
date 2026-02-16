"""
Security Monitoring System
SIEM, WAF, IDS integration for Cerebrum AI Platform
"""

import json
import re
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Types of security events"""
    # Authentication events
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILURE = 'login_failure'
    LOGOUT = 'logout'
    PASSWORD_CHANGE = 'password_change'
    MFA_ENABLED = 'mfa_enabled'
    MFA_DISABLED = 'mfa_disabled'
    
    # Access control events
    UNAUTHORIZED_ACCESS = 'unauthorized_access'
    PRIVILEGE_ESCALATION = 'privilege_escalation'
    PERMISSION_DENIED = 'permission_denied'
    
    # Threat detection
    SUSPICIOUS_ACTIVITY = 'suspicious_activity'
    BRUTE_FORCE_ATTEMPT = 'brute_force_attempt'
    SQL_INJECTION_ATTEMPT = 'sql_injection_attempt'
    XSS_ATTEMPT = 'xss_attempt'
    CSRF_ATTEMPT = 'csrf_attempt'
    RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded'
    
    # Data security
    DATA_EXPORT = 'data_export'
    BULK_DOWNLOAD = 'bulk_download'
    SENSITIVE_DATA_ACCESS = 'sensitive_data_access'
    
    # System security
    CONFIGURATION_CHANGE = 'configuration_change'
    API_KEY_CREATED = 'api_key_created'
    API_KEY_REVOKED = 'api_key_revoked'


class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SecurityEvent:
    """Security event record"""
    id: str
    timestamp: datetime
    event_type: SecurityEventType
    threat_level: ThreatLevel
    source_ip: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['threat_level'] = self.threat_level.value
        data['timestamp'] = self.timestamp.isoformat()
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data


class SIEMIntegration:
    """Security Information and Event Management integration"""
    
    def __init__(self):
        self.splunk_url = settings.SPLUNK_URL
        self.splunk_token = settings.SPLUNK_HEC_TOKEN
        self.sentinel_workspace_id = settings.AZURE_SENTINEL_WORKSPACE_ID
        self.sentinel_key = settings.AZURE_SENTINEL_KEY
    
    async def send_event(self, event: SecurityEvent):
        """Send security event to SIEM"""
        # Send to Splunk
        if self.splunk_url and self.splunk_token:
            await self._send_to_splunk(event)
        
        # Send to Azure Sentinel
        if self.sentinel_workspace_id and self.sentinel_key:
            await self._send_to_sentinel(event)
    
    async def _send_to_splunk(self, event: SecurityEvent):
        """Send event to Splunk HTTP Event Collector"""
        try:
            payload = {
                'time': event.timestamp.timestamp(),
                'source': 'cerebrum-security',
                'sourcetype': 'cerebrum:security',
                'event': event.to_dict()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'{self.splunk_url}/services/collector/event',
                    headers={'Authorization': f'Splunk {self.splunk_token}'},
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send to Splunk: {e}")
    
    async def _send_to_sentinel(self, event: SecurityEvent):
        """Send event to Azure Sentinel"""
        try:
            from azure.loganalytics.models import QueryBody
            
            # This would use Azure Log Analytics API
            pass
            
        except Exception as e:
            logger.error(f"Failed to send to Sentinel: {e}")


class WAFMonitor:
    """Web Application Firewall monitoring"""
    
    def __init__(self):
        self.blocked_ips: Set[str] = set()
        self.blocked_countries: Set[str] = set()
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.rules: List[Dict[str, Any]] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default WAF rules"""
        self.rules = [
            {
                'id': 'sql-injection',
                'name': 'SQL Injection Detection',
                'pattern': r"(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(from|into|table|database)\b)|(--|#|\/\*)",
                'action': 'block',
                'severity': 'high'
            },
            {
                'id': 'xss-detection',
                'name': 'XSS Detection',
                'pattern': r"(<script|javascript:|on\w+\s*=|<iframe|<object|<embed)",
                'action': 'block',
                'severity': 'high'
            },
            {
                'id': 'path-traversal',
                'name': 'Path Traversal',
                'pattern': r"\.\.(\/|\\|%2f|%5c)",
                'action': 'block',
                'severity': 'medium'
            },
            {
                'id': 'bot-detection',
                'name': 'Bot Detection',
                'pattern': r"(bot|crawler|spider|scraper)",
                'action': 'challenge',
                'severity': 'low'
            }
        ]
    
    def analyze_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: str = None,
        client_ip: str = None
    ) -> Dict[str, Any]:
        """Analyze request for threats"""
        violations = []
        
        # Check IP blocklist
        if client_ip and client_ip in self.blocked_ips:
            violations.append({
                'rule_id': 'ip-blocklist',
                'severity': 'critical',
                'message': 'IP address is blocked'
            })
        
        # Check rate limits
        if client_ip:
            rate_violation = self._check_rate_limit(client_ip)
            if rate_violation:
                violations.append(rate_violation)
        
        # Check WAF rules
        request_string = f"{method} {path} {json.dumps(headers)} {body or ''}"
        
        for rule in self.rules:
            if re.search(rule['pattern'], request_string, re.IGNORECASE):
                violations.append({
                    'rule_id': rule['id'],
                    'rule_name': rule['name'],
                    'severity': rule['severity'],
                    'action': rule['action']
                })
        
        return {
            'blocked': len(violations) > 0 and any(
                v.get('action') == 'block' or v.get('severity') == 'critical'
                for v in violations
            ),
            'violations': violations
        }
    
    def _check_rate_limit(self, client_ip: str) -> Optional[Dict[str, Any]]:
        """Check if client has exceeded rate limit"""
        now = datetime.utcnow()
        
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = {
                'count': 1,
                'window_start': now
            }
            return None
        
        limit_data = self.rate_limits[client_ip]
        
        # Reset window if expired (1 minute)
        if (now - limit_data['window_start']).total_seconds() > 60:
            limit_data['count'] = 1
            limit_data['window_start'] = now
            return None
        
        limit_data['count'] += 1
        
        # Check if limit exceeded (100 requests per minute)
        if limit_data['count'] > 100:
            return {
                'rule_id': 'rate-limit',
                'severity': 'medium',
                'message': f'Rate limit exceeded: {limit_data["count"]} requests/min',
                'action': 'block'
            }
        
        return None
    
    def block_ip(self, ip: str, duration_minutes: int = 60):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        logger.warning(f"Blocked IP: {ip} for {duration_minutes} minutes")
    
    def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip)
        logger.info(f"Unblocked IP: {ip}")


class IDSMonitor:
    """Intrusion Detection System monitoring"""
    
    def __init__(self):
        self.signatures: List[Dict[str, Any]] = []
        self.anomaly_baselines: Dict[str, Dict[str, Any]] = {}
        self._load_signatures()
    
    def _load_signatures(self):
        """Load IDS signatures"""
        self.signatures = [
            {
                'id': 'SIG-001',
                'name': 'Multiple Failed Logins',
                'description': 'Detects multiple failed login attempts',
                'event_type': SecurityEventType.BRUTE_FORCE_ATTEMPT,
                'threshold': 5,
                'window_minutes': 5,
                'severity': ThreatLevel.HIGH
            },
            {
                'id': 'SIG-002',
                'name': 'Privilege Escalation Attempt',
                'description': 'Detects attempts to escalate privileges',
                'event_type': SecurityEventType.PRIVILEGE_ESCALATION,
                'severity': ThreatLevel.CRITICAL
            },
            {
                'id': 'SIG-003',
                'name': 'Unusual Data Access Pattern',
                'description': 'Detects unusual data access patterns',
                'event_type': SecurityEventType.SUSPICIOUS_ACTIVITY,
                'severity': ThreatLevel.MEDIUM
            },
            {
                'id': 'SIG-004',
                'name': 'Off-Hours Admin Activity',
                'description': 'Detects administrative activity outside business hours',
                'event_type': SecurityEventType.SUSPICIOUS_ACTIVITY,
                'severity': ThreatLevel.LOW
            }
        ]
    
    def detect_intrusion(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect potential intrusions"""
        alerts = []
        
        for signature in self.signatures:
            if self._match_signature(signature, event_data):
                alerts.append({
                    'signature_id': signature['id'],
                    'signature_name': signature['name'],
                    'severity': signature['severity'].value,
                    'event_type': signature['event_type'].value,
                    'description': signature['description']
                })
        
        # Check for anomalies
        anomaly = self._detect_anomaly(event_data)
        if anomaly:
            alerts.append(anomaly)
        
        return alerts
    
    def _match_signature(self, signature: Dict[str, Any], 
                         event_data: Dict[str, Any]) -> bool:
        """Check if event matches signature"""
        # This would implement signature matching logic
        return False
    
    def _detect_anomaly(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect anomalous behavior"""
        # This would implement anomaly detection
        return None


class SecurityMonitor:
    """Central security monitoring system"""
    
    def __init__(self):
        self.events: List[SecurityEvent] = []
        self.max_events = 10000
        self.siem = SIEMIntegration()
        self.waf = WAFMonitor()
        self.ids = IDSMonitor()
        self.alert_handlers: List[callable] = []
    
    async def log_event(
        self,
        event_type: SecurityEventType,
        threat_level: ThreatLevel,
        source_ip: str,
        description: str,
        user_id: str = None,
        tenant_id: str = None,
        details: Dict[str, Any] = None
    ) -> SecurityEvent:
        """Log a security event"""
        event_id = hashlib.md5(
            f"{event_type.value}:{source_ip}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        event = SecurityEvent(
            id=event_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            threat_level=threat_level,
            source_ip=source_ip,
            user_id=user_id,
            tenant_id=tenant_id,
            description=description,
            details=details or {}
        )
        
        self.events.append(event)
        
        # Trim old events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Send to SIEM
        await self.siem.send_event(event)
        
        # Trigger alerts for high/critical events
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            await self._trigger_alert(event)
        
        return event
    
    async def _trigger_alert(self, event: SecurityEvent):
        """Trigger security alert"""
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in security alert handler: {e}")
    
    def on_alert(self, handler: callable):
        """Register alert handler"""
        self.alert_handlers.append(handler)
    
    def get_events(
        self,
        event_type: SecurityEventType = None,
        threat_level: ThreatLevel = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get security events with filtering"""
        filtered = self.events
        
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        
        if threat_level:
            filtered = [e for e in filtered if e.threat_level == threat_level]
        
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        
        filtered.sort(key=lambda e: e.timestamp, reverse=True)
        
        return [e.to_dict() for e in filtered[:limit]]
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [e for e in self.events if e.timestamp > cutoff]
        
        return {
            'period_hours': hours,
            'total_events': len(recent_events),
            'by_type': {
                event_type.value: sum(1 for e in recent_events if e.event_type == event_type)
                for event_type in SecurityEventType
            },
            'by_threat_level': {
                'critical': sum(1 for e in recent_events if e.threat_level == ThreatLevel.CRITICAL),
                'high': sum(1 for e in recent_events if e.threat_level == ThreatLevel.HIGH),
                'medium': sum(1 for e in recent_events if e.threat_level == ThreatLevel.MEDIUM),
                'low': sum(1 for e in recent_events if e.threat_level == ThreatLevel.LOW)
            },
            'blocked_ips': len(self.waf.blocked_ips),
            'active_alerts': sum(1 for e in recent_events if not e.resolved)
        }


# Global security monitor
security_monitor = SecurityMonitor()
