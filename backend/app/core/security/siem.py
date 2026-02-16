"""
SIEM Integration with Anomaly Detection
Security Information and Event Management integration
"""
import os
import json
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class EventSeverity(Enum):
    """Event severity levels"""
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class EventCategory(Enum):
    """Security event categories"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    DATA_ACCESS = "data_access"
    SYSTEM = "system"
    APPLICATION = "application"
    THREAT = "threat"
    COMPLIANCE = "compliance"


@dataclass
class SecurityEvent:
    """Security event record"""
    event_id: str
    timestamp: datetime
    category: EventCategory
    severity: EventSeverity
    source: str
    message: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    outcome: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyAlert:
    """Anomaly detection alert"""
    alert_id: str
    timestamp: datetime
    anomaly_type: str
    severity: EventSeverity
    description: str
    affected_entities: List[str]
    confidence: float
    baseline_deviation: float
    recommended_actions: List[str]
    related_events: List[str] = field(default_factory=list)


class SIEMConnector:
    """Connector for SIEM platforms"""
    
    SUPPORTED_SIEMS = ['splunk', 'elk', 'sentinel', 'qradar', 'sumo']
    
    def __init__(self, siem_type: str, config: Dict):
        self.siem_type = siem_type.lower()
        self.config = config
        self._connected = False
        self._event_buffer: List[SecurityEvent] = []
        self._buffer_size = config.get('buffer_size', 1000)
        self._flush_interval = config.get('flush_interval', 60)
    
    async def connect(self):
        """Connect to SIEM platform"""
        if self.siem_type not in self.SUPPORTED_SIEMS:
            raise ValueError(f"Unsupported SIEM: {self.siem_type}")
        
        # Platform-specific connection logic
        if self.siem_type == 'splunk':
            await self._connect_splunk()
        elif self.siem_type == 'elk':
            await self._connect_elk()
        elif self.siem_type == 'sentinel':
            await self._connect_sentinel()
        
        self._connected = True
        logger.info(f"Connected to {self.siem_type} SIEM")
    
    async def _connect_splunk(self):
        """Connect to Splunk"""
        import aiohttp
        self._session = aiohttp.ClientSession()
        self._hec_url = f"{self.config['host']}/services/collector/event"
        self._hec_token = self.config['token']
    
    async def _connect_elk(self):
        """Connect to ELK Stack"""
        from elasticsearch import AsyncElasticsearch
        self._es_client = AsyncElasticsearch([self.config['host']])
    
    async def _connect_sentinel(self):
        """Connect to Azure Sentinel"""
        # Azure Sentinel integration
        pass
    
    async def send_event(self, event: SecurityEvent):
        """Send event to SIEM"""
        self._event_buffer.append(event)
        
        if len(self._event_buffer) >= self._buffer_size:
            await self.flush_events()
    
    async def flush_events(self):
        """Flush buffered events to SIEM"""
        if not self._event_buffer:
            return
        
        events_to_send = self._event_buffer[:]
        self._event_buffer = []
        
        try:
            if self.siem_type == 'splunk':
                await self._send_to_splunk(events_to_send)
            elif self.siem_type == 'elk':
                await self._send_to_elk(events_to_send)
            
            logger.info(f"Sent {len(events_to_send)} events to {self.siem_type}")
            
        except Exception as e:
            logger.error(f"Failed to send events to SIEM: {e}")
            # Re-buffer events
            self._event_buffer.extend(events_to_send)
    
    async def _send_to_splunk(self, events: List[SecurityEvent]):
        """Send events to Splunk HEC"""
        import aiohttp
        
        for event in events:
            payload = {
                'time': event.timestamp.timestamp(),
                'source': event.source,
                'sourcetype': f"cerebrum:{event.category.value}",
                'event': {
                    'message': event.message,
                    'severity': event.severity.name,
                    'user_id': event.user_id,
                    'ip_address': event.ip_address,
                    'resource': event.resource,
                    'action': event.action,
                    'outcome': event.outcome,
                    'metadata': event.metadata
                }
            }
            
            headers = {'Authorization': f'Splunk {self._hec_token}'}
            
            async with self._session.post(
                self._hec_url,
                json=payload,
                headers=headers,
                ssl=False
            ) as response:
                if response.status != 200:
                    logger.warning(f"Splunk HEC error: {response.status}")
    
    async def _send_to_elk(self, events: List[SecurityEvent]):
        """Send events to Elasticsearch"""
        from elasticsearch.helpers import async_bulk
        
        actions = []
        for event in events:
            actions.append({
                '_index': f"cerebrum-security-{event.timestamp.strftime('%Y.%m.%d')}",
                '_source': {
                    'timestamp': event.timestamp.isoformat(),
                    'category': event.category.value,
                    'severity': event.severity.name,
                    'source': event.source,
                    'message': event.message,
                    'user_id': event.user_id,
                    'ip_address': event.ip_address,
                    'resource': event.resource,
                    'action': event.action,
                    'outcome': event.outcome,
                    'metadata': event.metadata
                }
            })
        
        await async_bulk(self._es_client, actions)


class AnomalyDetector:
    """Anomaly detection engine"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._baselines: Dict[str, Dict] = {}
        self._event_windows: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size))
        self._detectors: Dict[str, Callable] = {}
        self._alerts: List[AnomalyAlert] = []
    
    def register_detector(self, name: str, detector: Callable):
        """Register anomaly detector"""
        self._detectors[name] = detector
    
    def record_event(self, event: SecurityEvent):
        """Record event for anomaly detection"""
        key = f"{event.category.value}:{event.source}"
        self._event_windows[key].append(event)
        
        # Update baseline
        self._update_baseline(key)
    
    def _update_baseline(self, key: str):
        """Update baseline statistics"""
        window = self._event_windows[key]
        
        if len(window) < 10:
            return
        
        # Calculate baseline metrics
        severities = [e.severity.value for e in window]
        timestamps = [e.timestamp for e in window]
        
        # Calculate event rate
        if len(timestamps) >= 2:
            time_span = (timestamps[-1] - timestamps[0]).total_seconds()
            event_rate = len(window) / time_span if time_span > 0 else 0
        else:
            event_rate = 0
        
        self._baselines[key] = {
            'mean_severity': statistics.mean(severities),
            'std_severity': statistics.stdev(severities) if len(severities) > 1 else 0,
            'event_rate': event_rate,
            'last_updated': datetime.utcnow()
        }
    
    async def detect_anomalies(self) -> List[AnomalyAlert]:
        """Run all anomaly detectors"""
        alerts = []
        
        for detector_name, detector in self._detectors.items():
            try:
                detector_alerts = await detector(self._event_windows, self._baselines)
                alerts.extend(detector_alerts)
            except Exception as e:
                logger.error(f"Detector {detector_name} failed: {e}")
        
        self._alerts.extend(alerts)
        return alerts


class StatisticalAnomalyDetector:
    """Statistical anomaly detection"""
    
    @staticmethod
    async def detect_rate_anomalies(windows: Dict[str, deque],
                                    baselines: Dict[str, Dict]) -> List[AnomalyAlert]:
        """Detect rate-based anomalies"""
        alerts = []
        
        for key, window in windows.items():
            baseline = baselines.get(key)
            if not baseline:
                continue
            
            # Calculate current rate
            recent_events = list(window)[-10:]
            if len(recent_events) < 2:
                continue
            
            time_span = (recent_events[-1].timestamp - recent_events[0].timestamp).total_seconds()
            current_rate = len(recent_events) / time_span if time_span > 0 else 0
            
            baseline_rate = baseline.get('event_rate', 0)
            
            # Check for significant deviation
            if baseline_rate > 0 and current_rate > baseline_rate * 3:
                deviation = (current_rate - baseline_rate) / baseline_rate
                
                alert = AnomalyAlert(
                    alert_id=f"RATE-{key}-{datetime.utcnow().timestamp()}",
                    timestamp=datetime.utcnow(),
                    anomaly_type="event_rate_spike",
                    severity=EventSeverity.HIGH,
                    description=f"Event rate spike detected: {current_rate:.2f} events/sec "
                               f"(baseline: {baseline_rate:.2f})",
                    affected_entities=[key],
                    confidence=min(0.95, deviation / 5),
                    baseline_deviation=deviation,
                    recommended_actions=[
                        "Investigate source of increased events",
                        "Check for potential DDoS attack",
                        "Review system performance"
                    ],
                    related_events=[e.event_id for e in recent_events]
                )
                
                alerts.append(alert)
        
        return alerts
    
    @staticmethod
    async def detect_time_based_anomalies(windows: Dict[str, deque],
                                          baselines: Dict[str, Dict]) -> List[AnomalyAlert]:
        """Detect time-based anomalies (unusual activity times)"""
        alerts = []
        
        for key, window in windows.items():
            recent_events = list(window)[-20:]
            
            # Check for off-hours activity
            off_hours_events = [
                e for e in recent_events 
                if e.timestamp.hour < 6 or e.timestamp.hour > 22
            ]
            
            if len(off_hours_events) > len(recent_events) * 0.5:
                alert = AnomalyAlert(
                    alert_id=f"TIME-{key}-{datetime.utcnow().timestamp()}",
                    timestamp=datetime.utcnow(),
                    anomaly_type="off_hours_activity",
                    severity=EventSeverity.MEDIUM,
                    description=f"Unusual off-hours activity detected: "
                               f"{len(off_hours_events)} events",
                    affected_entities=[key],
                    confidence=0.7,
                    baseline_deviation=2.0,
                    recommended_actions=[
                        "Verify authorized off-hours access",
                        "Review user activity logs",
                        "Check for compromised accounts"
                    ],
                    related_events=[e.event_id for e in off_hours_events]
                )
                
                alerts.append(alert)
        
        return alerts


class MLAnomalyDetector:
    """Machine learning-based anomaly detection"""
    
    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._feature_extractors: Dict[str, Callable] = {}
    
    def register_feature_extractor(self, event_type: str, extractor: Callable):
        """Register feature extractor for event type"""
        self._feature_extractors[event_type] = extractor
    
    async def detect(self, events: List[SecurityEvent]) -> List[AnomalyAlert]:
        """Detect anomalies using ML models"""
        alerts = []
        
        # Group events by category
        by_category = defaultdict(list)
        for event in events:
            by_category[event.category.value].append(event)
        
        # Process each category
        for category, cat_events in by_category.items():
            extractor = self._feature_extractors.get(category)
            if not extractor:
                continue
            
            # Extract features
            features = [extractor(e) for e in cat_events]
            
            # Run detection (placeholder for actual ML model)
            # In practice, this would use trained models
            
        return alerts


class SecurityEventCollector:
    """Collects and processes security events"""
    
    def __init__(self):
        self._events: List[SecurityEvent] = []
        self._handlers: List[Callable] = []
        self._siem_connectors: List[SIEMConnector] = []
        self._anomaly_detector = AnomalyDetector()
    
    def add_handler(self, handler: Callable):
        """Add event handler"""
        self._handlers.append(handler)
    
    def add_siem_connector(self, connector: SIEMConnector):
        """Add SIEM connector"""
        self._siem_connectors.append(connector)
    
    async def collect_event(self, event: SecurityEvent):
        """Collect and process security event"""
        self._events.append(event)
        
        # Send to anomaly detector
        self._anomaly_detector.record_event(event)
        
        # Send to SIEM connectors
        for connector in self._siem_connectors:
            await connector.send_event(event)
        
        # Run handlers
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
    
    async def run_anomaly_detection(self) -> List[AnomalyAlert]:
        """Run anomaly detection and return alerts"""
        return await self._anomaly_detector.detect_anomalies()


class AlertManager:
    """Manages security alerts"""
    
    def __init__(self):
        self._alerts: List[AnomalyAlert] = []
        self._notification_handlers: Dict[str, Callable] = {}
        self._escalation_policies: Dict[str, Dict] = {}
    
    def register_notification_handler(self, channel: str, handler: Callable):
        """Register notification handler"""
        self._notification_handlers[channel] = handler
    
    async def process_alert(self, alert: AnomalyAlert):
        """Process and route alert"""
        self._alerts.append(alert)
        
        # Determine notification channels based on severity
        channels = self._get_notification_channels(alert.severity)
        
        # Send notifications
        for channel in channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.error(f"Notification failed for {channel}: {e}")
    
    def _get_notification_channels(self, severity: EventSeverity) -> List[str]:
        """Get notification channels for severity level"""
        if severity == EventSeverity.CRITICAL:
            return ['pagerduty', 'slack', 'email', 'sms']
        elif severity == EventSeverity.HIGH:
            return ['slack', 'email']
        elif severity == EventSeverity.MEDIUM:
            return ['email']
        else:
            return ['log']


# Register anomaly detectors
anomaly_detector = AnomalyDetector()
anomaly_detector.register_detector(
    "rate_anomalies", 
    StatisticalAnomalyDetector.detect_rate_anomalies
)
anomaly_detector.register_detector(
    "time_anomalies",
    StatisticalAnomalyDetector.detect_time_based_anomalies
)

# Global event collector
event_collector = SecurityEventCollector()
event_collector._anomaly_detector = anomaly_detector

alert_manager = AlertManager()