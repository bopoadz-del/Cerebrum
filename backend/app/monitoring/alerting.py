"""
Alerting System
PagerDuty/Opsgenie integration for incident management
"""

import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import asyncio
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class AlertStatus(Enum):
    """Alert status values"""
    TRIGGERED = 'triggered'
    ACKNOWLEDGED = 'acknowledged'
    RESOLVED = 'resolved'
    SUPPRESSED = 'suppressed'


@dataclass
class Alert:
    """Alert definition"""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    service: str
    created_at: datetime
    updated_at: datetime
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    dedup_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['acknowledged_at'] = self.acknowledged_at.isoformat() if self.acknowledged_at else None
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data


@dataclass
class AlertRule:
    """Alert rule configuration"""
    id: str
    name: str
    condition: str  # Query or condition to evaluate
    threshold: float
    comparison: str  # gt, lt, eq, neq
    duration_minutes: int
    severity: AlertSeverity
    notification_channels: List[str]
    auto_resolve: bool = True
    enabled: bool = True
    cooldown_minutes: int = 30
    description: str = ''


class PagerDutyClient:
    """PagerDuty API client"""
    
    def __init__(self, api_token: str, service_key: str):
        self.api_token = api_token
        self.service_key = service_key
        self.base_url = 'https://api.pagerduty.com'
        self.events_url = 'https://events.pagerduty.com/v2/enqueue'
    
    async def trigger_incident(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        dedup_key: str = None,
        custom_details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Trigger a PagerDuty incident"""
        payload = {
            'routing_key': self.service_key,
            'event_action': 'trigger',
            'dedup_key': dedup_key,
            'payload': {
                'summary': title,
                'severity': self._map_severity(severity),
                'source': settings.SERVICE_NAME,
                'custom_details': custom_details or {}
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.events_url,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    
    async def acknowledge_incident(self, dedup_key: str) -> Dict[str, Any]:
        """Acknowledge a PagerDuty incident"""
        payload = {
            'routing_key': self.service_key,
            'event_action': 'acknowledge',
            'dedup_key': dedup_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.events_url,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    
    async def resolve_incident(self, dedup_key: str) -> Dict[str, Any]:
        """Resolve a PagerDuty incident"""
        payload = {
            'routing_key': self.service_key,
            'event_action': 'resolve',
            'dedup_key': dedup_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.events_url,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    
    def _map_severity(self, severity: AlertSeverity) -> str:
        """Map internal severity to PagerDuty severity"""
        mapping = {
            AlertSeverity.INFO: 'info',
            AlertSeverity.WARNING: 'warning',
            AlertSeverity.ERROR: 'error',
            AlertSeverity.CRITICAL: 'critical'
        }
        return mapping.get(severity, 'error')


class OpsgenieClient:
    """Opsgenie API client"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://api.opsgenie.com/v2'
    
    async def create_alert(
        self,
        title: str,
        message: str,
        priority: str = 'P3',
        alias: str = None,
        details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create an Opsgenie alert"""
        payload = {
            'message': title,
            'description': message,
            'priority': priority,
            'alias': alias,
            'details': details or {},
            'source': settings.SERVICE_NAME
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/alerts',
                json=payload,
                headers={'Authorization': f'GenieKey {self.api_key}'},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    
    async def close_alert(self, alias: str) -> Dict[str, Any]:
        """Close an Opsgenie alert"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/alerts/{alias}/close',
                headers={'Authorization': f'GenieKey {self.api_key}'},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()


class SlackNotifier:
    """Slack notification client"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def send_alert(self, alert: Alert, channel: str = None):
        """Send alert to Slack"""
        color = self._get_color(alert.severity)
        
        payload = {
            'channel': channel,
            'attachments': [{
                'color': color,
                'title': alert.title,
                'text': alert.message,
                'fields': [
                    {'title': 'Severity', 'value': alert.severity.value, 'short': True},
                    {'title': 'Source', 'value': alert.source, 'short': True},
                    {'title': 'Status', 'value': alert.status.value, 'short': True},
                    {'title': 'Time', 'value': alert.created_at.isoformat(), 'short': True}
                ],
                'footer': 'Cerebrum AI Monitoring',
                'ts': int(alert.created_at.timestamp())
            }]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.webhook_url,
                json=payload,
                timeout=10.0
            )
            response.raise_for_status()
    
    def _get_color(self, severity: AlertSeverity) -> str:
        """Get Slack color for severity"""
        colors = {
            AlertSeverity.INFO: '#3b82f6',
            AlertSeverity.WARNING: '#f59e0b',
            AlertSeverity.ERROR: '#ef4444',
            AlertSeverity.CRITICAL: '#7f1d1d'
        }
        return colors.get(severity, '#6b7280')


class AlertManager:
    """Central alert management system"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, AlertRule] = {}
        self.notification_channels: Dict[str, Any] = {}
        self.pagerduty: Optional[PagerDutyClient] = None
        self.opsgenie: Optional[OpsgenieClient] = None
        self.slack: Optional[SlackNotifier] = None
        self._callbacks: List[Callable] = []
        self._rule_tasks: Dict[str, asyncio.Task] = {}
    
    def initialize(self):
        """Initialize notification channels"""
        if settings.PAGERDUTY_SERVICE_KEY:
            self.pagerduty = PagerDutyClient(
                settings.PAGERDUTY_API_TOKEN,
                settings.PAGERDUTY_SERVICE_KEY
            )
        
        if settings.OPSGENIE_API_KEY:
            self.opsgenie = OpsgenieClient(settings.OPSGENIE_API_KEY)
        
        if settings.SLACK_WEBHOOK_URL:
            self.slack = SlackNotifier(settings.SLACK_WEBHOOK_URL)
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules[rule.id] = rule
        
        if rule.enabled:
            self._start_rule_evaluation(rule)
    
    def _start_rule_evaluation(self, rule: AlertRule):
        """Start evaluating an alert rule"""
        if rule.id in self._rule_tasks:
            return
        
        task = asyncio.create_task(self._evaluate_rule_loop(rule))
        self._rule_tasks[rule.id] = task
    
    async def _evaluate_rule_loop(self, rule: AlertRule):
        """Continuously evaluate an alert rule"""
        while rule.enabled:
            try:
                should_alert = await self._evaluate_condition(rule)
                
                if should_alert:
                    await self._trigger_rule_alert(rule)
                
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")
            
            await asyncio.sleep(rule.duration_minutes * 60)
    
    async def _evaluate_condition(self, rule: AlertRule) -> bool:
        """Evaluate alert rule condition"""
        # This would evaluate the condition against metrics
        # For now, return False as placeholder
        return False
    
    async def _trigger_rule_alert(self, rule: AlertRule):
        """Trigger alert from rule"""
        alert = Alert(
            id=f"rule-{rule.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            title=f"Rule triggered: {rule.name}",
            message=rule.description,
            severity=rule.severity,
            status=AlertStatus.TRIGGERED,
            source='alert_rule',
            service=settings.SERVICE_NAME,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={'rule_id': rule.id}
        )
        
        await self.create_alert(alert)
    
    async def create_alert(self, alert: Alert) -> str:
        """Create and send an alert"""
        self.alerts[alert.id] = alert
        
        # Send to notification channels
        await self._send_notifications(alert)
        
        # Notify callbacks
        await self._notify_callbacks(alert)
        
        logger.info(f"Created alert: {alert.id}")
        return alert.id
    
    async def _send_notifications(self, alert: Alert):
        """Send alert to all configured channels"""
        tasks = []
        
        # PagerDuty for critical alerts
        if self.pagerduty and alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            tasks.append(self._send_pagerduty(alert))
        
        # Opsgenie
        if self.opsgenie:
            tasks.append(self._send_opsgenie(alert))
        
        # Slack
        if self.slack:
            tasks.append(self._send_slack(alert))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_pagerduty(self, alert: Alert):
        """Send alert to PagerDuty"""
        try:
            result = await self.pagerduty.trigger_incident(
                title=alert.title,
                message=alert.message,
                severity=alert.severity,
                dedup_key=alert.dedup_key,
                custom_details=alert.metadata
            )
            alert.dedup_key = result.get('dedup_key')
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
    
    async def _send_opsgenie(self, alert: Alert):
        """Send alert to Opsgenie"""
        try:
            priority = self._map_to_opsgenie_priority(alert.severity)
            await self.opsgenie.create_alert(
                title=alert.title,
                message=alert.message,
                priority=priority,
                alias=alert.dedup_key,
                details=alert.metadata
            )
        except Exception as e:
            logger.error(f"Failed to send Opsgenie alert: {e}")
    
    async def _send_slack(self, alert: Alert):
        """Send alert to Slack"""
        try:
            await self.slack.send_alert(alert)
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _map_to_opsgenie_priority(self, severity: AlertSeverity) -> str:
        """Map severity to Opsgenie priority"""
        mapping = {
            AlertSeverity.INFO: 'P5',
            AlertSeverity.WARNING: 'P3',
            AlertSeverity.ERROR: 'P2',
            AlertSeverity.CRITICAL: 'P1'
        }
        return mapping.get(severity, 'P3')
    
    async def acknowledge_alert(self, alert_id: str, user_id: str) -> Optional[Alert]:
        """Acknowledge an alert"""
        if alert_id not in self.alerts:
            return None
        
        alert = self.alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()
        alert.updated_at = datetime.utcnow()
        
        # Acknowledge in PagerDuty
        if self.pagerduty and alert.dedup_key:
            try:
                await self.pagerduty.acknowledge_incident(alert.dedup_key)
            except Exception as e:
                logger.error(f"Failed to acknowledge PagerDuty incident: {e}")
        
        return alert
    
    async def resolve_alert(self, alert_id: str, user_id: str = None) -> Optional[Alert]:
        """Resolve an alert"""
        if alert_id not in self.alerts:
            return None
        
        alert = self.alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_by = user_id
        alert.resolved_at = datetime.utcnow()
        alert.updated_at = datetime.utcnow()
        
        # Resolve in PagerDuty
        if self.pagerduty and alert.dedup_key:
            try:
                await self.pagerduty.resolve_incident(alert.dedup_key)
            except Exception as e:
                logger.error(f"Failed to resolve PagerDuty incident: {e}")
        
        return alert
    
    def on_alert(self, callback: Callable):
        """Register alert callback"""
        self._callbacks.append(callback)
    
    async def _notify_callbacks(self, alert: Alert):
        """Notify registered callbacks"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(alert))
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def get_alerts(
        self,
        status: AlertStatus = None,
        severity: AlertSeverity = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get alerts with filtering"""
        alerts = list(self.alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        
        return [a.to_dict() for a in alerts[:limit]]
    
    def get_alert_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_alerts = [a for a in self.alerts.values() if a.created_at > cutoff]
        
        return {
            'total': len(recent_alerts),
            'by_severity': {
                severity.value: sum(1 for a in recent_alerts if a.severity == severity)
                for severity in AlertSeverity
            },
            'by_status': {
                status.value: sum(1 for a in recent_alerts if a.status == status)
                for status in AlertStatus
            },
            'mttr_minutes': self._calculate_mttr(recent_alerts)
        }
    
    def _calculate_mttr(self, alerts: List[Alert]) -> float:
        """Calculate Mean Time To Resolution"""
        resolved = [a for a in alerts if a.resolved_at and a.created_at]
        
        if not resolved:
            return 0
        
        total_minutes = sum(
            (a.resolved_at - a.created_at).total_seconds() / 60
            for a in resolved
        )
        
        return total_minutes / len(resolved)


# Global alert manager
alert_manager = AlertManager()
