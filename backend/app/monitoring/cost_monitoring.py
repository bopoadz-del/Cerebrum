"""
Cloud Cost Monitoring
Cost tracking, optimization, and alerting for cloud resources
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

import boto3
from google.cloud import billing_v1
from azure.mgmt.consumption import ConsumptionManagementClient
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class CostAlertType(Enum):
    """Types of cost alerts"""
    BUDGET_THRESHOLD = 'budget_threshold'
    ANOMALY_DETECTED = 'anomaly_detected'
    RESOURCE_UNUSED = 'resource_unused'
    RATE_INCREASE = 'rate_increase'


@dataclass
class CostBreakdown:
    """Cost breakdown by category"""
    service: str
    resource_type: str
    region: str
    amount: float
    currency: str = 'USD'
    usage_quantity: float = 0
    usage_unit: str = ''
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Budget:
    """Budget definition"""
    id: str
    name: str
    amount: float
    period: str  # monthly, quarterly, yearly
    alert_thresholds: List[float] = field(default_factory=lambda: [50, 80, 100])
    current_spend: float = 0
    notifications_enabled: bool = True


class AWSCostExplorer:
    """AWS Cost Explorer integration"""
    
    def __init__(self, access_key: str = None, secret_key: str = None, region: str = 'us-east-1'):
        self.client = boto3.client(
            'ce',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    
    async def get_cost_and_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = 'DAILY',
        group_by: List[str] = None
    ) -> Dict[str, Any]:
        """Get cost and usage data"""
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity=granularity,
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': g}
                    for g in (group_by or ['SERVICE'])
                ]
            )
            
            return {
                'results_by_time': response.get('ResultsByTime', []),
                'group_definitions': response.get('GroupDefinitions', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting AWS cost data: {e}")
            return {}
    
    async def get_cost_forecast(
        self,
        start_date: datetime,
        end_date: datetime,
        prediction_interval: int = 95
    ) -> Dict[str, Any]:
        """Get cost forecast"""
        try:
            response = self.client.get_cost_forecast(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Metric='BLENDED_COST',
                Granularity='MONTHLY',
                PredictionIntervalLevel=prediction_interval
            )
            
            return {
                'forecast': response.get('Forecast', {}),
                'total': response.get('Total', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting AWS cost forecast: {e}")
            return {}
    
    async def get_rightsizing_recommendations(self) -> List[Dict[str, Any]]:
        """Get EC2 rightsizing recommendations"""
        try:
            response = self.client.get_rightsizing_recommendation(
                Service='AmazonEC2'
            )
            
            return response.get('RightsizingRecommendations', [])
            
        except Exception as e:
            logger.error(f"Error getting rightsizing recommendations: {e}")
            return []


class GCPCostClient:
    """Google Cloud Billing API client"""
    
    def __init__(self, project_id: str, credentials_path: str = None):
        self.project_id = project_id
        self.client = billing_v1.CloudBillingClient()
    
    async def get_billing_info(self) -> Dict[str, Any]:
        """Get billing account information"""
        try:
            name = f"projects/{self.project_id}/billingInfo"
            response = self.client.get_project_billing_info(name=name)
            
            return {
                'billing_account_name': response.billing_account_name,
                'billing_enabled': response.billing_enabled
            }
            
        except Exception as e:
            logger.error(f"Error getting GCP billing info: {e}")
            return {}


class CostAnalyzer:
    """Analyze and optimize costs"""
    
    def __init__(self):
        self.aws_client: Optional[AWSCostExplorer] = None
        self.gcp_client: Optional[GCPCostClient] = None
        self.budgets: Dict[str, Budget] = {}
        self.cost_history: List[Dict[str, Any]] = []
    
    def initialize(self):
        """Initialize cost clients"""
        if settings.AWS_ACCESS_KEY_ID:
            self.aws_client = AWSCostExplorer(
                settings.AWS_ACCESS_KEY_ID,
                settings.AWS_SECRET_ACCESS_KEY
            )
        
        if settings.GCP_PROJECT_ID:
            self.gcp_client = GCPCostClient(settings.GCP_PROJECT_ID)
    
    async def get_current_month_costs(self) -> Dict[str, Any]:
        """Get current month costs"""
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        costs = {
            'period': {
                'start': start_of_month.isoformat(),
                'end': now.isoformat()
            },
            'total': 0,
            'by_service': {},
            'by_region': {},
            'forecast': None
        }
        
        if self.aws_client:
            aws_costs = await self.aws_client.get_cost_and_usage(
                start_date=start_of_month,
                end_date=now,
                group_by=['SERVICE', 'REGION']
            )
            
            # Process AWS costs
            for result in aws_costs.get('results_by_time', []):
                for group in result.get('Groups', []):
                    keys = group.get('Keys', [])
                    metrics = group.get('Metrics', {})
                    
                    amount = float(metrics.get('BlendedCost', {}).get('Amount', 0))
                    costs['total'] += amount
                    
                    if len(keys) >= 1:
                        service = keys[0]
                        costs['by_service'][service] = costs['by_service'].get(service, 0) + amount
                    
                    if len(keys) >= 2:
                        region = keys[1]
                        costs['by_region'][region] = costs['by_region'].get(region, 0) + amount
        
        return costs
    
    async def get_cost_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get cost trends over time"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        trends = {
            'daily_costs': [],
            'average_daily': 0,
            'trend_direction': 'stable'
        }
        
        if self.aws_client:
            aws_data = await self.aws_client.get_cost_and_usage(
                start_date=start_date,
                end_date=end_date,
                granularity='DAILY'
            )
            
            daily_costs = []
            for result in aws_data.get('results_by_time', []):
                date = result.get('TimePeriod', {}).get('Start')
                total = sum(
                    float(g.get('Metrics', {}).get('BlendedCost', {}).get('Amount', 0))
                    for g in result.get('Groups', [])
                ) or float(result.get('Total', {}).get('BlendedCost', {}).get('Amount', 0))
                
                daily_costs.append({'date': date, 'cost': total})
            
            trends['daily_costs'] = daily_costs
            
            if daily_costs:
                trends['average_daily'] = sum(d['cost'] for d in daily_costs) / len(daily_costs)
                
                # Calculate trend
                if len(daily_costs) >= 7:
                    first_week = sum(d['cost'] for d in daily_costs[:7]) / 7
                    last_week = sum(d['cost'] for d in daily_costs[-7:]) / 7
                    
                    change_pct = ((last_week - first_week) / first_week) * 100
                    
                    if change_pct > 10:
                        trends['trend_direction'] = 'increasing'
                    elif change_pct < -10:
                        trends['trend_direction'] = 'decreasing'
        
        return trends
    
    async def detect_cost_anomalies(self, threshold_pct: float = 20) -> List[Dict[str, Any]]:
        """Detect cost anomalies"""
        anomalies = []
        
        trends = await self.get_cost_trends(days=30)
        daily_costs = trends.get('daily_costs', [])
        
        if len(daily_costs) < 7:
            return anomalies
        
        # Calculate rolling average
        for i in range(7, len(daily_costs)):
            current = daily_costs[i]['cost']
            avg_prev = sum(d['cost'] for d in daily_costs[i-7:i]) / 7
            
            if avg_prev > 0:
                change_pct = abs((current - avg_prev) / avg_prev) * 100
                
                if change_pct > threshold_pct:
                    anomalies.append({
                        'date': daily_costs[i]['date'],
                        'cost': current,
                        'expected': avg_prev,
                        'variance_percent': change_pct,
                        'type': 'spike' if current > avg_prev else 'drop'
                    })
        
        return anomalies
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get cost optimization recommendations"""
        recommendations = []
        
        # Get AWS rightsizing recommendations
        if self.aws_client:
            aws_recs = await self.aws_client.get_rightsizing_recommendations()
            
            for rec in aws_recs:
                current = rec.get('CurrentInstance', {})
                recommended = rec.get('RecommendedInstance', {})
                
                savings = float(rec.get('EstimatedMonthlySavings', 0))
                
                if savings > 0:
                    recommendations.append({
                        'type': 'rightsizing',
                        'provider': 'aws',
                        'resource_id': current.get('ResourceId'),
                        'current_type': current.get('InstanceType'),
                        'recommended_type': recommended.get('InstanceType'),
                        'estimated_monthly_savings': savings,
                        'savings_percent': rec.get('EstimatedSavingsPercentage', 0)
                    })
        
        # Sort by savings
        recommendations.sort(key=lambda x: x['estimated_monthly_savings'], reverse=True)
        
        return recommendations
    
    def create_budget(self, budget: Budget) -> str:
        """Create a cost budget"""
        self.budgets[budget.id] = budget
        return budget.id
    
    async def check_budgets(self) -> List[Dict[str, Any]]:
        """Check budget status and generate alerts"""
        alerts = []
        
        current_costs = await self.get_current_month_costs()
        total_spend = current_costs.get('total', 0)
        
        for budget in self.budgets.values():
            budget.current_spend = total_spend
            
            spend_pct = (total_spend / budget.amount) * 100
            
            for threshold in budget.alert_thresholds:
                if spend_pct >= threshold:
                    alerts.append({
                        'budget_id': budget.id,
                        'budget_name': budget.name,
                        'threshold_percent': threshold,
                        'current_spend': total_spend,
                        'budget_amount': budget.amount,
                        'spend_percent': spend_pct,
                        'severity': 'critical' if threshold >= 100 else 'warning' if threshold >= 80 else 'info'
                    })
        
        return alerts
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary for dashboard"""
        return {
            'current_month': {
                'total': 0,
                'forecast': 0,
                'budget': sum(b.amount for b in self.budgets.values()),
                'budget_utilization': 0
            },
            'last_month': {
                'total': 0
            },
            'ytd': {
                'total': 0
            },
            'top_services': [],
            'optimization_potential': 0
        }


# Global cost analyzer
cost_analyzer = CostAnalyzer()
