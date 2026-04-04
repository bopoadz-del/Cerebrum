"""
ML-Based Anomaly Detection
Machine learning anomaly detection for metrics and logs
"""

import json
import statistics
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """Types of anomalies"""
    POINT = 'point'  # Single point anomaly
    CONTEXTUAL = 'contextual'  # Context-dependent anomaly
    COLLECTIVE = 'collective'  # Sequence of anomalous points
    SEASONAL = 'seasonal'  # Seasonal pattern anomaly


class AnomalySeverity(Enum):
    """Anomaly severity levels"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


@dataclass
class Anomaly:
    """Detected anomaly"""
    id: str
    timestamp: datetime
    metric_name: str
    value: float
    expected_value: float
    deviation: float
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['anomaly_type'] = self.anomaly_type.value
        data['severity'] = self.severity.value
        return data


class StatisticalDetector:
    """Statistical anomaly detection using z-scores"""
    
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold
        self.history: Dict[str, List[float]] = {}
        self.max_history = 1000
    
    def add_point(self, metric_name: str, value: float):
        """Add a data point"""
        if metric_name not in self.history:
            self.history[metric_name] = []
        
        self.history[metric_name].append(value)
        
        # Trim history
        if len(self.history[metric_name]) > self.max_history:
            self.history[metric_name] = self.history[metric_name][-self.max_history:]
    
    def detect(self, metric_name: str, value: float) -> Optional[Anomaly]:
        """Detect anomaly using z-score"""
        if metric_name not in self.history or len(self.history[metric_name]) < 30:
            self.add_point(metric_name, value)
            return None
        
        history = self.history[metric_name]
        
        mean = statistics.mean(history)
        std = statistics.stdev(history) if len(history) > 1 else 0
        
        if std == 0:
            self.add_point(metric_name, value)
            return None
        
        z_score = abs((value - mean) / std)
        
        self.add_point(metric_name, value)
        
        if z_score > self.threshold:
            severity = self._get_severity(z_score)
            
            return Anomaly(
                id=f"stat-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{metric_name}",
                timestamp=datetime.utcnow(),
                metric_name=metric_name,
                value=value,
                expected_value=mean,
                deviation=z_score,
                anomaly_type=AnomalyType.POINT,
                severity=severity,
                context={
                    'z_score': z_score,
                    'mean': mean,
                    'std': std,
                    'threshold': self.threshold
                }
            )
        
        return None
    
    def _get_severity(self, z_score: float) -> AnomalySeverity:
        """Get severity based on z-score"""
        if z_score > 5:
            return AnomalySeverity.CRITICAL
        elif z_score > 4:
            return AnomalySeverity.HIGH
        elif z_score > 3:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW


class SeasonalDetector:
    """Detect seasonal anomalies"""
    
    def __init__(self, season_length: int = 24):
        self.season_length = season_length
        self.seasonal_patterns: Dict[str, Dict[int, List[float]]] = {}
    
    def add_point(self, metric_name: str, value: float, hour: int):
        """Add a data point with hour information"""
        if metric_name not in self.seasonal_patterns:
            self.seasonal_patterns[metric_name] = {h: [] for h in range(self.season_length)}
        
        self.seasonal_patterns[metric_name][hour].append(value)
    
    def detect(self, metric_name: str, value: float, hour: int) -> Optional[Anomaly]:
        """Detect seasonal anomaly"""
        if metric_name not in self.seasonal_patterns:
            return None
        
        hour_history = self.seasonal_patterns[metric_name].get(hour, [])
        
        if len(hour_history) < 7:  # Need at least a week of data
            return None
        
        mean = statistics.mean(hour_history)
        std = statistics.stdev(hour_history) if len(hour_history) > 1 else 0
        
        if std == 0:
            return None
        
        z_score = abs((value - mean) / std)
        
        if z_score > 3:
            return Anomaly(
                id=f"seas-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{metric_name}",
                timestamp=datetime.utcnow(),
                metric_name=metric_name,
                value=value,
                expected_value=mean,
                deviation=z_score,
                anomaly_type=AnomalyType.SEASONAL,
                severity=AnomalySeverity.HIGH if z_score > 4 else AnomalySeverity.MEDIUM,
                context={
                    'hour': hour,
                    'z_score': z_score,
                    'seasonal_mean': mean
                }
            )
        
        return None


class ChangePointDetector:
    """Detect change points in time series"""
    
    def __init__(self, window_size: int = 30, threshold: float = 2.0):
        self.window_size = window_size
        self.threshold = threshold
        self.history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def add_point(self, metric_name: str, timestamp: datetime, value: float):
        """Add a data point"""
        if metric_name not in self.history:
            self.history[metric_name] = []
        
        self.history[metric_name].append((timestamp, value))
    
    def detect(self, metric_name: str) -> Optional[Anomaly]:
        """Detect change point"""
        if metric_name not in self.history:
            return None
        
        history = self.history[metric_name]
        
        if len(history) < self.window_size * 2:
            return None
        
        # Split into two windows
        window1 = [v for _, v in history[-self.window_size*2:-self.window_size]]
        window2 = [v for _, v in history[-self.window_size:]]
        
        mean1 = statistics.mean(window1)
        mean2 = statistics.mean(window2)
        
        std1 = statistics.stdev(window1) if len(window1) > 1 else 0
        std2 = statistics.stdev(window2) if len(window2) > 1 else 0
        
        if std1 == 0 or std2 == 0:
            return None
        
        # Calculate change magnitude
        change_magnitude = abs(mean2 - mean1) / ((std1 + std2) / 2)
        
        if change_magnitude > self.threshold:
            return Anomaly(
                id=f"cp-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{metric_name}",
                timestamp=datetime.utcnow(),
                metric_name=metric_name,
                value=mean2,
                expected_value=mean1,
                deviation=change_magnitude,
                anomaly_type=AnomalyType.COLLECTIVE,
                severity=AnomalySeverity.HIGH if change_magnitude > 4 else AnomalySeverity.MEDIUM,
                context={
                    'previous_mean': mean1,
                    'new_mean': mean2,
                    'change_magnitude': change_magnitude
                }
            )
        
        return None


class AnomalyDetector:
    """Main anomaly detection system"""
    
    def __init__(self):
        self.statistical = StatisticalDetector()
        self.seasonal = SeasonalDetector()
        self.change_point = ChangePointDetector()
        self.anomalies: List[Anomaly] = []
        self.max_anomalies = 1000
        self.alert_handlers: List[Callable] = []
    
    def detect_metric(
        self,
        metric_name: str,
        value: float,
        timestamp: datetime = None,
        hour: int = None
    ) -> List[Anomaly]:
        """Run all detection algorithms on a metric"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        if hour is None:
            hour = timestamp.hour
        
        detected = []
        
        # Statistical detection
        anomaly = self.statistical.detect(metric_name, value)
        if anomaly:
            detected.append(anomaly)
        
        # Seasonal detection
        self.seasonal.add_point(metric_name, value, hour)
        anomaly = self.seasonal.detect(metric_name, value, hour)
        if anomaly:
            detected.append(anomaly)
        
        # Change point detection
        self.change_point.add_point(metric_name, timestamp, value)
        anomaly = self.change_point.detect(metric_name)
        if anomaly:
            detected.append(anomaly)
        
        # Store and alert
        for anomaly in detected:
            self._store_anomaly(anomaly)
            self._alert_anomaly(anomaly)
        
        return detected
    
    def _store_anomaly(self, anomaly: Anomaly):
        """Store detected anomaly"""
        self.anomalies.append(anomaly)
        
        # Trim old anomalies
        if len(self.anomalies) > self.max_anomalies:
            self.anomalies = self.anomalies[-self.max_anomalies:]
    
    def _alert_anomaly(self, anomaly: Anomaly):
        """Alert on anomaly"""
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(anomaly))
                else:
                    handler(anomaly)
            except Exception as e:
                logger.error(f"Error in anomaly alert handler: {e}")
    
    def on_anomaly(self, handler: Callable):
        """Register anomaly handler"""
        self.alert_handlers.append(handler)
    
    def get_anomalies(
        self,
        metric_name: str = None,
        severity: AnomalySeverity = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get anomalies with filtering"""
        filtered = self.anomalies
        
        if metric_name:
            filtered = [a for a in filtered if a.metric_name == metric_name]
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        
        if start_time:
            filtered = [a for a in filtered if a.timestamp >= start_time]
        
        if end_time:
            filtered = [a for a in filtered if a.timestamp <= end_time]
        
        filtered.sort(key=lambda a: a.timestamp, reverse=True)
        
        return [a.to_dict() for a in filtered[:limit]]
    
    def get_anomaly_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get anomaly summary"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [a for a in self.anomalies if a.timestamp > cutoff]
        
        return {
            'period_hours': hours,
            'total_anomalies': len(recent),
            'by_severity': {
                'critical': sum(1 for a in recent if a.severity == AnomalySeverity.CRITICAL),
                'high': sum(1 for a in recent if a.severity == AnomalySeverity.HIGH),
                'medium': sum(1 for a in recent if a.severity == AnomalySeverity.MEDIUM),
                'low': sum(1 for a in recent if a.severity == AnomalySeverity.LOW)
            },
            'by_type': {
                'point': sum(1 for a in recent if a.anomaly_type == AnomalyType.POINT),
                'seasonal': sum(1 for a in recent if a.anomaly_type == AnomalyType.SEASONAL),
                'collective': sum(1 for a in recent if a.anomaly_type == AnomalyType.COLLECTIVE),
                'contextual': sum(1 for a in recent if a.anomaly_type == AnomalyType.CONTEXTUAL)
            },
            'top_metrics': self._get_top_anomalous_metrics(recent)
        }
    
    def _get_top_anomalous_metrics(self, anomalies: List[Anomaly], limit: int = 5) -> List[Dict[str, Any]]:
        """Get metrics with most anomalies"""
        from collections import Counter
        
        metric_counts = Counter(a.metric_name for a in anomalies)
        
        return [
            {'metric': metric, 'anomaly_count': count}
            for metric, count in metric_counts.most_common(limit)
        ]


# Global anomaly detector
anomaly_detector = AnomalyDetector()
