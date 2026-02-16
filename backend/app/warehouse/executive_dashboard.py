"""
Executive Dashboard
C-suite portfolio view with key business metrics
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class KPICard:
    """KPI card for dashboard"""
    id: str
    title: str
    value: Any
    unit: str = ''
    change_percent: float = 0
    trend: str = 'neutral'  # up, down, neutral
    target: Optional[float] = None
    comparison_period: str = 'vs last month'


@dataclass
class ChartData:
    """Chart data for dashboard"""
    chart_type: str  # line, bar, pie, funnel
    title: str
    labels: List[str]
    datasets: List[Dict[str, Any]]
    options: Dict[str, Any] = field(default_factory=dict)


class ExecutiveDashboard:
    """Executive dashboard with business KPIs"""
    
    def __init__(self):
        self.kpis: Dict[str, KPICard] = {}
        self.charts: Dict[str, ChartData] = {}
    
    async def get_revenue_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get revenue metrics"""
        # This would query the data warehouse
        return {
            'mrr': 125000,
            'arr': 1500000,
            'mrr_growth': 12.5,
            'revenue_churn': 2.1,
            'net_revenue_retention': 108.5,
            'arpu': 250,
            'ltv': 2500,
            'cac': 500,
            'ltv_cac_ratio': 5.0
        }
    
    async def get_customer_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get customer metrics"""
        return {
            'total_customers': 500,
            'new_customers': 25,
            'churned_customers': 5,
            'customer_growth_rate': 4.2,
            'logo_churn_rate': 1.0,
            'nps_score': 52,
            'csat_score': 4.5,
            'active_users': 2500,
            'user_growth': 8.3
        }
    
    async def get_product_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get product usage metrics"""
        return {
            'total_projects': 2500,
            'active_projects': 1800,
            'total_tasks': 50000,
            'completed_tasks': 42000,
            'task_completion_rate': 84,
            'avg_project_duration_days': 45,
            'feature_adoption': {
                'document_management': 85,
                'task_tracking': 92,
                'reporting': 65,
                'integrations': 45
            }
        }
    
    async def get_operational_metrics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get operational metrics"""
        return {
            'system_uptime': 99.95,
            'api_response_time_ms': 120,
            'error_rate': 0.01,
            'support_tickets': 45,
            'avg_resolution_hours': 8,
            'customer_satisfaction': 4.6
        }
    
    async def get_financial_forecast(self, months: int = 12) -> Dict[str, Any]:
        """Get financial forecast"""
        return {
            'forecast_period_months': months,
            'projected_arr': 2000000,
            'projected_growth': 33.3,
            'revenue_by_quarter': [
                {'quarter': 'Q1', 'revenue': 375000},
                {'quarter': 'Q2', 'revenue': 400000},
                {'quarter': 'Q3', 'revenue': 450000},
                {'quarter': 'Q4', 'revenue': 500000}
            ],
            'cash_runway_months': 24,
            'burn_rate_monthly': 150000
        }
    
    async def get_portfolio_overview(self) -> Dict[str, Any]:
        """Get portfolio overview"""
        return {
            'summary': {
                'total_tenants': 500,
                'active_tenants': 450,
                'total_users': 5000,
                'active_users': 3500,
                'total_projects': 2500,
                'active_projects': 1800
            },
            'by_segment': {
                'enterprise': {'count': 50, 'revenue': 750000, 'growth': 15},
                'mid_market': {'count': 150, 'revenue': 500000, 'growth': 20},
                'smb': {'count': 300, 'revenue': 250000, 'growth': 25}
            },
            'by_industry': {
                'construction': {'count': 200, 'revenue': 600000},
                'engineering': {'count': 150, 'revenue': 450000},
                'architecture': {'count': 100, 'revenue': 300000},
                'other': {'count': 50, 'revenue': 150000}
            },
            'health_score': {
                'excellent': 200,
                'good': 200,
                'at_risk': 80,
                'churn_risk': 20
            }
        }
    
    async def get_kpi_cards(self) -> List[Dict[str, Any]]:
        """Get KPI cards for dashboard"""
        revenue = await self.get_revenue_metrics()
        customers = await self.get_customer_metrics()
        product = await self.get_product_metrics()
        operational = await self.get_operational_metrics()
        
        return [
            {
                'id': 'mrr',
                'title': 'Monthly Recurring Revenue',
                'value': revenue['mrr'],
                'unit': '$',
                'change_percent': revenue['mrr_growth'],
                'trend': 'up',
                'format': 'currency'
            },
            {
                'id': 'customers',
                'title': 'Total Customers',
                'value': customers['total_customers'],
                'change_percent': customers['customer_growth_rate'],
                'trend': 'up',
                'format': 'number'
            },
            {
                'id': 'nps',
                'title': 'Net Promoter Score',
                'value': customers['nps_score'],
                'change_percent': 5,
                'trend': 'up',
                'format': 'number'
            },
            {
                'id': 'uptime',
                'title': 'System Uptime',
                'value': operational['system_uptime'],
                'unit': '%',
                'change_percent': 0,
                'trend': 'neutral',
                'format': 'percentage'
            },
            {
                'id': 'churn',
                'title': 'Logo Churn Rate',
                'value': customers['logo_churn_rate'],
                'unit': '%',
                'change_percent': -0.5,
                'trend': 'up',  # Lower is better for churn
                'format': 'percentage',
                'lower_is_better': True
            },
            {
                'id': 'nrr',
                'title': 'Net Revenue Retention',
                'value': revenue['net_revenue_retention'],
                'unit': '%',
                'change_percent': 3,
                'trend': 'up',
                'format': 'percentage'
            }
        ]
    
    async def get_charts(self) -> Dict[str, Any]:
        """Get charts for dashboard"""
        return {
            'revenue_trend': {
                'type': 'line',
                'title': 'Revenue Trend',
                'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                'datasets': [
                    {
                        'label': 'MRR',
                        'data': [100000, 105000, 110000, 115000, 120000, 125000]
                    }
                ]
            },
            'customer_growth': {
                'type': 'bar',
                'title': 'Customer Growth',
                'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                'datasets': [
                    {
                        'label': 'New Customers',
                        'data': [20, 22, 25, 23, 28, 25]
                    },
                    {
                        'label': 'Churned Customers',
                        'data': [3, 4, 5, 4, 6, 5]
                    }
                ]
            },
            'revenue_by_segment': {
                'type': 'pie',
                'title': 'Revenue by Segment',
                'labels': ['Enterprise', 'Mid-Market', 'SMB'],
                'datasets': [
                    {
                        'data': [750000, 500000, 250000]
                    }
                ]
            },
            'feature_adoption': {
                'type': 'horizontalBar',
                'title': 'Feature Adoption',
                'labels': ['Task Tracking', 'Document Management', 'Reporting', 'Integrations'],
                'datasets': [
                    {
                        'label': 'Adoption %',
                        'data': [92, 85, 65, 45]
                    }
                ]
            }
        }
    
    async def get_full_dashboard(self) -> Dict[str, Any]:
        """Get full executive dashboard"""
        return {
            'generated_at': datetime.utcnow().isoformat(),
            'period': {
                'days': 30,
                'start': (datetime.utcnow() - timedelta(days=30)).isoformat(),
                'end': datetime.utcnow().isoformat()
            },
            'kpis': await self.get_kpi_cards(),
            'charts': await self.get_charts(),
            'portfolio': await self.get_portfolio_overview(),
            'revenue': await self.get_revenue_metrics(),
            'customers': await self.get_customer_metrics(),
            'product': await self.get_product_metrics(),
            'operational': await self.get_operational_metrics(),
            'forecast': await self.get_financial_forecast()
        }


# Global executive dashboard
executive_dashboard = ExecutiveDashboard()
