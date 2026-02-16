"""
Application Performance Monitoring (APM) Integration
Datadog/New Relic APM integration for Cerebrum AI Platform
"""

import os
import time
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
import logging

from ddtrace import tracer, patch_all
from ddtrace.contrib.fastapi import TraceMiddleware
from ddtrace.contrib.sqlalchemy import trace_sqlalchemy
from ddtrace.contrib.redis import trace_redis
from ddtrace.contrib.celery import patch_celery
import newrelic.agent

from app.core.config import settings

logger = logging.getLogger(__name__)


class APMManager:
    """Manages APM integrations for Datadog and New Relic"""
    
    def __init__(self):
        self.datadog_enabled = settings.DATADOG_ENABLED
        self.newrelic_enabled = settings.NEWRELIC_ENABLED
        self.service_name = settings.SERVICE_NAME
        self.environment = settings.ENVIRONMENT
        
    def initialize(self):
        """Initialize APM integrations"""
        if self.datadog_enabled:
            self._init_datadog()
        
        if self.newrelic_enabled:
            self._init_newrelic()
    
    def _init_datadog(self):
        """Initialize Datadog APM"""
        try:
            # Patch common libraries
            patch_all(
                sqlalchemy=True,
                redis=True,
                celery=True,
                requests=True,
                aiohttp=True,
                botocore=True
            )
            
            # Configure tracer
            tracer.configure(
                hostname=settings.DATADOG_AGENT_HOST,
                port=settings.DATADOG_AGENT_PORT,
                enabled=True,
                settings={
                    'FILTERS': [
                        {'filter': 'http', 'pattern': '/health'},
                        {'filter': 'http', 'pattern': '/metrics'}
                    ]
                }
            )
            
            logger.info("Datadog APM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Datadog APM: {e}")
    
    def _init_newrelic(self):
        """Initialize New Relic APM"""
        try:
            newrelic.agent.initialize(
                config_file='newrelic.ini',
                environment=self.environment,
                log_file='/var/log/newrelic/python-agent.log',
                log_level=logging.INFO
            )
            logger.info("New Relic APM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize New Relic APM: {e}")
    
    def get_fastapi_middleware(self):
        """Get FastAPI middleware for tracing"""
        if self.datadog_enabled:
            return TraceMiddleware
        return None


# Global APM manager instance
apm_manager = APMManager()


class CustomSpan:
    """Custom span wrapper for distributed tracing"""
    
    def __init__(self, name: str, service: str = None, resource: str = None):
        self.name = name
        self.service = service or settings.SERVICE_NAME
        self.resource = resource
        self.span = None
        self.start_time = None
    
    def __enter__(self):
        if apm_manager.datadog_enabled:
            self.span = tracer.trace(
                self.name,
                service=self.service,
                resource=self.resource
            )
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_val:
                self.span.set_exc_info(exc_type, exc_val, exc_tb)
            self.span.finish()
        
        duration = time.time() - self.start_time
        logger.debug(f"Span {self.name} completed in {duration:.3f}s")
    
    def set_tag(self, key: str, value: Any):
        """Set tag on the span"""
        if self.span:
            self.span.set_tag(key, value)
    
    def set_metric(self, key: str, value: float):
        """Set metric on the span"""
        if self.span:
            self.span.set_metric(key, value)


def trace_operation(
    operation_name: str,
    service: str = None,
    resource: str = None,
    tags: Dict[str, Any] = None
):
    """Decorator to trace function execution"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with CustomSpan(operation_name, service, resource or func.__name__) as span:
                if tags:
                    for key, value in tags.items():
                        span.set_tag(key, value)
                
                # Add function arguments as tags (sanitized)
                for i, arg in enumerate(args):
                    if isinstance(arg, (str, int, float, bool)):
                        span.set_tag(f'arg_{i}', str(arg))
                
                for key, value in kwargs.items():
                    if isinstance(value, (str, int, float, bool)):
                        span.set_tag(f'kwarg_{key}', str(value))
                
                try:
                    result = func(*args, **kwargs)
                    span.set_tag('status', 'success')
                    return result
                except Exception as e:
                    span.set_tag('status', 'error')
                    span.set_tag('error.message', str(e))
                    raise
        
        return wrapper
    return decorator


def trace_db_query(query_name: str, db_type: str = 'postgresql'):
    """Decorator to trace database queries"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with CustomSpan(
                f'db.query.{query_name}',
                service=f'{settings.SERVICE_NAME}-db',
                resource=query_name
            ) as span:
                span.set_tag('db.type', db_type)
                span.set_tag('db.operation', query_name)
                
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    span.set_metric('db.duration_ms', (time.time() - start) * 1000)
                    span.set_tag('db.rows_affected', getattr(result, 'rowcount', 0))
                    return result
                except Exception as e:
                    span.set_tag('db.error', str(e))
                    raise
        
        return wrapper
    return decorator


def trace_external_call(service_name: str, operation: str = None):
    """Decorator to trace external API calls"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with CustomSpan(
                f'external.{service_name}',
                service=f'{settings.SERVICE_NAME}-external',
                resource=operation or func.__name__
            ) as span:
                span.set_tag('external.service', service_name)
                span.set_tag('http.url', kwargs.get('url', 'unknown'))
                
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    span.set_metric('http.duration_ms', (time.time() - start) * 1000)
                    
                    if hasattr(result, 'status_code'):
                        span.set_tag('http.status_code', result.status_code)
                    
                    return result
                except Exception as e:
                    span.set_tag('http.error', str(e))
                    raise
        
        return wrapper
    return decorator


class PerformanceMetrics:
    """Collect and report performance metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_timing(self, metric_name: str, value_ms: float, tags: Dict[str, str] = None):
        """Record a timing metric"""
        if apm_manager.datadog_enabled:
            tracer.set_metric(f'cerebrum.{metric_name}', value_ms)
        
        logger.debug(f"Metric {metric_name}: {value_ms}ms")
    
    def record_count(self, metric_name: str, value: int = 1, tags: Dict[str, str] = None):
        """Record a count metric"""
        if apm_manager.datadog_enabled:
            tracer.set_metric(f'cerebrum.{metric_name}', value)
    
    def record_gauge(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a gauge metric"""
        if apm_manager.datadog_enabled:
            tracer.set_metric(f'cerebrum.{metric_name}', value)


# Global metrics instance
metrics = PerformanceMetrics()


@contextmanager
def timed_operation(operation_name: str):
    """Context manager for timing operations"""
    start = time.time()
    try:
        yield
    finally:
        duration = (time.time() - start) * 1000
        metrics.record_timing(operation_name, duration)


class EndpointProfiler:
    """Profile API endpoints"""
    
    def __init__(self):
        self.profiles = {}
    
    def profile_endpoint(self, endpoint: str, method: str, duration_ms: float, 
                         status_code: int, user_id: Optional[str] = None):
        """Record endpoint performance profile"""
        key = f"{method}:{endpoint}"
        
        if key not in self.profiles:
            self.profiles[key] = {
                'count': 0,
                'total_duration': 0,
                'min_duration': float('inf'),
                'max_duration': 0,
                'status_codes': {},
                'errors': 0
            }
        
        profile = self.profiles[key]
        profile['count'] += 1
        profile['total_duration'] += duration_ms
        profile['min_duration'] = min(profile['min_duration'], duration_ms)
        profile['max_duration'] = max(profile['max_duration'], duration_ms)
        profile['status_codes'][status_code] = profile['status_codes'].get(status_code, 0) + 1
        
        if status_code >= 400:
            profile['errors'] += 1
        
        # Send to APM
        with CustomSpan('endpoint.profile', resource=endpoint) as span:
            span.set_tag('http.method', method)
            span.set_tag('http.route', endpoint)
            span.set_metric('http.response_time', duration_ms)
            span.set_tag('http.status_code', status_code)
    
    def get_slow_endpoints(self, threshold_ms: float = 1000) -> list:
        """Get endpoints slower than threshold"""
        slow = []
        for key, profile in self.profiles.items():
            avg_duration = profile['total_duration'] / profile['count']
            if avg_duration > threshold_ms:
                slow.append({
                    'endpoint': key,
                    'avg_duration_ms': avg_duration,
                    'p95_duration_ms': profile['max_duration'],
                    'request_count': profile['count'],
                    'error_rate': profile['errors'] / profile['count']
                })
        return sorted(slow, key=lambda x: x['avg_duration_ms'], reverse=True)


# Initialize on module import
apm_manager.initialize()
