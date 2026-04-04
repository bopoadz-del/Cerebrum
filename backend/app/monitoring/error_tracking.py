"""
Error Tracking System
Sentry backend integration for Cerebrum AI Platform
"""

import os
import sys
import traceback
import hashlib
import json
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import asyncio

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.core.config import settings

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    FATAL = 'fatal'


@dataclass
class ErrorContext:
    """Error context information"""
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Any] = None
    tags: Optional[Dict[str, str]] = None
    extras: Optional[Dict[str, Any]] = None


class SentryManager:
    """Manages Sentry error tracking integration"""
    
    def __init__(self):
        self.dsn = settings.SENTRY_DSN
        self.environment = settings.ENVIRONMENT
        self.release = settings.APP_VERSION
        self.enabled = bool(self.dsn)
        self.initialized = False
    
    def initialize(self):
        """Initialize Sentry SDK"""
        if not self.enabled or self.initialized:
            return
        
        try:
            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                release=self.release,
                traces_sample_rate=0.1,  # Sample 10% of transactions
                profiles_sample_rate=0.01,  # Profile 1% of transactions
                send_default_pii=False,  # Don't send PII by default
                max_breadcrumbs=50,
                attach_stacktrace=True,
                integrations=[
                    FastApiIntegration(transaction_style='endpoint'),
                    SqlalchemyIntegration(),
                    RedisIntegration(),
                    CeleryIntegration(),
                    AsyncioIntegration(),
                    LoggingIntegration(
                        level=logging.INFO,
                        event_level=logging.ERROR
                    )
                ],
                before_send=self._before_send,
                before_breadcrumb=self._before_breadcrumb,
                ignore_errors=[
                    'asyncio.CancelledError',
                    'ConnectionResetError'
                ]
            )
            
            self.initialized = True
            logger.info("Sentry initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    
    def _before_send(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter events before sending to Sentry"""
        # Filter out health check endpoints
        if event.get('request', {}).get('url', '').endswith(('/health', '/ready', '/metrics')):
            return None
        
        # Filter out specific error types
        exception = event.get('exception', {})
        values = exception.get('values', [])
        
        for value in values:
            error_type = value.get('type', '')
            if error_type in ['ValidationError', 'HTTPException']:
                # Only send 5xx errors
                status_code = value.get('mechanism', {}).get('data', {}).get('status_code', 200)
                if status_code < 500:
                    return None
        
        return event
    
    def _before_breadcrumb(self, breadcrumb: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter breadcrumbs before adding to event"""
        # Filter sensitive data from breadcrumbs
        if breadcrumb.get('category') == 'http':
            data = breadcrumb.get('data', {})
            if 'url' in data:
                # Remove query parameters
                url = data['url']
                if '?' in url:
                    data['url'] = url.split('?')[0] + '?<redacted>'
        
        return breadcrumb
    
    def set_user(self, user_id: str, email: Optional[str] = None, 
                 username: Optional[str] = None, tenant_id: Optional[str] = None):
        """Set user context for Sentry"""
        if not self.initialized:
            return
        
        user_context = {'id': user_id}
        if email:
            user_context['email'] = email
        if username:
            user_context['username'] = username
        if tenant_id:
            user_context['tenant_id'] = tenant_id
        
        sentry_sdk.set_user(user_context)
    
    def clear_user(self):
        """Clear user context"""
        if self.initialized:
            sentry_sdk.set_user(None)
    
    def set_tags(self, tags: Dict[str, str]):
        """Set tags for current scope"""
        if not self.initialized:
            return
        
        for key, value in tags.items():
            sentry_sdk.set_tag(key, value)
    
    def set_extra(self, key: str, value: Any):
        """Set extra context"""
        if self.initialized:
            sentry_sdk.set_extra(key, value)
    
    def capture_exception(self, exception: Exception = None, 
                         context: ErrorContext = None) -> Optional[str]:
        """Capture an exception"""
        if not self.initialized:
            return None
        
        with sentry_sdk.push_scope() as scope:
            if context:
                if context.user_id:
                    scope.set_user({'id': context.user_id, 'tenant_id': context.tenant_id})
                
                if context.tags:
                    for key, value in context.tags.items():
                        scope.set_tag(key, value)
                
                if context.extras:
                    for key, value in context.extras.items():
                        scope.set_extra(key, value)
                
                if context.request_id:
                    scope.set_tag('request_id', context.request_id)
            
            event_id = sentry_sdk.capture_exception(exception)
            return event_id
    
    def capture_message(self, message: str, level: ErrorSeverity = ErrorSeverity.INFO,
                       context: ErrorContext = None) -> Optional[str]:
        """Capture a message"""
        if not self.initialized:
            return None
        
        with sentry_sdk.push_scope() as scope:
            if context:
                if context.tags:
                    for key, value in context.tags.items():
                        scope.set_tag(key, value)
            
            event_id = sentry_sdk.capture_message(message, level=level.value)
            return event_id
    
    def start_transaction(self, name: str, op: str = None) -> Any:
        """Start a performance transaction"""
        if not self.initialized:
            return None
        
        return sentry_sdk.start_transaction(name=name, op=op)
    
    def start_span(self, op: str, description: str = None):
        """Start a span within current transaction"""
        if not self.initialized:
            return None
        
        return sentry_sdk.start_span(op=op, description=description)


# Global Sentry manager
sentry_manager = SentryManager()


class ErrorTracker:
    """Custom error tracking with local storage"""
    
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.max_errors = 1000
        self.error_handlers: Dict[str, List[Callable]] = {}
    
    def track_error(
        self,
        exception: Exception,
        context: ErrorContext = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> str:
        """Track an error locally"""
        error_id = self._generate_error_id(exception)
        
        error_record = {
            'id': error_id,
            'timestamp': datetime.utcnow().isoformat(),
            'type': type(exception).__name__,
            'message': str(exception),
            'stacktrace': traceback.format_exc(),
            'severity': severity.value,
            'context': asdict(context) if context else None,
            'count': 1,
            'first_seen': datetime.utcnow().isoformat(),
            'last_seen': datetime.utcnow().isoformat()
        }
        
        # Check if we've seen this error before
        existing = self._find_existing_error(error_id)
        if existing:
            existing['count'] += 1
            existing['last_seen'] = error_record['timestamp']
        else:
            self.errors.append(error_record)
            
            # Trim if needed
            if len(self.errors) > self.max_errors:
                self.errors = self.errors[-self.max_errors:]
        
        # Send to Sentry
        sentry_manager.capture_exception(exception, context)
        
        # Notify handlers
        self._notify_handlers(error_record)
        
        return error_id
    
    def _generate_error_id(self, exception: Exception) -> str:
        """Generate unique error ID based on exception"""
        content = f"{type(exception).__name__}:{str(exception)}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _find_existing_error(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Find existing error by ID"""
        for error in self.errors:
            if error['id'] == error_id:
                return error
        return None
    
    def register_handler(self, error_type: str, handler: Callable):
        """Register an error handler"""
        if error_type not in self.error_handlers:
            self.error_handlers[error_type] = []
        self.error_handlers[error_type].append(handler)
    
    def _notify_handlers(self, error: Dict[str, Any]):
        """Notify registered handlers"""
        handlers = self.error_handlers.get(error['type'], [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(error))
                else:
                    handler(error)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    def get_errors(
        self,
        severity: ErrorSeverity = None,
        error_type: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get tracked errors with filtering"""
        filtered = self.errors
        
        if severity:
            filtered = [e for e in filtered if e['severity'] == severity.value]
        
        if error_type:
            filtered = [e for e in filtered if e['type'] == error_type]
        
        return sorted(filtered, key=lambda x: x['last_seen'], reverse=True)[:limit]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        stats = {
            'total_errors': len(self.errors),
            'by_severity': {},
            'by_type': {},
            'top_errors': []
        }
        
        for error in self.errors:
            severity = error['severity']
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
            
            error_type = error['type']
            stats['by_type'][error_type] = stats['by_type'].get(error_type, 0) + error['count']
        
        # Get top errors by count
        sorted_errors = sorted(self.errors, key=lambda x: x['count'], reverse=True)
        stats['top_errors'] = [
            {
                'id': e['id'],
                'type': e['type'],
                'message': e['message'][:100],
                'count': e['count'],
                'last_seen': e['last_seen']
            }
            for e in sorted_errors[:10]
        ]
        
        return stats


# Global error tracker
error_tracker = ErrorTracker()


def track_error(
    exception: Exception = None,
    message: str = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    user_id: str = None,
    tenant_id: str = None,
    request_id: str = None,
    tags: Dict[str, str] = None,
    extras: Dict[str, Any] = None
) -> Optional[str]:
    """Convenience function to track an error"""
    if exception is None and message:
        exception = Exception(message)
    
    if exception is None:
        exception = sys.exc_info()[1]
    
    if exception is None:
        return None
    
    context = ErrorContext(
        user_id=user_id,
        tenant_id=tenant_id,
        request_id=request_id,
        tags=tags,
        extras=extras
    )
    
    return error_tracker.track_error(exception, context, severity)


class ErrorBoundary:
    """Error boundary for catching and tracking errors"""
    
    def __init__(self, component_name: str, context: Dict[str, Any] = None):
        self.component_name = component_name
        self.context = context or {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            context = ErrorContext(
                extras={
                    'component': self.component_name,
                    **self.context
                }
            )
            error_tracker.track_error(exc_val, context, ErrorSeverity.ERROR)
        
        # Don't suppress the exception
        return False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            context = ErrorContext(
                extras={
                    'component': self.component_name,
                    **self.context
                }
            )
            error_tracker.track_error(exc_val, context, ErrorSeverity.ERROR)
        
        return False


class PerformanceMonitor:
    """Monitor application performance"""
    
    def __init__(self):
        self.transactions: Dict[str, Dict[str, Any]] = {}
    
    def start_transaction(self, name: str, op: str = None) -> str:
        """Start a performance transaction"""
        transaction_id = hashlib.md5(f"{name}:{datetime.utcnow()}".encode()).hexdigest()[:16]
        
        self.transactions[transaction_id] = {
            'id': transaction_id,
            'name': name,
            'op': op,
            'start_time': datetime.utcnow(),
            'spans': []
        }
        
        # Also start Sentry transaction
        sentry_manager.start_transaction(name, op)
        
        return transaction_id
    
    def finish_transaction(self, transaction_id: str, status: str = 'ok'):
        """Finish a transaction"""
        if transaction_id not in self.transactions:
            return
        
        transaction = self.transactions[transaction_id]
        transaction['end_time'] = datetime.utcnow()
        transaction['duration_ms'] = (
            transaction['end_time'] - transaction['start_time']
        ).total_seconds() * 1000
        transaction['status'] = status
        
        # Log slow transactions
        if transaction['duration_ms'] > 1000:
            logger.warning(
                f"Slow transaction: {transaction['name']} took {transaction['duration_ms']:.2f}ms"
            )
    
    def add_span(self, transaction_id: str, op: str, description: str,
                 start_time: datetime, end_time: datetime):
        """Add a span to a transaction"""
        if transaction_id not in self.transactions:
            return
        
        self.transactions[transaction_id]['spans'].append({
            'op': op,
            'description': description,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_ms': (end_time - start_time).total_seconds() * 1000
        })


# Initialize Sentry on module import
sentry_manager.initialize()
