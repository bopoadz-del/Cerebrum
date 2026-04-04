"""
Status Page System
status.cerebrum.ai - Public status page for service availability
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

from app.core.config import settings
from app.monitoring.uptime import uptime_monitor, CheckStatus

logger = logging.getLogger(__name__)


class IncidentStatus(Enum):
    """Incident status values"""
    INVESTIGATING = 'investigating'
    IDENTIFIED = 'identified'
    MONITORING = 'monitoring'
    RESOLVED = 'resolved'


class IncidentImpact(Enum):
    """Incident impact levels"""
    NONE = 'none'
    MINOR = 'minor'
    MAJOR = 'major'
    CRITICAL = 'critical'


class ComponentStatus(Enum):
    """Component status values"""
    OPERATIONAL = 'operational'
    DEGRADED = 'degraded_performance'
    PARTIAL_OUTAGE = 'partial_outage'
    MAJOR_OUTAGE = 'major_outage'
    MAINTENANCE = 'under_maintenance'


@dataclass
class Incident:
    """Status page incident"""
    id: str
    name: str
    status: IncidentStatus
    impact: IncidentImpact
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    components: List[str] = field(default_factory=list)
    updates: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['impact'] = self.impact.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        return data


@dataclass
class ScheduledMaintenance:
    """Scheduled maintenance window"""
    id: str
    name: str
    description: str
    scheduled_start: datetime
    scheduled_end: datetime
    components: List[str]
    status: str = 'scheduled'  # scheduled, in_progress, completed
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['scheduled_start'] = self.scheduled_start.isoformat()
        data['scheduled_end'] = self.scheduled_end.isoformat()
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class StatusComponent:
    """Status page component"""
    id: str
    name: str
    description: str
    status: ComponentStatus
    group: Optional[str] = None
    order: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data


class StatusPageManager:
    """Manage status page content"""
    
    def __init__(self):
        self.components: Dict[str, StatusComponent] = {}
        self.incidents: Dict[str, Incident] = {}
        self.maintenance_windows: Dict[str, ScheduledMaintenance] = {}
        self._load_default_components()
    
    def _load_default_components(self):
        """Load default status page components"""
        default_components = [
            StatusComponent(
                id='api',
                name='API',
                description='REST API and GraphQL endpoints',
                status=ComponentStatus.OPERATIONAL,
                group='Core Services',
                order=1
            ),
            StatusComponent(
                id='web-app',
                name='Web Application',
                description='Main web application',
                status=ComponentStatus.OPERATIONAL,
                group='Core Services',
                order=2
            ),
            StatusComponent(
                id='mobile-app',
                name='Mobile Application',
                description='iOS and Android apps',
                status=ComponentStatus.OPERATIONAL,
                group='Core Services',
                order=3
            ),
            StatusComponent(
                id='authentication',
                name='Authentication',
                description='Login and user authentication',
                status=ComponentStatus.OPERATIONAL,
                group='Core Services',
                order=4
            ),
            StatusComponent(
                id='database',
                name='Database',
                description='Primary database cluster',
                status=ComponentStatus.OPERATIONAL,
                group='Infrastructure',
                order=5
            ),
            StatusComponent(
                id='cache',
                name='Cache',
                description='Redis cache cluster',
                status=ComponentStatus.OPERATIONAL,
                group='Infrastructure',
                order=6
            ),
            StatusComponent(
                id='storage',
                name='File Storage',
                description='Document and image storage',
                status=ComponentStatus.OPERATIONAL,
                group='Infrastructure',
                order=7
            ),
            StatusComponent(
                id='search',
                name='Search',
                description='Full-text search functionality',
                status=ComponentStatus.OPERATIONAL,
                group='Features',
                order=8
            ),
            StatusComponent(
                id='notifications',
                name='Notifications',
                description='Email and push notifications',
                status=ComponentStatus.OPERATIONAL,
                group='Features',
                order=9
            ),
            StatusComponent(
                id='integrations',
                name='Third-party Integrations',
                description='External service integrations',
                status=ComponentStatus.OPERATIONAL,
                group='Features',
                order=10
            )
        ]
        
        for component in default_components:
            self.components[component.id] = component
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get overall status summary"""
        # Determine overall status
        component_statuses = [c.status for c in self.components.values()]
        
        if any(s == ComponentStatus.MAJOR_OUTAGE for s in component_statuses):
            overall_status = 'major_outage'
            indicator = 'critical'
            description = 'Major Service Outage'
        elif any(s == ComponentStatus.PARTIAL_OUTAGE for s in component_statuses):
            overall_status = 'partial_outage'
            indicator = 'major'
            description = 'Partial Service Outage'
        elif any(s == ComponentStatus.DEGRADED for s in component_statuses):
            overall_status = 'degraded'
            indicator = 'minor'
            description = 'Degraded Performance'
        else:
            overall_status = 'operational'
            indicator = 'none'
            description = 'All Systems Operational'
        
        return {
            'status': {
                'indicator': indicator,
                'description': description
            },
            'page': {
                'name': 'Cerebrum AI Platform Status',
                'url': 'https://status.cerebrum.ai',
                'updated_at': datetime.utcnow().isoformat()
            }
        }
    
    def get_components(self, group: str = None) -> List[Dict[str, Any]]:
        """Get status page components"""
        components = list(self.components.values())
        
        if group:
            components = [c for c in components if c.group == group]
        
        components.sort(key=lambda c: c.order)
        
        return [c.to_dict() for c in components]
    
    def update_component_status(self, component_id: str, status: ComponentStatus):
        """Update component status"""
        if component_id in self.components:
            self.components[component_id].status = status
            self.components[component_id].updated_at = datetime.utcnow()
            logger.info(f"Updated component {component_id} status to {status.value}")
    
    def create_incident(
        self,
        name: str,
        impact: IncidentImpact,
        component_ids: List[str],
        message: str
    ) -> Incident:
        """Create a new incident"""
        incident_id = f"inc-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        now = datetime.utcnow()
        incident = Incident(
            id=incident_id,
            name=name,
            status=IncidentStatus.INVESTIGATING,
            impact=impact,
            created_at=now,
            updated_at=now,
            components=component_ids,
            updates=[{
                'status': IncidentStatus.INVESTIGATING.value,
                'message': message,
                'timestamp': now.isoformat()
            }]
        )
        
        self.incidents[incident_id] = incident
        
        # Update component statuses
        for component_id in component_ids:
            if impact == IncidentImpact.CRITICAL:
                self.update_component_status(component_id, ComponentStatus.MAJOR_OUTAGE)
            elif impact == IncidentImpact.MAJOR:
                self.update_component_status(component_id, ComponentStatus.PARTIAL_OUTAGE)
            elif impact == IncidentImpact.MINOR:
                self.update_component_status(component_id, ComponentStatus.DEGRADED)
        
        logger.info(f"Created incident: {incident_id}")
        return incident
    
    def update_incident(
        self,
        incident_id: str,
        status: IncidentStatus,
        message: str
    ) -> Optional[Incident]:
        """Update an incident"""
        if incident_id not in self.incidents:
            return None
        
        incident = self.incidents[incident_id]
        incident.status = status
        incident.updated_at = datetime.utcnow()
        
        incident.updates.append({
            'status': status.value,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # If resolved, update component statuses
        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()
            for component_id in incident.components:
                self.update_component_status(component_id, ComponentStatus.OPERATIONAL)
        
        logger.info(f"Updated incident {incident_id} to {status.value}")
        return incident
    
    def get_incidents(
        self,
        status: IncidentStatus = None,
        active_only: bool = False,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get incidents"""
        incidents = list(self.incidents.values())
        
        if status:
            incidents = [i for i in incidents if i.status == status]
        
        if active_only:
            incidents = [i for i in incidents if i.status != IncidentStatus.RESOLVED]
        
        incidents.sort(key=lambda i: i.created_at, reverse=True)
        
        return [i.to_dict() for i in incidents[:limit]]
    
    def schedule_maintenance(
        self,
        name: str,
        description: str,
        start: datetime,
        end: datetime,
        component_ids: List[str]
    ) -> ScheduledMaintenance:
        """Schedule maintenance window"""
        maintenance_id = f"mnt-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        maintenance = ScheduledMaintenance(
            id=maintenance_id,
            name=name,
            description=description,
            scheduled_start=start,
            scheduled_end=end,
            components=component_ids
        )
        
        self.maintenance_windows[maintenance_id] = maintenance
        
        logger.info(f"Scheduled maintenance: {maintenance_id}")
        return maintenance
    
    def get_maintenance_windows(
        self,
        upcoming_only: bool = False,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get maintenance windows"""
        windows = list(self.maintenance_windows.values())
        
        if upcoming_only:
            now = datetime.utcnow()
            windows = [w for w in windows if w.scheduled_start > now]
        
        windows.sort(key=lambda w: w.scheduled_start)
        
        return [w.to_dict() for w in windows[:limit]]
    
    def get_full_status_page(self) -> Dict[str, Any]:
        """Get complete status page data"""
        summary = self.get_status_summary()
        
        return {
            **summary,
            'components': self.get_components(),
            'incidents': self.get_incidents(active_only=True),
            'scheduled_maintenances': self.get_maintenance_windows(upcoming_only=True)
        }
    
    def get_uptime_data(self, days: int = 90) -> Dict[str, Any]:
        """Get uptime data for status page"""
        uptime_data = {}
        
        for component_id in self.components:
            # Map component to uptime check
            check_id = self._get_check_id_for_component(component_id)
            if check_id:
                stats = uptime_monitor.get_uptime_stats(check_id, hours=days * 24)
                uptime_data[component_id] = {
                    'uptime_percentage': stats.get('uptime_percentage', 100),
                    'avg_response_time_ms': stats.get('avg_response_time_ms', 0)
                }
        
        return uptime_data
    
    def _get_check_id_for_component(self, component_id: str) -> Optional[str]:
        """Map component ID to uptime check ID"""
        mapping = {
            'api': 'api-health',
            'web-app': 'web-app',
            'database': 'database',
            'cache': 'redis'
        }
        return mapping.get(component_id)


# Global status page manager
status_page_manager = StatusPageManager()


class StatusPageAPI:
    """API endpoints for status page"""
    
    def __init__(self, manager: StatusPageManager):
        self.manager = manager
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return self.manager.get_full_status_page()
    
    def get_components(self) -> List[Dict[str, Any]]:
        """Get all components"""
        return self.manager.get_components()
    
    def get_component(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific component"""
        if component_id in self.manager.components:
            return self.manager.components[component_id].to_dict()
        return None
    
    def get_incidents(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get incidents"""
        return self.manager.get_incidents(active_only=active_only)
    
    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific incident"""
        if incident_id in self.manager.incidents:
            return self.manager.incidents[incident_id].to_dict()
        return None
    
    def get_maintenance(self) -> List[Dict[str, Any]]:
        """Get scheduled maintenance"""
        return self.manager.get_maintenance_windows(upcoming_only=True)
    
    def get_uptime(self, days: int = 90) -> Dict[str, Any]:
        """Get uptime statistics"""
        return self.manager.get_uptime_data(days)


# HTML template for status page
STATUS_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cerebrum AI Platform Status</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .status-indicator {
            display: inline-flex;
            align-items: center;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1.2em;
            font-weight: 600;
        }
        .status-indicator.none { background: #22c55e; color: white; }
        .status-indicator.minor { background: #f59e0b; color: white; }
        .status-indicator.major { background: #ef4444; color: white; }
        .status-indicator.critical { background: #7f1d1d; color: white; }
        .status-indicator::before {
            content: '';
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: white;
            margin-right: 10px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .section {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .section h2 {
            font-size: 1.3em;
            margin-bottom: 16px;
            color: #1f2937;
        }
        .component {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #e5e7eb;
        }
        .component:last-child { border-bottom: none; }
        .component-name { font-weight: 500; }
        .component-description { font-size: 0.9em; color: #6b7280; }
        .component-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }
        .component-status.operational { background: #dcfce7; color: #166534; }
        .component-status.degraded_performance { background: #fef3c7; color: #92400e; }
        .component-status.partial_outage { background: #fee2e2; color: #991b1b; }
        .component-status.major_outage { background: #fecaca; color: #7f1d1d; }
        .incident {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 12px;
        }
        .incident.investigating { background: #fef3c7; }
        .incident.identified { background: #fee2e2; }
        .incident.monitoring { background: #dbeafe; }
        .incident.resolved { background: #dcfce7; }
        .incident h3 { margin-bottom: 8px; }
        .incident-meta { font-size: 0.9em; color: #6b7280; margin-bottom: 12px; }
        .incident-update {
            padding: 12px;
            background: rgba(255,255,255,0.5);
            border-radius: 6px;
            margin-top: 8px;
        }
        .footer {
            text-align: center;
            color: #6b7280;
            font-size: 0.9em;
            margin-top: 40px;
        }
        .uptime-bar {
            display: flex;
            gap: 2px;
            height: 30px;
            margin-top: 12px;
        }
        .uptime-day {
            flex: 1;
            border-radius: 2px;
        }
        .uptime-day.up { background: #22c55e; }
        .uptime-day.down { background: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Cerebrum AI Platform Status</h1>
            <div class="status-indicator {{indicator}}">{{status_description}}</div>
            <p style="margin-top: 16px; color: #6b7280;">Last updated: {{updated_at}}</p>
        </div>
        
        {{#active_incidents}}
        <div class="section">
            <h2>Active Incidents</h2>
            {{#incidents}}
            <div class="incident {{status}}">
                <h3>{{name}}</h3>
                <div class="incident-meta">{{impact}} impact • {{created_at}}</div>
                {{#updates}}
                <div class="incident-update">
                    <strong>{{status}}</strong> - {{message}}
                    <div style="font-size: 0.85em; color: #6b7280; margin-top: 4px;">{{timestamp}}</div>
                </div>
                {{/updates}}
            </div>
            {{/incidents}}
        </div>
        {{/active_incidents}}
        
        <div class="section">
            <h2>System Components</h2>
            {{#components}}
            <div class="component">
                <div>
                    <div class="component-name">{{name}}</div>
                    <div class="component-description">{{description}}</div>
                </div>
                <span class="component-status {{status}}">{{status_text}}</span>
            </div>
            {{/components}}
        </div>
        
        {{#scheduled_maintenance}}
        <div class="section">
            <h2>Scheduled Maintenance</h2>
            {{#maintenance}}
            <div class="component">
                <div>
                    <div class="component-name">{{name}}</div>
                    <div class="component-description">{{scheduled_start}} - {{scheduled_end}}</div>
                </div>
            </div>
            {{/maintenance}}
        </div>
        {{/scheduled_maintenance}}
        
        <div class="footer">
            <p>© 2024 Cerebrum AI. <a href="https://cerebrum.ai">Visit our website</a></p>
            <p style="margin-top: 8px;"><a href="/api/v1/status">View API Status</a></p>
        </div>
    </div>
</body>
</html>
"""
