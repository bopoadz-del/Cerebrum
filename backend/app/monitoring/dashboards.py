"""
Monitoring Dashboards
Executive, Engineering, and Customer Success dashboards
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class DashboardType(Enum):
    """Dashboard types"""
    EXECUTIVE = 'executive'
    ENGINEERING = 'engineering'
    CUSTOMER_SUCCESS = 'customer_success'
    SECURITY = 'security'
    BUSINESS = 'business'


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    id: str
    type: str  # metric, chart, table, alert
    title: str
    query: str
    data_source: str
    refresh_interval: int = 60  # seconds
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dashboard:
    """Dashboard configuration"""
    id: str
    name: str
    type: DashboardType
    widgets: List[DashboardWidget]
    layout: Dict[str, Any]
    filters: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ExecutiveDashboard:
    """Executive-level dashboard with business KPIs"""
    
    def __init__(self):
        self.widgets = self._create_widgets()
    
    def _create_widgets(self) -> List[DashboardWidget]:
        """Create executive dashboard widgets"""
        return [
            DashboardWidget(
                id='revenue_mrr',
                type='metric',
                title='Monthly Recurring Revenue',
                query='SELECT SUM(mrr) FROM subscriptions WHERE status = \'active\'',
                data_source='billing_db',
                config={'format': 'currency', 'prefix': '$'}
            ),
            DashboardWidget(
                id='active_tenants',
                type='metric',
                title='Active Tenants',
                query='SELECT COUNT(*) FROM tenants WHERE status = \'active\'',
                data_source='app_db'
            ),
            DashboardWidget(
                id='user_growth',
                type='chart',
                title='User Growth (30 days)',
                query='''
                    SELECT DATE(created_at) as date, COUNT(*) as users
                    FROM users
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                ''',
                data_source='app_db',
                config={'chart_type': 'line', 'x_axis': 'date', 'y_axis': 'users'}
            ),
            DashboardWidget(
                id='churn_rate',
                type='metric',
                title='Monthly Churn Rate',
                query='''
                    SELECT 
                        (COUNT(CASE WHEN status = 'cancelled' THEN 1 END) * 100.0 / COUNT(*)) as churn_rate
                    FROM subscriptions
                    WHERE updated_at >= DATE_TRUNC('month', NOW())
                ''',
                data_source='billing_db',
                config={'format': 'percentage', 'suffix': '%'}
            ),
            DashboardWidget(
                id='arpu',
                type='metric',
                title='Average Revenue Per User',
                query='''
                    SELECT 
                        SUM(mrr) / COUNT(DISTINCT user_id) as arpu
                    FROM subscriptions
                    WHERE status = 'active'
                ''',
                data_source='billing_db',
                config={'format': 'currency', 'prefix': '$'}
            ),
            DashboardWidget(
                id='nps_score',
                type='metric',
                title='Net Promoter Score',
                query='''
                    SELECT 
                        (COUNT(CASE WHEN score >= 9 THEN 1 END) * 100.0 / COUNT(*)) -
                        (COUNT(CASE WHEN score <= 6 THEN 1 END) * 100.0 / COUNT(*)) as nps
                    FROM nps_surveys
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                ''',
                data_source='app_db',
                config={'format': 'number'}
            ),
            DashboardWidget(
                id='system_uptime',
                type='metric',
                title='System Uptime (30 days)',
                query='''
                    SELECT 
                        (COUNT(CASE WHEN status = 'up' THEN 1 END) * 100.0 / COUNT(*)) as uptime
                    FROM uptime_checks
                    WHERE timestamp >= NOW() - INTERVAL '30 days'
                ''',
                data_source='monitoring_db',
                config={'format': 'percentage', 'suffix': '%', 'target': 99.9}
            ),
            DashboardWidget(
                id='top_tenants',
                type='table',
                title='Top 10 Tenants by Usage',
                query='''
                    SELECT 
                        t.name,
                        COUNT(DISTINCT u.id) as users,
                        COUNT(DISTINCT p.id) as projects,
                        ts.storage_gb
                    FROM tenants t
                    JOIN users u ON u.tenant_id = t.id
                    JOIN projects p ON p.tenant_id = t.id
                    JOIN tenant_storage ts ON ts.tenant_id = t.id
                    WHERE t.status = 'active'
                    GROUP BY t.id, t.name, ts.storage_gb
                    ORDER BY users DESC
                    LIMIT 10
                ''',
                data_source='app_db'
            )
        ]
    
    def get_dashboard_data(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Get executive dashboard data"""
        return {
            'dashboard_type': 'executive',
            'generated_at': datetime.utcnow().isoformat(),
            'period': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            },
            'widgets': [
                {
                    'id': w.id,
                    'title': w.title,
                    'type': w.type,
                    'data': self._execute_widget_query(w, start_date, end_date)
                }
                for w in self.widgets
            ]
        }
    
    def _execute_widget_query(self, widget: DashboardWidget, 
                              start_date: datetime, end_date: datetime) -> Any:
        """Execute widget query and return data"""
        # This would execute the actual query against the data source
        # For now, return placeholder data
        return {'value': 0, 'trend': 'up', 'change_percent': 0}


class EngineeringDashboard:
    """Engineering dashboard with technical metrics"""
    
    def __init__(self):
        self.widgets = self._create_widgets()
    
    def _create_widgets(self) -> List[DashboardWidget]:
        """Create engineering dashboard widgets"""
        return [
            DashboardWidget(
                id='error_rate',
                type='metric',
                title='Error Rate (5 min)',
                query='rate(cerebrum_http_requests_total{status_code=~"5.."}[5m])',
                data_source='prometheus'
            ),
            DashboardWidget(
                id='p95_latency',
                type='metric',
                title='P95 Response Time',
                query='histogram_quantile(0.95, rate(cerebrum_http_request_duration_seconds_bucket[5m]))',
                data_source='prometheus',
                config={'format': 'duration', 'unit': 'ms'}
            ),
            DashboardWidget(
                id='throughput',
                type='chart',
                title='Request Throughput',
                query='rate(cerebrum_http_requests_total[5m])',
                data_source='prometheus',
                config={'chart_type': 'line'}
            ),
            DashboardWidget(
                id='cpu_usage',
                type='chart',
                title='CPU Usage by Service',
                query='cerebrum_system_cpu_usage_percent',
                data_source='prometheus',
                config={'chart_type': 'area'}
            ),
            DashboardWidget(
                id='memory_usage',
                type='chart',
                title='Memory Usage',
                query='cerebrum_system_memory_usage_bytes',
                data_source='prometheus',
                config={'chart_type': 'area'}
            ),
            DashboardWidget(
                id='db_connections',
                type='metric',
                title='Active DB Connections',
                query='cerebrum_db_connections_active',
                data_source='prometheus'
            ),
            DashboardWidget(
                id='cache_hit_ratio',
                type='metric',
                title='Cache Hit Ratio',
                query='cerebrum_cache_hit_ratio',
                data_source='prometheus',
                config={'format': 'percentage', 'suffix': '%'}
            ),
            DashboardWidget(
                id='deployments',
                type='table',
                title='Recent Deployments',
                query='''
                    SELECT 
                        version,
                        deployed_at,
                        deployed_by,
                        status
                    FROM deployments
                    ORDER BY deployed_at DESC
                    LIMIT 10
                ''',
                data_source='app_db'
            ),
            DashboardWidget(
                id='slow_queries',
                type='table',
                title='Slow Queries (Top 10)',
                query='''
                    SELECT 
                        query,
                        mean_exec_time,
                        calls,
                        total_exec_time
                    FROM pg_stat_statements
                    ORDER BY mean_exec_time DESC
                    LIMIT 10
                ''',
                data_source='postgres'
            ),
            DashboardWidget(
                id='active_alerts',
                type='alert',
                title='Active Alerts',
                query="status = 'triggered' OR status = 'acknowledged'",
                data_source='alert_manager'
            )
        ]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get engineering dashboard data"""
        return {
            'dashboard_type': 'engineering',
            'generated_at': datetime.utcnow().isoformat(),
            'widgets': [
                {
                    'id': w.id,
                    'title': w.title,
                    'type': w.type,
                    'data': self._execute_widget_query(w)
                }
                for w in self.widgets
            ]
        }
    
    def _execute_widget_query(self, widget: DashboardWidget) -> Any:
        """Execute widget query"""
        return {'value': 0}


class CustomerSuccessDashboard:
    """Customer Success dashboard with user engagement metrics"""
    
    def __init__(self):
        self.widgets = self._create_widgets()
    
    def _create_widgets(self) -> List[DashboardWidget]:
        """Create CS dashboard widgets"""
        return [
            DashboardWidget(
                id='daily_active_users',
                type='metric',
                title='Daily Active Users',
                query='''
                    SELECT COUNT(DISTINCT user_id) 
                    FROM user_sessions 
                    WHERE last_activity >= CURRENT_DATE
                ''',
                data_source='app_db'
            ),
            DashboardWidget(
                id='monthly_active_users',
                type='metric',
                title='Monthly Active Users',
                query='''
                    SELECT COUNT(DISTINCT user_id)
                    FROM user_sessions
                    WHERE last_activity >= DATE_TRUNC('month', NOW())
                ''',
                data_source='app_db'
            ),
            DashboardWidget(
                id='feature_adoption',
                type='chart',
                title='Feature Adoption Rate',
                query='''
                    SELECT 
                        feature_name,
                        COUNT(DISTINCT user_id) as users,
                        COUNT(*) as events
                    FROM feature_usage
                    WHERE timestamp >= NOW() - INTERVAL '30 days'
                    GROUP BY feature_name
                    ORDER BY users DESC
                ''',
                data_source='app_db',
                config={'chart_type': 'bar'}
            ),
            DashboardWidget(
                id='support_tickets',
                type='metric',
                title='Open Support Tickets',
                query="SELECT COUNT(*) FROM support_tickets WHERE status = 'open'",
                data_source='app_db'
            ),
            DashboardWidget(
                id='avg_resolution_time',
                type='metric',
                title='Avg Ticket Resolution Time',
                query='''
                    SELECT AVG(resolved_at - created_at) as avg_time
                    FROM support_tickets
                    WHERE status = 'resolved'
                    AND resolved_at >= NOW() - INTERVAL '30 days'
                ''',
                data_source='app_db',
                config={'format': 'duration'}
            ),
            DashboardWidget(
                id='csat_score',
                type='metric',
                title='Customer Satisfaction (CSAT)',
                query='''
                    SELECT 
                        (COUNT(CASE WHEN rating >= 4 THEN 1 END) * 100.0 / COUNT(*)) as csat
                    FROM csat_surveys
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                ''',
                data_source='app_db',
                config={'format': 'percentage', 'suffix': '%'}
            ),
            DashboardWidget(
                id='user_onboarding',
                type='chart',
                title='User Onboarding Funnel',
                query='''
                    SELECT 
                        step_name,
                        COUNT(DISTINCT user_id) as users,
                        COUNT(DISTINCT CASE WHEN completed THEN user_id END) as completed
                    FROM onboarding_steps
                    WHERE started_at >= NOW() - INTERVAL '30 days'
                    GROUP BY step_name
                    ORDER BY step_order
                ''',
                data_source='app_db',
                config={'chart_type': 'funnel'}
            ),
            DashboardWidget(
                id='at_risk_tenants',
                type='table',
                title='At-Risk Tenants',
                query='''
                    SELECT 
                        t.name,
                        t.plan,
                        COUNT(DISTINCT u.id) as users,
                        MAX(us.last_activity) as last_activity,
                        health_score
                    FROM tenants t
                    JOIN users u ON u.tenant_id = t.id
                    LEFT JOIN user_sessions us ON us.user_id = u.id
                    JOIN tenant_health th ON th.tenant_id = t.id
                    WHERE t.status = 'active'
                    AND health_score < 50
                    GROUP BY t.id, t.name, t.plan, health_score
                    ORDER BY health_score ASC
                    LIMIT 10
                ''',
                data_source='app_db'
            )
        ]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get CS dashboard data"""
        return {
            'dashboard_type': 'customer_success',
            'generated_at': datetime.utcnow().isoformat(),
            'widgets': [
                {
                    'id': w.id,
                    'title': w.title,
                    'type': w.type,
                    'data': self._execute_widget_query(w)
                }
                for w in self.widgets
            ]
        }
    
    def _execute_widget_query(self, widget: DashboardWidget) -> Any:
        """Execute widget query"""
        return {'value': 0}


class DashboardManager:
    """Manage all dashboards"""
    
    def __init__(self):
        self.executive = ExecutiveDashboard()
        self.engineering = EngineeringDashboard()
        self.customer_success = CustomerSuccessDashboard()
        self.custom_dashboards: Dict[str, Dashboard] = {}
    
    def get_dashboard(self, dashboard_type: DashboardType, 
                      user_role: str = None) -> Dict[str, Any]:
        """Get dashboard by type"""
        if dashboard_type == DashboardType.EXECUTIVE:
            return self.executive.get_dashboard_data()
        elif dashboard_type == DashboardType.ENGINEERING:
            return self.engineering.get_dashboard_data()
        elif dashboard_type == DashboardType.CUSTOMER_SUCCESS:
            return self.customer_success.get_dashboard_data()
        else:
            return {}
    
    def create_custom_dashboard(self, dashboard: Dashboard) -> str:
        """Create a custom dashboard"""
        self.custom_dashboards[dashboard.id] = dashboard
        return dashboard.id
    
    def get_custom_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a custom dashboard"""
        return self.custom_dashboards.get(dashboard_id)
    
    def get_all_dashboards(self) -> List[Dict[str, str]]:
        """Get list of all available dashboards"""
        dashboards = [
            {'id': 'executive', 'name': 'Executive Dashboard', 'type': 'executive'},
            {'id': 'engineering', 'name': 'Engineering Dashboard', 'type': 'engineering'},
            {'id': 'customer_success', 'name': 'Customer Success Dashboard', 'type': 'customer_success'}
        ]
        
        for dashboard_id, dashboard in self.custom_dashboards.items():
            dashboards.append({
                'id': dashboard_id,
                'name': dashboard.name,
                'type': dashboard.type.value
            })
        
        return dashboards


# Global dashboard manager
dashboard_manager = DashboardManager()
