"""
Coordination Dashboard - Coordination Health Metrics
Provides real-time metrics and KPIs for project coordination.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from .clash_detection import ClashResult, Clash, ClashStatus, ClashSeverity
from .model_quality import ValidationResult

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Overall health status."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class CoordinationMetric:
    """A single coordination metric."""
    name: str
    value: float
    unit: str
    target: float
    status: HealthStatus
    trend: str  # 'up', 'down', 'stable'
    history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CoordinationHealth:
    """Overall coordination health snapshot."""
    project_id: str
    timestamp: datetime
    overall_status: HealthStatus
    overall_score: float
    metrics: Dict[str, CoordinationMetric]
    alerts: List[Dict[str, Any]]
    recommendations: List[str]


class CoordinationDashboard:
    """Dashboard for coordination health monitoring."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.clash_results: List[ClashResult] = []
        self.validation_results: List[ValidationResult] = []
        self.metric_history: List[CoordinationHealth] = []
    
    def add_clash_result(self, result: ClashResult):
        """Add a clash detection result."""
        self.clash_results.append(result)
    
    def add_validation_result(self, result: ValidationResult):
        """Add a model validation result."""
        self.validation_results.append(result)
    
    def calculate_health(self) -> CoordinationHealth:
        """Calculate overall coordination health."""
        timestamp = datetime.utcnow()
        
        # Calculate individual metrics
        metrics = {
            'clash_density': self._calculate_clash_density(),
            'model_quality': self._calculate_model_quality(),
            'resolution_rate': self._calculate_resolution_rate(),
            'response_time': self._calculate_response_time(),
            'discipline_alignment': self._calculate_discipline_alignment(),
        }
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metrics)
        overall_status = self._score_to_status(overall_score)
        
        # Generate alerts
        alerts = self._generate_alerts(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, alerts)
        
        health = CoordinationHealth(
            project_id=self.project_id,
            timestamp=timestamp,
            overall_status=overall_status,
            overall_score=overall_score,
            metrics=metrics,
            alerts=alerts,
            recommendations=recommendations
        )
        
        self.metric_history.append(health)
        
        return health
    
    def _calculate_clash_density(self) -> CoordinationMetric:
        """Calculate clash density metric."""
        if not self.clash_results:
            return CoordinationMetric(
                name="Clash Density",
                value=0.0,
                unit="clashes/1000 elements",
                target=5.0,
                status=HealthStatus.EXCELLENT,
                trend="stable"
            )
        
        latest = self.clash_results[-1]
        
        if latest.total_elements_checked > 0:
            density = (latest.clash_count / latest.total_elements_checked) * 1000
        else:
            density = 0.0
        
        # Determine status
        if density < 5:
            status = HealthStatus.EXCELLENT
        elif density < 15:
            status = HealthStatus.GOOD
        elif density < 30:
            status = HealthStatus.FAIR
        elif density < 50:
            status = HealthStatus.POOR
        else:
            status = HealthStatus.CRITICAL
        
        # Calculate trend
        trend = "stable"
        if len(self.clash_results) >= 2:
            prev = self.clash_results[-2]
            if prev.total_elements_checked > 0:
                prev_density = (prev.clash_count / prev.total_elements_checked) * 1000
                if density < prev_density:
                    trend = "down"  # Improving
                elif density > prev_density:
                    trend = "up"    # Worsening
        
        return CoordinationMetric(
            name="Clash Density",
            value=round(density, 2),
            unit="clashes/1000 elements",
            target=5.0,
            status=status,
            trend=trend
        )
    
    def _calculate_model_quality(self) -> CoordinationMetric:
        """Calculate model quality metric."""
        if not self.validation_results:
            return CoordinationMetric(
                name="Model Quality",
                value=100.0,
                unit="score",
                target=90.0,
                status=HealthStatus.EXCELLENT,
                trend="stable"
            )
        
        latest = self.validation_results[-1]
        score = latest.score
        
        # Determine status
        if score >= 95:
            status = HealthStatus.EXCELLENT
        elif score >= 85:
            status = HealthStatus.GOOD
        elif score >= 70:
            status = HealthStatus.FAIR
        elif score >= 50:
            status = HealthStatus.POOR
        else:
            status = HealthStatus.CRITICAL
        
        # Calculate trend
        trend = "stable"
        if len(self.validation_results) >= 2:
            prev = self.validation_results[-2]
            if score > prev.score:
                trend = "up"
            elif score < prev.score:
                trend = "down"
        
        return CoordinationMetric(
            name="Model Quality",
            value=score,
            unit="score",
            target=90.0,
            status=status,
            trend=trend
        )
    
    def _calculate_resolution_rate(self) -> CoordinationMetric:
        """Calculate clash resolution rate."""
        if not self.clash_results:
            return CoordinationMetric(
                name="Resolution Rate",
                value=100.0,
                unit="%",
                target=95.0,
                status=HealthStatus.EXCELLENT,
                trend="stable"
            )
        
        # Get all unique clashes
        all_clashes = {}
        for result in self.clash_results:
            for clash in result.clashes:
                all_clashes[clash.id] = clash
        
        if not all_clashes:
            resolution_rate = 100.0
        else:
            resolved = sum(1 for c in all_clashes.values() 
                          if c.status == ClashStatus.RESOLVED)
            resolution_rate = (resolved / len(all_clashes)) * 100
        
        # Determine status
        if resolution_rate >= 95:
            status = HealthStatus.EXCELLENT
        elif resolution_rate >= 80:
            status = HealthStatus.GOOD
        elif resolution_rate >= 60:
            status = HealthStatus.FAIR
        elif resolution_rate >= 40:
            status = HealthStatus.POOR
        else:
            status = HealthStatus.CRITICAL
        
        return CoordinationMetric(
            name="Resolution Rate",
            value=round(resolution_rate, 1),
            unit="%",
            target=95.0,
            status=status,
            trend="stable"
        )
    
    def _calculate_response_time(self) -> CoordinationMetric:
        """Calculate average response time to new clashes."""
        # Placeholder - would calculate from clash timestamps
        return CoordinationMetric(
            name="Response Time",
            value=2.5,
            unit="days",
            target=3.0,
            status=HealthStatus.GOOD,
            trend="stable"
        )
    
    def _calculate_discipline_alignment(self) -> CoordinationMetric:
        """Calculate cross-discipline coordination alignment."""
        if not self.clash_results:
            return CoordinationMetric(
                name="Discipline Alignment",
                value=100.0,
                unit="%",
                target=90.0,
                status=HealthStatus.EXCELLENT,
                trend="stable"
            )
        
        latest = self.clash_results[-1]
        
        # Count cross-discipline vs same-discipline clashes
        cross_discipline = sum(1 for c in latest.clashes if c.is_cross_discipline)
        total = len(latest.clashes)
        
        if total > 0:
            # Lower cross-discipline clash rate is better
            alignment = 100 - (cross_discipline / total * 100)
        else:
            alignment = 100.0
        
        # Determine status
        if alignment >= 90:
            status = HealthStatus.EXCELLENT
        elif alignment >= 75:
            status = HealthStatus.GOOD
        elif alignment >= 60:
            status = HealthStatus.FAIR
        elif alignment >= 40:
            status = HealthStatus.POOR
        else:
            status = HealthStatus.CRITICAL
        
        return CoordinationMetric(
            name="Discipline Alignment",
            value=round(alignment, 1),
            unit="%",
            target=90.0,
            status=status,
            trend="stable"
        )
    
    def _calculate_overall_score(self, metrics: Dict[str, CoordinationMetric]) -> float:
        """Calculate overall coordination score."""
        weights = {
            'clash_density': 0.30,
            'model_quality': 0.25,
            'resolution_rate': 0.25,
            'response_time': 0.10,
            'discipline_alignment': 0.10
        }
        
        score = 0.0
        for key, metric in metrics.items():
            weight = weights.get(key, 0.1)
            
            # Normalize metrics to 0-100 scale
            if key == 'clash_density':
                # Lower is better, invert
                normalized = max(0, 100 - metric.value * 2)
            elif key == 'response_time':
                # Lower is better, invert
                normalized = max(0, 100 - metric.value * 20)
            else:
                normalized = metric.value
            
            score += normalized * weight
        
        return round(score, 1)
    
    def _score_to_status(self, score: float) -> HealthStatus:
        """Convert score to health status."""
        if score >= 90:
            return HealthStatus.EXCELLENT
        elif score >= 75:
            return HealthStatus.GOOD
        elif score >= 60:
            return HealthStatus.FAIR
        elif score >= 40:
            return HealthStatus.POOR
        else:
            return HealthStatus.CRITICAL
    
    def _generate_alerts(self, metrics: Dict[str, CoordinationMetric]) -> List[Dict[str, Any]]:
        """Generate alerts based on metrics."""
        alerts = []
        
        for key, metric in metrics.items():
            if metric.status in [HealthStatus.POOR, HealthStatus.CRITICAL]:
                alerts.append({
                    'severity': 'critical' if metric.status == HealthStatus.CRITICAL else 'warning',
                    'metric': metric.name,
                    'message': f"{metric.name} is {metric.status.value}: {metric.value} {metric.unit}",
                    'target': f"Target: {metric.target} {metric.unit}"
                })
        
        return alerts
    
    def _generate_recommendations(self, metrics: Dict[str, CoordinationMetric],
                                  alerts: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on metrics and alerts."""
        recommendations = []
        
        clash_density = metrics.get('clash_density')
        if clash_density and clash_density.status in [HealthStatus.POOR, HealthStatus.CRITICAL]:
            recommendations.append(
                "Schedule weekly clash detection runs and assign resolution responsibilities"
            )
        
        model_quality = metrics.get('model_quality')
        if model_quality and model_quality.status in [HealthStatus.POOR, HealthStatus.CRITICAL]:
            recommendations.append(
                "Implement model validation gates before model submission"
            )
        
        resolution_rate = metrics.get('resolution_rate')
        if resolution_rate and resolution_rate.status in [HealthStatus.POOR, HealthStatus.CRITICAL]:
            recommendations.append(
                "Establish clash resolution workflow with clear SLAs"
            )
        
        discipline = metrics.get('discipline_alignment')
        if discipline and discipline.status in [HealthStatus.POOR, HealthStatus.CRITICAL]:
            recommendations.append(
                "Schedule coordination meetings between disciplines with high clash rates"
            )
        
        if not recommendations:
            recommendations.append("Continue current coordination practices")
        
        return recommendations
    
    def get_trend_data(self, days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """Get trend data for dashboard charts."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_history = [h for h in self.metric_history if h.timestamp >= cutoff]
        
        return {
            'overall_score': [
                {'date': h.timestamp.isoformat(), 'value': h.overall_score}
                for h in recent_history
            ],
            'clash_count': [
                {'date': r.run_at.isoformat(), 'value': r.clash_count}
                for r in self.clash_results[-days:]
            ],
            'model_quality': [
                {'date': r.validated_at.isoformat(), 'value': r.score}
                for r in self.validation_results[-days:]
            ]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dashboard to dictionary."""
        health = self.calculate_health()
        
        return {
            'project_id': self.project_id,
            'timestamp': health.timestamp.isoformat(),
            'overall_status': health.overall_status.value,
            'overall_score': health.overall_score,
            'metrics': {
                name: {
                    'value': m.value,
                    'unit': m.unit,
                    'target': m.target,
                    'status': m.status.value,
                    'trend': m.trend
                }
                for name, m in health.metrics.items()
            },
            'alerts': health.alerts,
            'recommendations': health.recommendations
        }
