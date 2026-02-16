"""
Cost Optimization - Cloud Resource Cost Management
Tools for monitoring and optimizing cloud infrastructure costs.
"""

import os
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of cloud resources."""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    LOAD_BALANCER = "load_balancer"
    CONTAINER_REGISTRY = "container_registry"
    LOGGING = "logging"
    MONITORING = "monitoring"


@dataclass
class CostBreakdown:
    """Cost breakdown by resource type."""
    resource_type: ResourceType
    daily_cost: float
    monthly_cost: float
    yearly_cost: float
    percentage: float
    trend: str  # 'up', 'down', 'stable'


@dataclass
class ResourceUtilization:
    """Resource utilization metrics."""
    resource_id: str
    resource_type: ResourceType
    cpu_utilization: float
    memory_utilization: float
    disk_utilization: float
    network_utilization: float
    cost_per_hour: float
    recommendation: Optional[str]


@dataclass
class CostAlert:
    """Cost alert configuration."""
    alert_id: str
    name: str
    threshold_amount: float
    threshold_percentage: Optional[float]
    period: str  # 'daily', 'weekly', 'monthly'
    notification_channels: List[str]
    enabled: bool


class CostAnalyzer:
    """Analyze cloud infrastructure costs."""
    
    def __init__(self, cloud_provider: str = "gcp"):
        self.cloud_provider = cloud_provider
        self.logger = logging.getLogger(__name__)
    
    def get_cost_breakdown(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[CostBreakdown]:
        """Get cost breakdown by resource type."""
        # In production, would query cloud billing API
        
        # Mock data
        breakdowns = [
            CostBreakdown(
                resource_type=ResourceType.COMPUTE,
                daily_cost=450.0,
                monthly_cost=13500.0,
                yearly_cost=162000.0,
                percentage=45.0,
                trend='up'
            ),
            CostBreakdown(
                resource_type=ResourceType.DATABASE,
                daily_cost=200.0,
                monthly_cost=6000.0,
                yearly_cost=72000.0,
                percentage=20.0,
                trend='stable'
            ),
            CostBreakdown(
                resource_type=ResourceType.STORAGE,
                daily_cost=150.0,
                monthly_cost=4500.0,
                yearly_cost=54000.0,
                percentage=15.0,
                trend='up'
            ),
            CostBreakdown(
                resource_type=ResourceType.NETWORK,
                daily_cost=100.0,
                monthly_cost=3000.0,
                yearly_cost=36000.0,
                percentage=10.0,
                trend='stable'
            ),
            CostBreakdown(
                resource_type=ResourceType.LOAD_BALANCER,
                daily_cost=50.0,
                monthly_cost=1500.0,
                yearly_cost=18000.0,
                percentage=5.0,
                trend='stable'
            ),
            CostBreakdown(
                resource_type=ResourceType.LOGGING,
                daily_cost=30.0,
                monthly_cost=900.0,
                yearly_cost=10800.0,
                percentage=3.0,
                trend='up'
            ),
            CostBreakdown(
                resource_type=ResourceType.MONITORING,
                daily_cost=20.0,
                monthly_cost=600.0,
                yearly_cost=7200.0,
                percentage=2.0,
                trend='stable'
            )
        ]
        
        return breakdowns
    
    def get_resource_utilization(self) -> List[ResourceUtilization]:
        """Get resource utilization for cost optimization."""
        # Mock data
        return [
            ResourceUtilization(
                resource_id="gke-node-pool-1",
                resource_type=ResourceType.COMPUTE,
                cpu_utilization=25.0,
                memory_utilization=40.0,
                disk_utilization=30.0,
                network_utilization=15.0,
                cost_per_hour=5.0,
                recommendation="Consider downsizing or using preemptible instances"
            ),
            ResourceUtilization(
                resource_id="postgres-primary",
                resource_type=ResourceType.DATABASE,
                cpu_utilization=35.0,
                memory_utilization=60.0,
                disk_utilization=45.0,
                network_utilization=20.0,
                cost_per_hour=2.5,
                recommendation=None
            ),
            ResourceUtilization(
                resource_id="redis-cache",
                resource_type=ResourceType.DATABASE,
                cpu_utilization=15.0,
                memory_utilization=25.0,
                disk_utilization=0.0,
                network_utilization=80.0,
                cost_per_hour=1.0,
                recommendation="Consider using smaller instance or Redis Cluster"
            )
        ]
    
    def identify_cost_anomalies(
        self,
        lookback_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Identify unusual cost patterns."""
        # Mock anomalies
        return [
            {
                'resource_type': 'compute',
                'description': 'Compute costs increased 50% vs last week',
                'current_cost': 450.0,
                'expected_cost': 300.0,
                'difference': 150.0,
                'severity': 'high'
            },
            {
                'resource_type': 'storage',
                'description': 'Storage costs trending upward',
                'current_cost': 150.0,
                'expected_cost': 120.0,
                'difference': 30.0,
                'severity': 'medium'
            }
        ]
    
    def generate_cost_forecast(
        self,
        months_ahead: int = 3
    ) -> Dict[str, Any]:
        """Generate cost forecast."""
        current_monthly = 30000.0
        
        # Simple linear projection with growth
        growth_rate = 0.05  # 5% monthly growth
        
        forecast = []
        for i in range(1, months_ahead + 1):
            projected = current_monthly * ((1 + growth_rate) ** i)
            forecast.append({
                'month': i,
                'projected_cost': projected
            })
        
        return {
            'current_monthly': current_monthly,
            'forecast': forecast,
            'yearly_projection': sum(f['projected_cost'] for f in forecast) * 4
        }


class CostOptimizer:
    """Optimize cloud infrastructure costs."""
    
    def __init__(self, analyzer: CostAnalyzer):
        self.analyzer = analyzer
        self.logger = logging.getLogger(__name__)
        self.optimizations: List[Dict[str, Any]] = []
    
    def analyze_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """Analyze and identify cost optimization opportunities."""
        opportunities = []
        
        # Get utilization data
        utilization = self.analyzer.get_resource_utilization()
        
        # Identify underutilized resources
        for resource in utilization:
            if resource.cpu_utilization < 30 and resource.memory_utilization < 40:
                opportunities.append({
                    'type': 'rightsizing',
                    'resource_id': resource.resource_id,
                    'resource_type': resource.resource_type.value,
                    'current_cost_per_hour': resource.cost_per_hour,
                    'potential_savings_per_hour': resource.cost_per_hour * 0.3,
                    'recommendation': f"Downsize {resource.resource_id} - low utilization detected",
                    'priority': 'high' if resource.cpu_utilization < 20 else 'medium'
                })
        
        # Check for idle resources
        opportunities.extend(self._find_idle_resources())
        
        # Check for reserved instance opportunities
        opportunities.extend(self._analyze_ri_opportunities())
        
        # Check for storage optimization
        opportunities.extend(self._analyze_storage_costs())
        
        return opportunities
    
    def _find_idle_resources(self) -> List[Dict[str, Any]]:
        """Find idle or unused resources."""
        # Mock idle resources
        return [
            {
                'type': 'idle_resource',
                'resource_id': 'unused-disk-001',
                'resource_type': 'storage',
                'current_cost_per_hour': 0.5,
                'potential_savings_per_hour': 0.5,
                'recommendation': 'Delete unused persistent disk',
                'priority': 'high'
            },
            {
                'type': 'idle_resource',
                'resource_id': 'old-snapshot-backup',
                'resource_type': 'storage',
                'current_cost_per_hour': 0.2,
                'potential_savings_per_hour': 0.2,
                'recommendation': 'Remove old snapshots (>90 days)',
                'priority': 'medium'
            }
        ]
    
    def _analyze_ri_opportunities(self) -> List[Dict[str, Any]]:
        """Analyze reserved instance/commitment opportunities."""
        return [
            {
                'type': 'reserved_capacity',
                'resource_type': 'compute',
                'current_cost_per_hour': 5.0,
                'reserved_cost_per_hour': 3.5,
                'potential_savings_per_hour': 1.5,
                'savings_percentage': 30.0,
                'recommendation': 'Purchase 1-year committed use discount for GKE nodes',
                'priority': 'high'
            }
        ]
    
    def _analyze_storage_costs(self) -> List[Dict[str, Any]]:
        """Analyze storage cost optimization opportunities."""
        return [
            {
                'type': 'storage_class',
                'resource_id': 'logs-bucket',
                'current_class': 'standard',
                'recommended_class': 'nearline',
                'current_cost_per_month': 500.0,
                'potential_savings_per_month': 200.0,
                'recommendation': 'Move infrequently accessed logs to Nearline storage',
                'priority': 'medium'
            }
        ]
    
    def calculate_total_savings_potential(self) -> Dict[str, float]:
        """Calculate total savings potential."""
        opportunities = self.analyze_optimization_opportunities()
        
        total_hourly = sum(
            o.get('potential_savings_per_hour', 0)
            for o in opportunities
        )
        
        total_monthly = sum(
            o.get('potential_savings_per_month', 0)
            for o in opportunities
        )
        
        return {
            'hourly_savings': total_hourly,
            'daily_savings': total_hourly * 24,
            'monthly_savings': total_monthly + (total_hourly * 24 * 30),
            'yearly_savings': (total_monthly + (total_hourly * 24 * 30)) * 12,
            'opportunity_count': len(opportunities)
        }


class CostAlertManager:
    """Manage cost alerts and notifications."""
    
    def __init__(self):
        self.alerts: List[CostAlert] = []
        self.logger = logging.getLogger(__name__)
        self.notification_handlers: Dict[str, Callable] = {}
    
    def register_notification_handler(self, channel: str, handler: Callable):
        """Register notification handler for a channel."""
        self.notification_handlers[channel] = handler
    
    def create_alert(
        self,
        name: str,
        threshold_amount: float,
        period: str = 'monthly',
        threshold_percentage: Optional[float] = None,
        notification_channels: List[str] = None
    ) -> CostAlert:
        """Create cost alert."""
        alert = CostAlert(
            alert_id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            threshold_amount=threshold_amount,
            threshold_percentage=threshold_percentage,
            period=period,
            notification_channels=notification_channels or ['email'],
            enabled=True
        )
        
        self.alerts.append(alert)
        return alert
    
    def check_alerts(self, current_costs: Dict[str, float]):
        """Check if any alerts should be triggered."""
        for alert in self.alerts:
            if not alert.enabled:
                continue
            
            current = current_costs.get(alert.period, 0)
            
            # Check absolute threshold
            if current >= alert.threshold_amount:
                self._trigger_alert(alert, current, 'amount')
            
            # Check percentage threshold
            if alert.threshold_percentage:
                # Would compare to historical average
                pass
    
    def _trigger_alert(
        self,
        alert: CostAlert,
        current_value: float,
        threshold_type: str
    ):
        """Trigger alert notification."""
        message = {
            'alert_id': alert.alert_id,
            'alert_name': alert.name,
            'current_value': current_value,
            'threshold': alert.threshold_amount if threshold_type == 'amount' else alert.threshold_percentage,
            'threshold_type': threshold_type,
            'period': alert.period,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for channel in alert.notification_channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    handler(message)
                except Exception as e:
                    self.logger.error(f"Notification handler failed for {channel}: {e}")


class BudgetManager:
    """Manage cloud budgets and spending limits."""
    
    def __init__(self):
        self.budgets: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_budget(
        self,
        name: str,
        amount: float,
        period: str = 'monthly',
        alert_thresholds: List[float] = None
    ):
        """Create spending budget."""
        self.budgets[name] = {
            'name': name,
            'amount': amount,
            'period': period,
            'alert_thresholds': alert_thresholds or [50, 80, 100],
            'created_at': datetime.utcnow().isoformat(),
            'alerts_triggered': []
        }
    
    def check_budget(self, name: str, current_spend: float) -> List[Dict[str, Any]]:
        """Check budget status and return triggered alerts."""
        budget = self.budgets.get(name)
        if not budget:
            return []
        
        percentage = (current_spend / budget['amount']) * 100
        triggered = []
        
        for threshold in budget['alert_thresholds']:
            if percentage >= threshold and threshold not in budget['alerts_triggered']:
                budget['alerts_triggered'].append(threshold)
                triggered.append({
                    'budget_name': name,
                    'threshold_percentage': threshold,
                    'current_percentage': percentage,
                    'current_spend': current_spend,
                    'budget_amount': budget['amount'],
                    'message': f"Budget '{name}' has reached {threshold}% of limit"
                })
        
        return triggered
    
    def get_budget_status(self, name: str, current_spend: float) -> Dict[str, Any]:
        """Get current budget status."""
        budget = self.budgets.get(name)
        if not budget:
            return {'error': 'Budget not found'}
        
        percentage = (current_spend / budget['amount']) * 100
        
        return {
            'name': name,
            'budget_amount': budget['amount'],
            'current_spend': current_spend,
            'remaining': budget['amount'] - current_spend,
            'percentage_used': percentage,
            'status': 'over' if percentage > 100 else 'at_risk' if percentage > 80 else 'ok'
        }


# Usage recommendations
class UsageRecommendations:
    """Generate usage-based cost recommendations."""
    
    @staticmethod
    def get_compute_recommendations(utilization: ResourceUtilization) -> List[str]:
        """Get compute optimization recommendations."""
        recommendations = []
        
        if utilization.cpu_utilization < 20:
            recommendations.append(
                f"Consider using smaller instance type or consolidating workloads"
            )
        
        if utilization.cpu_utilization < 30 and utilization.memory_utilization < 40:
            recommendations.append(
                f"Consider using preemptible/spot instances for non-critical workloads"
            )
        
        if utilization.cpu_utilization > 80:
            recommendations.append(
                f"Consider scaling up or load balancing to prevent performance issues"
            )
        
        return recommendations
    
    @staticmethod
    def get_storage_recommendations(
        total_storage_gb: float,
        access_pattern: str  # 'frequent', 'infrequent', 'archive'
    ) -> List[str]:
        """Get storage optimization recommendations."""
        recommendations = []
        
        if access_pattern == 'infrequent' and total_storage_gb > 100:
            recommendations.append(
                "Move infrequently accessed data to Nearline or Coldline storage"
            )
        
        if access_pattern == 'archive':
            recommendations.append(
                "Use Archive storage for long-term retention"
            )
        
        return recommendations
