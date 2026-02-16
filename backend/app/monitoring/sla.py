"""
SLA Monitoring & Error Budgets
Service Level Agreement tracking and error budget management
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SLIMetricType(Enum):
    """Service Level Indicator metric types"""
    AVAILABILITY = 'availability'
    LATENCY = 'latency'
    ERROR_RATE = 'error_rate'
    THROUGHPUT = 'throughput'
    DURABILITY = 'durability'


@dataclass
class ServiceLevelIndicator:
    """Service Level Indicator (SLI)"""
    id: str
    name: str
    metric_type: SLIMetricType
    query: str  # Prometheus/Metrics query
    good_threshold: float
    total_threshold: float
    unit: str = ''
    description: str = ''


@dataclass
class ServiceLevelObjective:
    """Service Level Objective (SLO)"""
    id: str
    name: str
    sli: ServiceLevelIndicator
    target: float  # Target percentage (e.g., 99.9)
    window_days: int = 30
    burn_rate_alerts: List[float] = field(default_factory=lambda: [2, 4, 8])
    
    def get_error_budget(self) -> float:
        """Calculate error budget"""
        return 100 - self.target


@dataclass
class ServiceLevelAgreement:
    """Service Level Agreement (SLA)"""
    id: str
    name: str
    slo: ServiceLevelObjective
    penalties: List[Dict[str, Any]] = field(default_factory=list)
    credits_enabled: bool = True


@dataclass
class ErrorBudget:
    """Error budget tracking"""
    slo_id: str
    period_start: datetime
    period_end: datetime
    total_budget: float  # Total error budget in percentage
    consumed: float = 0  # Consumed budget
    remaining: float = 0  # Remaining budget
    
    def __post_init__(self):
        self.remaining = self.total_budget - self.consumed
    
    def consume(self, amount: float):
        """Consume error budget"""
        self.consumed += amount
        self.remaining = max(0, self.total_budget - self.consumed)
    
    def get_burn_rate(self, hours: int = 1) -> float:
        """Get burn rate for the period"""
        period_hours = (self.period_end - self.period_start).total_seconds() / 3600
        if period_hours == 0:
            return 0
        
        expected_rate = self.total_budget / period_hours
        actual_rate = self.consumed / period_hours
        
        return actual_rate / expected_rate if expected_rate > 0 else 0
    
    def get_time_to_exhaustion_hours(self) -> Optional[float]:
        """Calculate time to exhaust error budget"""
        period_hours = (self.period_end - self.period_start).total_seconds() / 3600
        if period_hours == 0 or self.consumed == 0:
            return None
        
        burn_rate = self.consumed / period_hours
        if burn_rate == 0:
            return None
        
        return self.remaining / burn_rate


class SLAMonitor:
    """Monitor SLAs, SLOs, and error budgets"""
    
    def __init__(self):
        self.slis: Dict[str, ServiceLevelIndicator] = {}
        self.slos: Dict[str, ServiceLevelObjective] = {}
        self.slas: Dict[str, ServiceLevelAgreement] = {}
        self.error_budgets: Dict[str, List[ErrorBudget]] = {}
        self._load_default_slo_definitions()
    
    def _load_default_slo_definitions(self):
        """Load default SLO definitions"""
        # Availability SLO
        availability_sli = ServiceLevelIndicator(
            id='sli-availability',
            name='Service Availability',
            metric_type=SLIMetricType.AVAILABILITY,
            query='sum(rate(cerebrum_http_requests_total{status_code!~"5.."}[5m])) / sum(rate(cerebrum_http_requests_total[5m])) * 100',
            good_threshold=99.9,
            total_threshold=100,
            unit='percent',
            description='Percentage of successful requests'
        )
        
        availability_slo = ServiceLevelObjective(
            id='slo-availability',
            name='99.9% Availability',
            sli=availability_sli,
            target=99.9,
            window_days=30
        )
        
        self.slis[availability_sli.id] = availability_sli
        self.slos[availability_slo.id] = availability_slo
        
        # Latency SLO
        latency_sli = ServiceLevelIndicator(
            id='sli-latency',
            name='Request Latency',
            metric_type=SLIMetricType.LATENCY,
            query='histogram_quantile(0.95, rate(cerebrum_http_request_duration_seconds_bucket[5m])) * 1000',
            good_threshold=500,  # 500ms
            total_threshold=5000,
            unit='ms',
            description='P95 request latency'
        )
        
        latency_slo = ServiceLevelObjective(
            id='slo-latency',
            name='P95 < 500ms',
            sli=latency_sli,
            target=95,  # 95% of requests under 500ms
            window_days=30
        )
        
        self.slis[latency_sli.id] = latency_sli
        self.slos[latency_slo.id] = latency_slo
        
        # Error Rate SLO
        error_sli = ServiceLevelIndicator(
            id='sli-error-rate',
            name='Error Rate',
            metric_type=SLIMetricType.ERROR_RATE,
            query='sum(rate(cerebrum_http_requests_total{status_code=~"5.."}[5m])) / sum(rate(cerebrum_http_requests_total[5m])) * 100',
            good_threshold=0.1,
            total_threshold=100,
            unit='percent',
            description='Percentage of error responses'
        )
        
        error_slo = ServiceLevelObjective(
            id='slo-error-rate',
            name='< 0.1% Error Rate',
            sli=error_sli,
            target=99.9,  # 99.9% success rate
            window_days=30
        )
        
        self.slis[error_sli.id] = error_sli
        self.slos[error_slo.id] = error_slo
    
    def create_slo(self, slo: ServiceLevelObjective) -> str:
        """Create a new SLO"""
        self.slos[slo.id] = slo
        return slo.id
    
    def get_slo(self, slo_id: str) -> Optional[ServiceLevelObjective]:
        """Get an SLO by ID"""
        return self.slos.get(slo_id)
    
    def calculate_slo_compliance(
        self,
        slo_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate SLO compliance for a period"""
        slo = self.slos.get(slo_id)
        if not slo:
            return {'error': 'SLO not found'}
        
        # This would query metrics to calculate actual compliance
        # For now, return placeholder
        return {
            'slo_id': slo_id,
            'slo_name': slo.name,
            'target': slo.target,
            'actual': 0,
            'compliance': False,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'error_budget': {
                'total': slo.get_error_budget(),
                'consumed': 0,
                'remaining': slo.get_error_budget()
            }
        }
    
    def get_error_budget(self, slo_id: str, period: datetime = None) -> Optional[ErrorBudget]:
        """Get error budget for an SLO"""
        slo = self.slos.get(slo_id)
        if not slo:
            return None
        
        if period is None:
            period = datetime.utcnow()
        
        # Calculate period
        period_end = period
        period_start = period - timedelta(days=slo.window_days)
        
        # Get or create budget
        budgets = self.error_budgets.get(slo_id, [])
        
        for budget in budgets:
            if budget.period_start <= period <= budget.period_end:
                return budget
        
        # Create new budget
        new_budget = ErrorBudget(
            slo_id=slo_id,
            period_start=period_start,
            period_end=period_end,
            total_budget=slo.get_error_budget(),
            consumed=0
        )
        
        if slo_id not in self.error_budgets:
            self.error_budgets[slo_id] = []
        
        self.error_budgets[slo_id].append(new_budget)
        
        return new_budget
    
    def consume_error_budget(self, slo_id: str, amount: float):
        """Consume error budget"""
        budget = self.get_error_budget(slo_id)
        if budget:
            budget.consume(amount)
    
    def check_burn_rate_alerts(self, slo_id: str) -> List[Dict[str, Any]]:
        """Check for burn rate alerts"""
        slo = self.slos.get(slo_id)
        budget = self.get_error_budget(slo_id)
        
        if not slo or not budget:
            return []
        
        alerts = []
        burn_rate = budget.get_burn_rate()
        
        for threshold in slo.burn_rate_alerts:
            if burn_rate >= threshold:
                alerts.append({
                    'slo_id': slo_id,
                    'slo_name': slo.name,
                    'burn_rate': burn_rate,
                    'threshold': threshold,
                    'severity': 'critical' if threshold >= 8 else 'warning' if threshold >= 4 else 'info',
                    'message': f'Error budget burn rate is {burn_rate:.1f}x (threshold: {threshold}x)',
                    'time_to_exhaustion_hours': budget.get_time_to_exhaustion_hours()
                })
        
        return alerts
    
    def get_sla_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate SLA compliance report"""
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'slos': [],
            'summary': {
                'total_slos': len(self.slos),
                'compliant_slos': 0,
                'at_risk_slos': 0,
                'breached_slos': 0
            }
        }
        
        for slo in self.slos.values():
            compliance = self.calculate_slo_compliance(slo.id, start_date, end_date)
            budget = self.get_error_budget(slo.id, end_date)
            
            slo_report = {
                'id': slo.id,
                'name': slo.name,
                'target': slo.target,
                'actual': compliance.get('actual', 0),
                'compliant': compliance.get('compliance', False),
                'error_budget_remaining': budget.remaining if budget else 0,
                'burn_rate': budget.get_burn_rate() if budget else 0
            }
            
            report['slos'].append(slo_report)
            
            # Update summary
            if slo_report['compliant']:
                report['summary']['compliant_slos'] += 1
            elif slo_report['error_budget_remaining'] <= 0:
                report['summary']['breached_slos'] += 1
            else:
                report['summary']['at_risk_slos'] += 1
        
        return report


# Global SLA monitor
sla_monitor = SLAMonitor()
