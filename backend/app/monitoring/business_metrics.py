"""
Business Metrics & Analytics
Mixpanel/Amplitude-style product analytics for Cerebrum AI Platform
"""

import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import asyncio

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EventCategory(Enum):
    """Event categories"""
    USER_ACTION = 'user_action'
    PAGE_VIEW = 'page_view'
    FEATURE_USAGE = 'feature_usage'
    CONVERSION = 'conversion'
    ENGAGEMENT = 'engagement'
    ERROR = 'error'


@dataclass
class AnalyticsEvent:
    """Analytics event"""
    event_name: str
    user_id: str
    timestamp: datetime
    properties: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    device_info: Dict[str, Any] = field(default_factory=dict)
    referrer: Optional[str] = None
    category: EventCategory = EventCategory.USER_ACTION
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['category'] = self.category.value
        return data


@dataclass
class UserProfile:
    """User profile for analytics"""
    user_id: str
    first_seen: datetime
    last_seen: datetime
    properties: Dict[str, Any] = field(default_factory=dict)
    segments: List[str] = field(default_factory=list)


class MixpanelClient:
    """Mixpanel API client"""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = 'https://api.mixpanel.com'
    
    async def track_event(self, event: AnalyticsEvent):
        """Track event in Mixpanel"""
        try:
            payload = {
                'event': event.event_name,
                'properties': {
                    'token': self.api_token,
                    'distinct_id': event.user_id,
                    'time': int(event.timestamp.timestamp()),
                    **event.properties
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'{self.base_url}/track',
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send event to Mixpanel: {e}")
    
    async def set_user_profile(self, profile: UserProfile):
        """Set user profile in Mixpanel"""
        try:
            payload = {
                '$token': self.api_token,
                '$distinct_id': profile.user_id,
                '$set': {
                    'first_seen': profile.first_seen.isoformat(),
                    'last_seen': profile.last_seen.isoformat(),
                    **profile.properties
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'{self.base_url}/engage',
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to set Mixpanel profile: {e}")


class AmplitudeClient:
    """Amplitude API client"""
    
    def __init__(self, api_key: str, secret_key: str = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = 'https://api2.amplitude.com'
    
    async def track_event(self, event: AnalyticsEvent):
        """Track event in Amplitude"""
        try:
            payload = {
                'api_key': self.api_key,
                'events': [{
                    'user_id': event.user_id,
                    'event_type': event.event_name,
                    'time': int(event.timestamp.timestamp() * 1000),
                    'event_properties': event.properties,
                    'user_properties': {},
                    'session_id': event.session_id
                }]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'{self.base_url}/2/httpapi',
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send event to Amplitude: {e}")


class BusinessMetricsCollector:
    """Collect and analyze business metrics"""
    
    def __init__(self):
        self.mixpanel: Optional[MixpanelClient] = None
        self.amplitude: Optional[AmplitudeClient] = None
        self.events_buffer: List[AnalyticsEvent] = []
        self.buffer_size = 100
        self.flush_interval = 5  # seconds
        self.user_profiles: Dict[str, UserProfile] = {}
        self._flush_task = None
    
    def initialize(self):
        """Initialize analytics clients"""
        if settings.MIXPANEL_TOKEN:
            self.mixpanel = MixpanelClient(settings.MIXPANEL_TOKEN)
        
        if settings.AMPLITUDE_API_KEY:
            self.amplitude = AmplitudeClient(
                settings.AMPLITUDE_API_KEY,
                settings.AMPLITUDE_SECRET_KEY
            )
        
        self._flush_task = asyncio.create_task(self._periodic_flush())
    
    async def close(self):
        """Close the collector"""
        if self._flush_task:
            self._flush_task.cancel()
        
        await self._flush_buffer()
    
    async def track(
        self,
        event_name: str,
        user_id: str,
        properties: Dict[str, Any] = None,
        tenant_id: str = None,
        category: EventCategory = EventCategory.USER_ACTION
    ):
        """Track an analytics event"""
        event = AnalyticsEvent(
            event_name=event_name,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            properties=properties or {},
            tenant_id=tenant_id,
            category=category
        )
        
        self.events_buffer.append(event)
        
        if len(self.events_buffer) >= self.buffer_size:
            await self._flush_buffer()
    
    async def _periodic_flush(self):
        """Periodically flush events"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _flush_buffer(self):
        """Flush events buffer to analytics platforms"""
        if not self.events_buffer:
            return
        
        events = self.events_buffer[:]
        self.events_buffer = []
        
        # Send to Mixpanel
        if self.mixpanel:
            for event in events:
                try:
                    await self.mixpanel.track_event(event)
                except Exception as e:
                    logger.error(f"Failed to send event to Mixpanel: {e}")
        
        # Send to Amplitude
        if self.amplitude:
            for event in events:
                try:
                    await self.amplitude.track_event(event)
                except Exception as e:
                    logger.error(f"Failed to send event to Amplitude: {e}")
    
    def identify_user(self, user_id: str, properties: Dict[str, Any]):
        """Identify a user with properties"""
        now = datetime.utcnow()
        
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(
                user_id=user_id,
                first_seen=now,
                last_seen=now,
                properties=properties
            )
        else:
            profile = self.user_profiles[user_id]
            profile.last_seen = now
            profile.properties.update(properties)
    
    def calculate_funnel(
        self,
        steps: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate funnel conversion"""
        # This would query the analytics data
        # For now, return placeholder
        return {
            'steps': [
                {'name': step, 'users': 0, 'conversion_rate': 0}
                for step in steps
            ],
            'overall_conversion': 0
        }
    
    def calculate_retention(
        self,
        cohort_date: datetime,
        periods: int = 30
    ) -> Dict[str, Any]:
        """Calculate user retention"""
        return {
            'cohort_date': cohort_date.isoformat(),
            'cohort_size': 0,
            'retention': [
                {'day': i, 'users': 0, 'rate': 0}
                for i in range(periods)
            ]
        }
    
    def get_engagement_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get user engagement metrics"""
        return {
            'period_days': days,
            'daily_active_users': 0,
            'weekly_active_users': 0,
            'monthly_active_users': 0,
            'avg_session_duration_minutes': 0,
            'avg_sessions_per_user': 0,
            'stickiness_dau_mau': 0
        }


# Global metrics collector
business_metrics = BusinessMetricsCollector()


# Convenience functions for tracking
def track_event(
    event_name: str,
    user_id: str,
    properties: Dict[str, Any] = None,
    tenant_id: str = None
):
    """Track a business event"""
    asyncio.create_task(business_metrics.track(
        event_name=event_name,
        user_id=user_id,
        properties=properties,
        tenant_id=tenant_id
    ))


def track_page_view(user_id: str, page: str, properties: Dict[str, Any] = None):
    """Track a page view"""
    track_event(
        event_name='Page Viewed',
        user_id=user_id,
        properties={'page': page, **(properties or {})},
        category=EventCategory.PAGE_VIEW
    )


def track_feature_usage(user_id: str, feature: str, properties: Dict[str, Any] = None):
    """Track feature usage"""
    track_event(
        event_name=f'Feature Used: {feature}',
        user_id=user_id,
        properties={'feature': feature, **(properties or {})},
        category=EventCategory.FEATURE_USAGE
    )


def track_conversion(user_id: str, conversion_type: str, value: float = None):
    """Track a conversion"""
    track_event(
        event_name=f'Conversion: {conversion_type}',
        user_id=user_id,
        properties={'conversion_type': conversion_type, 'value': value},
        category=EventCategory.CONVERSION
    )
