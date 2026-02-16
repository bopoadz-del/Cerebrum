"""
Real User Monitoring (RUM) with Core Web Vitals
Tracks frontend performance metrics and user experience
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import httpx

from app.core.config import settings
from app.monitoring.apm import CustomSpan, metrics

logger = logging.getLogger(__name__)


@dataclass
class CoreWebVitals:
    """Core Web Vitals metrics"""
    lcp: Optional[float] = None  # Largest Contentful Paint (ms)
    fid: Optional[float] = None  # First Input Delay (ms)
    cls: Optional[float] = None  # Cumulative Layout Shift
    fcp: Optional[float] = None  # First Contentful Paint (ms)
    ttfb: Optional[float] = None  # Time to First Byte (ms)
    inp: Optional[float] = None  # Interaction to Next Paint (ms)
    
    def is_good(self) -> bool:
        """Check if all metrics are in 'good' range"""
        return (
            (self.lcp is None or self.lcp < 2500) and
            (self.fid is None or self.fid < 100) and
            (self.cls is None or self.cls < 0.1) and
            (self.fcp is None or self.fcp < 1800) and
            (self.ttfb is None or self.ttfb < 800)
        )
    
    def get_score(self) -> str:
        """Get overall performance score"""
        if self.is_good():
            return 'good'
        elif self._is_needs_improvement():
            return 'needs_improvement'
        return 'poor'
    
    def _is_needs_improvement(self) -> bool:
        """Check if metrics need improvement"""
        return (
            (self.lcp is None or self.lcp < 4000) and
            (self.fid is None or self.fid < 300) and
            (self.cls is None or self.cls < 0.25)
        )


@dataclass
class RUMEvent:
    """Real User Monitoring event"""
    session_id: str
    page_url: str
    user_agent: str
    timestamp: datetime
    vitals: CoreWebVitals
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    page_load_time: Optional[float] = None
    resource_count: Optional[int] = None
    resource_size: Optional[int] = None
    errors: List[Dict[str, Any]] = None
    custom_metrics: Dict[str, Any] = None


class RUMCollector:
    """Collect and process RUM data"""
    
    def __init__(self):
        self.datadog_rum_enabled = settings.DATADOG_RUM_ENABLED
        self.datadog_client_token = settings.DATADOG_CLIENT_TOKEN
        self.datadog_application_id = settings.DATADOG_APPLICATION_ID
        self.events_buffer = []
        self.buffer_size = 100
        
    async def collect_event(self, event: RUMEvent):
        """Collect a RUM event"""
        # Add to buffer
        self.events_buffer.append(event)
        
        # Flush if buffer is full
        if len(self.events_buffer) >= self.buffer_size:
            await self._flush_buffer()
        
        # Send to Datadog RUM
        if self.datadog_rum_enabled:
            await self._send_to_datadog(event)
    
    async def _send_to_datadog(self, event: RUMEvent):
        """Send event to Datadog RUM"""
        try:
            payload = {
                'application_id': self.datadog_application_id,
                'session_id': event.session_id,
                'view': {
                    'url': event.page_url,
                    'loading_time': event.page_load_time,
                },
                'usr': {
                    'id': event.user_id,
                    'tenant_id': event.tenant_id
                } if event.user_id else None,
                'vitals': asdict(event.vitals) if event.vitals else None
            }
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    'https://rum-http-intake.logs.datadoghq.com/v1/input',
                    headers={'DD-API-KEY': self.datadog_client_token},
                    json=payload,
                    timeout=5.0
                )
        except Exception as e:
            logger.error(f"Failed to send RUM event to Datadog: {e}")
    
    async def _flush_buffer(self):
        """Flush events buffer"""
        if not self.events_buffer:
            return
        
        # Process batch
        events = self.events_buffer[:]
        self.events_buffer = []
        
        # Store in database or analytics platform
        await self._store_events(events)
    
    async def _store_events(self, events: List[RUMEvent]):
        """Store events for analysis"""
        # Implementation would store in ClickHouse, BigQuery, etc.
        logger.info(f"Stored {len(events)} RUM events")


# Global RUM collector
rum_collector = RUMCollector()


class RUMMiddleware(BaseHTTPMiddleware):
    """Middleware to inject RUM tracking"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        duration_ms = (time.time() - start_time) * 1000
        
        # Inject RUM script for HTML responses
        if 'text/html' in response.headers.get('content-type', ''):
            response = await self._inject_rum_script(request, response)
        
        return response
    
    async def _inject_rum_script(self, request: Request, response: Response) -> Response:
        """Inject Datadog RUM script into HTML"""
        body = b''
        async for chunk in response.body_iterator:
            body += chunk
        
        rum_script = self._get_rum_script(request)
        
        # Inject before closing </head> or </body>
        if b'</head>' in body:
            body = body.replace(b'</head>', rum_script.encode() + b'</head>')
        elif b'</body>' in body:
            body = body.replace(b'</body>', rum_script.encode() + b'</body>')
        
        # Update response
        response.headers['content-length'] = str(len(body))
        response.body_iterator = iter([body])
        
        return response
    
    def _get_rum_script(self, request: Request) -> str:
        """Generate RUM initialization script"""
        return f"""
        <script>
        (function(h,o,u,n,d){{
            h=h[d]=h[d]||{{q:[],onReady:function(c){{h.q.push(c)}}}}
            d=o.createElement(u);d.async=1;d.src=n
            n=o.getElementsByTagName(u)[0];n.parentNode.insertBefore(d,n)
        }})(window,document,'script','https://www.datadoghq-browser-agent.com/datadog-rum-v4.js','DD_RUM')
        
        DD_RUM.onReady(function() {{
            DD_RUM.init({{
                clientToken: '{settings.DATADOG_CLIENT_TOKEN}',
                applicationId: '{settings.DATADOG_APPLICATION_ID}',
                site: 'datadoghq.com',
                service: '{settings.SERVICE_NAME}',
                env: '{settings.ENVIRONMENT}',
                version: '{settings.APP_VERSION}',
                sessionSampleRate: 100,
                sessionReplaySampleRate: 20,
                trackUserInteractions: true,
                trackResources: true,
                trackLongTasks: true,
                defaultPrivacyLevel: 'mask-user-input',
            }});
            
            // Set user context if available
            const userId = localStorage.getItem('user_id');
            const tenantId = localStorage.getItem('tenant_id');
            if (userId) {{
                DD_RUM.setUser({{ id: userId, tenant_id: tenantId }});
            }}
        }});
        </script>
        """


class CoreWebVitalsCollector:
    """Collect Core Web Vitals from frontend"""
    
    def __init__(self):
        self.vitals_history = []
        self.max_history = 10000
    
    def record_vitals(self, vitals: CoreWebVitals, context: Dict[str, Any]):
        """Record Core Web Vitals measurement"""
        entry = {
            'timestamp': datetime.utcnow(),
            'vitals': asdict(vitals),
            'context': context,
            'score': vitals.get_score()
        }
        
        self.vitals_history.append(entry)
        
        # Trim history
        if len(self.vitals_history) > self.max_history:
            self.vitals_history = self.vitals_history[-self.max_history:]
        
        # Send to APM
        with CustomSpan('web_vitals', resource='core_web_vitals') as span:
            span.set_tag('vitals.score', vitals.get_score())
            span.set_metric('vitals.lcp', vitals.lcp or 0)
            span.set_metric('vitals.fid', vitals.fid or 0)
            span.set_metric('vitals.cls', vitals.cls or 0)
    
    def get_percentiles(self, metric: str, percentiles: List[float] = [50, 75, 90, 95, 99]) -> Dict[str, float]:
        """Get percentile values for a metric"""
        values = [
            entry['vitals'].get(metric) 
            for entry in self.vitals_history 
            if entry['vitals'].get(metric) is not None
        ]
        
        if not values:
            return {}
        
        values.sort()
        results = {}
        for p in percentiles:
            idx = int(len(values) * p / 100)
            results[f'p{int(p)}'] = values[min(idx, len(values) - 1)]
        
        return results
    
    def get_score_distribution(self) -> Dict[str, int]:
        """Get distribution of performance scores"""
        distribution = {'good': 0, 'needs_improvement': 0, 'poor': 0}
        for entry in self.vitals_history:
            score = entry.get('score', 'unknown')
            if score in distribution:
                distribution[score] += 1
        return distribution


# Global vitals collector
vitals_collector = CoreWebVitalsCollector()


class UserExperienceMetrics:
    """Track user experience metrics"""
    
    def __init__(self):
        self.session_data = {}
    
    def start_session(self, session_id: str, user_id: Optional[str] = None):
        """Start tracking a user session"""
        self.session_data[session_id] = {
            'start_time': datetime.utcnow(),
            'user_id': user_id,
            'page_views': 0,
            'interactions': 0,
            'errors': 0,
            'total_time': 0
        }
    
    def record_page_view(self, session_id: str, page: str, load_time_ms: float):
        """Record a page view"""
        if session_id in self.session_data:
            self.session_data[session_id]['page_views'] += 1
            self.session_data[session_id]['total_time'] += load_time_ms
    
    def record_interaction(self, session_id: str, interaction_type: str):
        """Record a user interaction"""
        if session_id in self.session_data:
            self.session_data[session_id]['interactions'] += 1
    
    def end_session(self, session_id: str):
        """End a user session and calculate metrics"""
        if session_id not in self.session_data:
            return None
        
        data = self.session_data[session_id]
        duration = (datetime.utcnow() - data['start_time']).total_seconds()
        
        metrics = {
            'session_id': session_id,
            'duration_seconds': duration,
            'page_views': data['page_views'],
            'interactions': data['interactions'],
            'errors': data['errors'],
            'avg_page_load_ms': data['total_time'] / max(data['page_views'], 1),
            'engagement_score': self._calculate_engagement(data)
        }
        
        del self.session_data[session_id]
        return metrics
    
    def _calculate_engagement(self, data: Dict) -> float:
        """Calculate engagement score (0-100)"""
        score = 0
        
        # Page views (max 30 points)
        score += min(data['page_views'] * 5, 30)
        
        # Interactions (max 40 points)
        score += min(data['interactions'] * 2, 40)
        
        # Session duration (max 30 points)
        duration_minutes = data.get('duration', 0) / 60
        score += min(duration_minutes * 5, 30)
        
        return min(score, 100)


# API endpoint for receiving RUM data
async def receive_rum_data(data: Dict[str, Any], request: Request):
    """Receive RUM data from frontend"""
    try:
        vitals = CoreWebVitals(
            lcp=data.get('lcp'),
            fid=data.get('fid'),
            cls=data.get('cls'),
            fcp=data.get('fcp'),
            ttfb=data.get('ttfb'),
            inp=data.get('inp')
        )
        
        context = {
            'url': data.get('url'),
            'user_agent': request.headers.get('user-agent'),
            'referrer': data.get('referrer')
        }
        
        vitals_collector.record_vitals(vitals, context)
        
        # Create RUM event
        event = RUMEvent(
            session_id=data.get('session_id'),
            page_url=data.get('url'),
            user_agent=request.headers.get('user-agent', ''),
            timestamp=datetime.utcnow(),
            vitals=vitals,
            user_id=data.get('user_id'),
            tenant_id=data.get('tenant_id'),
            page_load_time=data.get('page_load_time'),
            errors=data.get('errors', [])
        )
        
        await rum_collector.collect_event(event)
        
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f"Error processing RUM data: {e}")
        return {'status': 'error', 'message': str(e)}
