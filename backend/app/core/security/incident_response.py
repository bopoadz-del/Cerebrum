"""
Incident Response Automation
Enterprise security incident handling and orchestration
"""
import os
import json
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import uuid

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels"""
    CRITICAL = "critical"    # Immediate response required
    HIGH = "high"            # Respond within 1 hour
    MEDIUM = "medium"        # Respond within 4 hours
    LOW = "low"              # Respond within 24 hours
    INFO = "info"            # Log only


class IncidentStatus(Enum):
    """Incident status states"""
    DETECTED = "detected"
    TRIAGING = "triaging"
    CONFIRMED = "confirmed"
    CONTAINING = "containing"
    CONTAINED = "contained"
    ERADICATING = "eradicating"
    ERADICATED = "eradicated"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class IncidentType(Enum):
    """Types of security incidents"""
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH = "data_breach"
    MALWARE = "malware"
    DDOS = "ddos"
    INSIDER_THREAT = "insider_threat"
    PHISHING = "phishing"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    CONFIGURATION_DRIFT = "configuration_drift"
    ANOMALY_DETECTED = "anomaly_detected"
    POLICY_VIOLATION = "policy_violation"


@dataclass
class SecurityIncident:
    """Security incident record"""
    id: str
    type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus
    title: str
    description: str
    detected_at: datetime
    reported_by: str
    affected_assets: List[str] = field(default_factory=list)
    indicators: List[Dict] = field(default_factory=list)
    timeline: List[Dict] = field(default_factory=list)
    assigned_to: Optional[str] = None
    containment_actions: List[Dict] = field(default_factory=list)
    evidence: List[Dict] = field(default_factory=list)
    lessons_learned: str = ""
    related_incidents: List[str] = field(default_factory=list)


@dataclass
class IncidentResponsePlaybook:
    """Incident response playbook"""
    id: str
    name: str
    incident_types: List[IncidentType]
    severity_levels: List[IncidentSeverity]
    steps: List[Dict]
    auto_containment: bool = False
    notification_channels: List[str] = field(default_factory=list)
    escalation_matrix: Dict = field(default_factory=dict)


@dataclass
class IncidentAlert:
    """Incident alert"""
    id: str
    incident_id: str
    channel: str
    sent_at: datetime
    recipients: List[str]
    message: str
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class IncidentDetectionEngine:
    """Engine for detecting security incidents"""
    
    def __init__(self):
        self._detection_rules: Dict[str, Dict] = {}
        self._anomaly_detectors: List[Callable] = []
        self._detection_history: List[Dict] = []
    
    def register_detection_rule(self, rule_id: str, rule: Dict):
        """Register a detection rule"""
        self._detection_rules[rule_id] = rule
    
    def register_anomaly_detector(self, detector: Callable):
        """Register an anomaly detection function"""
        self._anomaly_detectors.append(detector)
    
    async def analyze_event(self, event: Dict) -> Optional[SecurityIncident]:
        """Analyze security event for incident indicators"""
        # Check against detection rules
        for rule_id, rule in self._detection_rules.items():
            if self._matches_rule(event, rule):
                incident = await self._create_incident_from_rule(event, rule)
                return incident
        
        # Check anomaly detectors
        for detector in self._anomaly_detectors:
            anomaly = await detector(event)
            if anomaly:
                incident = await self._create_incident_from_anomaly(event, anomaly)
                return incident
        
        return None
    
    def _matches_rule(self, event: Dict, rule: Dict) -> bool:
        """Check if event matches detection rule"""
        conditions = rule.get('conditions', [])
        
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            event_value = event.get(field)
            
            if operator == 'eq' and event_value != value:
                return False
            elif operator == 'contains' and value not in str(event_value):
                return False
            elif operator == 'gt' and event_value <= value:
                return False
            elif operator == 'lt' and event_value >= value:
                return False
        
        return True
    
    async def _create_incident_from_rule(self, event: Dict, 
                                          rule: Dict) -> SecurityIncident:
        """Create incident from rule match"""
        return SecurityIncident(
            id=f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
            type=IncidentType(rule.get('incident_type')),
            severity=IncidentSeverity(rule.get('severity', 'medium')),
            status=IncidentStatus.DETECTED,
            title=rule.get('title', 'Security Incident'),
            description=rule.get('description', ''),
            detected_at=datetime.utcnow(),
            reported_by='automated_detection',
            indicators=[{'rule_id': rule.get('id'), 'event': event}]
        )
    
    async def _create_incident_from_anomaly(self, event: Dict,
                                             anomaly: Dict) -> SecurityIncident:
        """Create incident from anomaly detection"""
        return SecurityIncident(
            id=f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
            type=IncidentType.ANOMALY_DETECTED,
            severity=IncidentSeverity(anomaly.get('severity', 'medium')),
            status=IncidentStatus.DETECTED,
            title=f"Anomaly Detected: {anomaly.get('type', 'Unknown')}",
            description=anomaly.get('description', ''),
            detected_at=datetime.utcnow(),
            reported_by='anomaly_detection',
            indicators=[{'anomaly': anomaly, 'event': event}]
        )


class IncidentResponseOrchestrator:
    """Orchestrates incident response workflows"""
    
    def __init__(self):
        self._playbooks: Dict[str, IncidentResponsePlaybook] = {}
        self._incidents: Dict[str, SecurityIncident] = {}
        self._active_containments: Dict[str, Dict] = {}
        self._notification_handlers: Dict[str, Callable] = {}
    
    def register_playbook(self, playbook: IncidentResponsePlaybook):
        """Register an incident response playbook"""
        self._playbooks[playbook.id] = playbook
    
    def register_notification_handler(self, channel: str, handler: Callable):
        """Register notification handler for channel"""
        self._notification_handlers[channel] = handler
    
    async def handle_incident(self, incident: SecurityIncident) -> Dict:
        """Handle a security incident"""
        # Store incident
        self._incidents[incident.id] = incident
        
        # Find matching playbook
        playbook = self._find_playbook(incident)
        
        # Execute response
        response_result = {
            'incident_id': incident.id,
            'playbook_id': playbook.id if playbook else None,
            'actions_taken': [],
            'notifications_sent': [],
            'containment_initiated': False
        }
        
        try:
            # Update status to triaging
            await self._update_incident_status(incident, IncidentStatus.TRIAGING)
            
            # Send notifications
            notifications = await self._send_notifications(incident, playbook)
            response_result['notifications_sent'] = notifications
            
            # Execute containment if auto-containment enabled
            if playbook and playbook.auto_containment:
                containment = await self._execute_containment(incident, playbook)
                response_result['containment_initiated'] = containment
            
            # Execute playbook steps
            if playbook:
                for step in playbook.steps:
                    step_result = await self._execute_step(incident, step)
                    response_result['actions_taken'].append({
                        'step': step['name'],
                        'result': step_result
                    })
            
        except Exception as e:
            logger.error(f"Incident handling failed: {e}")
            response_result['error'] = str(e)
        
        return response_result
    
    def _find_playbook(self, incident: SecurityIncident) -> Optional[IncidentResponsePlaybook]:
        """Find matching playbook for incident"""
        for playbook in self._playbooks.values():
            if incident.type in playbook.incident_types:
                if incident.severity in playbook.severity_levels:
                    return playbook
        return None
    
    async def _update_incident_status(self, incident: SecurityIncident,
                                       status: IncidentStatus):
        """Update incident status with timeline entry"""
        old_status = incident.status
        incident.status = status
        
        incident.timeline.append({
            'timestamp': datetime.utcnow().isoformat(),
            'from_status': old_status.value,
            'to_status': status.value,
            'action': 'status_update'
        })
        
        logger.info(f"Incident {incident.id} status: {old_status.value} -> {status.value}")
    
    async def _send_notifications(self, incident: SecurityIncident,
                                   playbook: IncidentResponsePlaybook) -> List[str]:
        """Send incident notifications"""
        notifications = []
        channels = playbook.notification_channels if playbook else ['email']
        
        message = self._format_notification_message(incident)
        
        for channel in channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    await handler(incident, message)
                    notifications.append(channel)
                except Exception as e:
                    logger.error(f"Notification failed for {channel}: {e}")
        
        return notifications
    
    def _format_notification_message(self, incident: SecurityIncident) -> str:
        """Format incident notification message"""
        return f"""
SECURITY INCIDENT ALERT
======================
ID: {incident.id}
Type: {incident.type.value}
Severity: {incident.severity.value.upper()}
Status: {incident.status.value}
Detected: {incident.detected_at.isoformat()}

Title: {incident.title}
Description: {incident.description}

Affected Assets: {', '.join(incident.affected_assets) or 'Unknown'}

Please respond according to incident response procedures.
        """.strip()
    
    async def _execute_containment(self, incident: SecurityIncident,
                                    playbook: IncidentResponsePlaybook) -> bool:
        """Execute containment actions"""
        logger.info(f"Executing containment for incident {incident.id}")
        
        containment_actions = []
        
        # Type-specific containment
        if incident.type == IncidentType.UNAUTHORIZED_ACCESS:
            containment_actions = [
                {'type': 'block_ip', 'params': {'ips': self._extract_ips(incident)}},
                {'type': 'revoke_session', 'params': {'user_id': self._extract_user(incident)}},
                {'type': 'enable_mfa', 'params': {'user_id': self._extract_user(incident)}}
            ]
        
        elif incident.type == IncidentType.DATA_BREACH:
            containment_actions = [
                {'type': 'isolate_system', 'params': {'system_id': incident.affected_assets}},
                {'type': 'revoke_access', 'params': {'resource': incident.affected_assets}},
                {'type': 'enable_audit', 'params': {'level': 'maximum'}}
            ]
        
        elif incident.type == IncidentType.MALWARE:
            containment_actions = [
                {'type': 'isolate_endpoint', 'params': {'endpoint': incident.affected_assets}},
                {'type': 'block_hash', 'params': {'file_hash': self._extract_hashes(incident)}},
                {'type': 'scan_network', 'params': {'scope': 'full'}}
            ]
        
        # Execute actions
        for action in containment_actions:
            try:
                await self._execute_containment_action(incident, action)
                incident.containment_actions.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': action,
                    'status': 'completed'
                })
            except Exception as e:
                logger.error(f"Containment action failed: {e}")
                incident.containment_actions.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': action,
                    'status': 'failed',
                    'error': str(e)
                })
        
        await self._update_incident_status(incident, IncidentStatus.CONTAINED)
        
        return len([a for a in incident.containment_actions if a['status'] == 'completed']) > 0
    
    async def _execute_containment_action(self, incident: SecurityIncident,
                                           action: Dict):
        """Execute a single containment action"""
        logger.info(f"Executing containment action: {action['type']}")
        
        # This would integrate with actual security systems
        await asyncio.sleep(0.5)
    
    async def _execute_step(self, incident: SecurityIncident, 
                            step: Dict) -> bool:
        """Execute a playbook step"""
        logger.info(f"Executing step: {step['name']}")
        
        # This would execute actual response actions
        await asyncio.sleep(0.5)
        
        return True
    
    def _extract_ips(self, incident: SecurityIncident) -> List[str]:
        """Extract IP addresses from incident indicators"""
        ips = []
        for indicator in incident.indicators:
            if 'ip' in indicator:
                ips.append(indicator['ip'])
        return ips
    
    def _extract_user(self, incident: SecurityIncident) -> Optional[str]:
        """Extract user ID from incident indicators"""
        for indicator in incident.indicators:
            if 'user_id' in indicator:
                return indicator['user_id']
        return None
    
    def _extract_hashes(self, incident: SecurityIncident) -> List[str]:
        """Extract file hashes from incident indicators"""
        hashes = []
        for indicator in incident.indicators:
            if 'file_hash' in indicator:
                hashes.append(indicator['file_hash'])
        return hashes


class IncidentMetricsTracker:
    """Tracks incident response metrics"""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {
            'total_incidents': 0,
            'by_type': {},
            'by_severity': {},
            'mttr': [],  # Mean Time To Respond
            'mttd': [],  # Mean Time To Detect
            'containment_time': []
        }
    
    def record_incident(self, incident: SecurityIncident):
        """Record incident metrics"""
        self._metrics['total_incidents'] += 1
        
        # By type
        incident_type = incident.type.value
        self._metrics['by_type'][incident_type] = \
            self._metrics['by_type'].get(incident_type, 0) + 1
        
        # By severity
        severity = incident.severity.value
        self._metrics['by_severity'][severity] = \
            self._metrics['by_severity'].get(severity, 0) + 1
    
    def record_resolution(self, incident: SecurityIncident):
        """Record incident resolution metrics"""
        if incident.detected_at:
            # Calculate detection to containment time
            containment_entry = next(
                (t for t in incident.timeline if t.get('to_status') == 'contained'),
                None
            )
            
            if containment_entry:
                containment_time = datetime.fromisoformat(containment_entry['timestamp'])
                detection_time = incident.detected_at
                time_to_contain = (containment_time - detection_time).total_seconds() / 60
                self._metrics['containment_time'].append(time_to_contain)
    
    def get_metrics(self) -> Dict:
        """Get incident response metrics"""
        metrics = self._metrics.copy()
        
        # Calculate averages
        if metrics['containment_time']:
            metrics['avg_containment_time_minutes'] = \
                sum(metrics['containment_time']) / len(metrics['containment_time'])
        
        return metrics


# Global instances
detection_engine = IncidentDetectionEngine()
response_orchestrator = IncidentResponseOrchestrator()
metrics_tracker = IncidentMetricsTracker()