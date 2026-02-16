"""
Mobile App Monitoring
Firebase Crashlytics integration for mobile app monitoring
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

import httpx
import firebase_admin
from firebase_admin import credentials, crashlytics

from app.core.config import settings

logger = logging.getLogger(__name__)


class CrashSeverity(Enum):
    """Crash severity levels"""
    FATAL = 'fatal'
    NON_FATAL = 'non_fatal'
    ANR = 'anr'  # Application Not Responding


class AppPlatform(Enum):
    """Mobile app platforms"""
    IOS = 'ios'
    ANDROID = 'android'


@dataclass
class CrashReport:
    """Mobile crash report"""
    id: str
    timestamp: datetime
    platform: AppPlatform
    app_version: str
    os_version: str
    device_model: str
    severity: CrashSeverity
    exception_type: str
    exception_message: str
    stack_trace: List[str]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    breadcrumbs: List[Dict[str, Any]] = field(default_factory=list)
    custom_keys: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['platform'] = self.platform.value
        data['severity'] = self.severity.value
        return data


@dataclass
class PerformanceMetric:
    """Mobile performance metric"""
    metric_name: str
    value: float
    unit: str
    platform: AppPlatform
    app_version: str
    timestamp: datetime
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FirebaseCrashlyticsClient:
    """Firebase Crashlytics integration"""
    
    def __init__(self, credentials_path: str = None):
        self.initialized = False
        
        if credentials_path:
            try:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                logger.info("Firebase Crashlytics initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")
    
    async def log_crash(self, report: CrashReport):
        """Log crash to Crashlytics"""
        if not self.initialized:
            return
        
        try:
            # Log to Crashlytics
            crashlytics.log(report.exception_message)
            
            # Set custom keys
            for key, value in report.custom_keys.items():
                crashlytics.set_custom_key(key, value)
            
            # Record exception
            if report.severity == CrashSeverity.FATAL:
                crashlytics.record_error(
                    Exception(report.exception_message),
                    report.stack_trace
                )
                
        except Exception as e:
            logger.error(f"Failed to log crash to Crashlytics: {e}")
    
    async def get_crash_statistics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get crash statistics from Crashlytics"""
        # This would use Firebase Admin SDK to query Crashlytics data
        return {
            'total_crashes': 0,
            'unique_crashes': 0,
            'affected_users': 0,
            'crash_free_users_percent': 100
        }


class MobileAnalytics:
    """Mobile app analytics"""
    
    def __init__(self):
        self.crashlytics: Optional[FirebaseCrashlyticsClient] = None
        self.crashes: List[CrashReport] = []
        self.performance_metrics: List[PerformanceMetric] = []
        self.max_records = 10000
    
    def initialize(self):
        """Initialize mobile analytics"""
        if settings.FIREBASE_CREDENTIALS_PATH:
            self.crashlytics = FirebaseCrashlyticsClient(
                settings.FIREBASE_CREDENTIALS_PATH
            )
    
    async def report_crash(self, report: CrashReport):
        """Report a mobile crash"""
        self.crashes.append(report)
        
        # Trim old records
        if len(self.crashes) > self.max_records:
            self.crashes = self.crashes[-self.max_records:]
        
        # Send to Crashlytics
        if self.crashlytics:
            await self.crashlytics.log_crash(report)
    
    def record_performance_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        self.performance_metrics.append(metric)
        
        if len(self.performance_metrics) > self.max_records:
            self.performance_metrics = self.performance_metrics[-self.max_records:]
    
    def get_crash_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get crash summary"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_crashes = [c for c in self.crashes if c.timestamp > cutoff]
        
        if not recent_crashes:
            return {
                'period_days': days,
                'total_crashes': 0,
                'crash_free_sessions': 100
            }
        
        # Group by platform
        by_platform = {}
        for crash in recent_crashes:
            platform = crash.platform.value
            if platform not in by_platform:
                by_platform[platform] = []
            by_platform[platform].append(crash)
        
        # Group by app version
        by_version = {}
        for crash in recent_crashes:
            version = crash.app_version
            if version not in by_version:
                by_version[version] = []
            by_version[version].append(crash)
        
        # Get top crash types
        from collections import Counter
        crash_types = Counter(c.exception_type for c in recent_crashes)
        
        return {
            'period_days': days,
            'total_crashes': len(recent_crashes),
            'fatal_crashes': sum(1 for c in recent_crashes if c.severity == CrashSeverity.FATAL),
            'non_fatal_crashes': sum(1 for c in recent_crashes if c.severity == CrashSeverity.NON_FATAL),
            'by_platform': {
                platform: len(crashes)
                for platform, crashes in by_platform.items()
            },
            'by_version': {
                version: len(crashes)
                for version, crashes in by_version.items()
            },
            'top_crash_types': [
                {'type': crash_type, 'count': count}
                for crash_type, count in crash_types.most_common(5)
            ],
            'crash_free_sessions': 95  # Placeholder
        }
    
    def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get performance summary"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_metrics = [m for m in self.performance_metrics if m.timestamp > cutoff]
        
        if not recent_metrics:
            return {}
        
        # Group by metric name
        by_metric = {}
        for metric in recent_metrics:
            if metric.metric_name not in by_metric:
                by_metric[metric.metric_name] = []
            by_metric[metric.metric_name].append(metric.value)
        
        # Calculate statistics
        summary = {}
        for metric_name, values in by_metric.items():
            import statistics
            summary[metric_name] = {
                'count': len(values),
                'avg': statistics.mean(values),
                'min': min(values),
                'max': max(values),
                'p95': sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0]
            }
        
        return summary
    
    def get_crashes(
        self,
        platform: AppPlatform = None,
        severity: CrashSeverity = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get crashes with filtering"""
        filtered = self.crashes
        
        if platform:
            filtered = [c for c in filtered if c.platform == platform]
        
        if severity:
            filtered = [c for c in filtered if c.severity == severity]
        
        filtered.sort(key=lambda c: c.timestamp, reverse=True)
        
        return [c.to_dict() for c in filtered[:limit]]


# Global mobile analytics
mobile_analytics = MobileAnalytics()


# Convenience functions for mobile apps
def report_crash(
    platform: str,
    app_version: str,
    exception_type: str,
    exception_message: str,
    stack_trace: List[str],
    user_id: str = None,
    severity: str = 'fatal'
):
    """Report a crash from mobile app"""
    report = CrashReport(
        id=f"crash-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        timestamp=datetime.utcnow(),
        platform=AppPlatform(platform.lower()),
        app_version=app_version,
        os_version='',
        device_model='',
        severity=CrashSeverity(severity.lower()),
        exception_type=exception_type,
        exception_message=exception_message,
        stack_trace=stack_trace,
        user_id=user_id
    )
    
    asyncio.create_task(mobile_analytics.report_crash(report))


def record_app_launch(
    platform: str,
    app_version: str,
    user_id: str = None,
    launch_time_ms: float = None
):
    """Record app launch metric"""
    if launch_time_ms:
        metric = PerformanceMetric(
            metric_name='app_launch_time',
            value=launch_time_ms,
            unit='ms',
            platform=AppPlatform(platform.lower()),
            app_version=app_version,
            timestamp=datetime.utcnow(),
            user_id=user_id
        )
        mobile_analytics.record_performance_metric(metric)
