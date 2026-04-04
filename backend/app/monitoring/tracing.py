"""
Distributed Tracing
Jaeger/Zipkin integration for request tracing
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

import httpx
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

from app.core.config import settings

logger = logging.getLogger(__name__)


# Context variables for trace propagation
current_trace_id: ContextVar[str] = ContextVar('trace_id', default=None)
current_span_id: ContextVar[str] = ContextVar('span_id', default=None)


@dataclass
class Span:
    """Trace span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = 'ok'
    
    def finish(self, status: str = 'ok'):
        """Finish the span"""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status


@dataclass
class Trace:
    """Complete trace"""
    trace_id: str
    spans: List[Span]
    root_span_id: str
    start_time: datetime
    end_time: Optional[datetime] = None


class JaegerTracer:
    """Jaeger distributed tracing integration"""
    
    def __init__(self, agent_host: str = 'localhost', agent_port: int = 6831):
        self.agent_host = agent_host
        self.agent_port = agent_port
        self.service_name = settings.SERVICE_NAME
        
        # Initialize OpenTelemetry
        self.provider = TracerProvider()
        trace.set_tracer_provider(self.provider)
        
        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=agent_host,
            agent_port=agent_port
        )
        
        self.provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )
        
        self.tracer = trace.get_tracer(__name__)
    
    def start_span(
        self,
        name: str,
        parent_span_id: str = None,
        tags: Dict[str, Any] = None,
        kind: SpanKind = SpanKind.INTERNAL
    ) -> trace.Span:
        """Start a new span"""
        ctx = None
        if parent_span_id:
            # Extract parent context
            pass
        
        span = self.tracer.start_span(name, context=ctx, kind=kind)
        
        if tags:
            for key, value in tags.items():
                span.set_attribute(key, value)
        
        return span
    
    def inject_headers(self, span: trace.Span) -> Dict[str, str]:
        """Inject trace context into headers"""
        from opentelemetry.propagate import inject
        
        carrier = {}
        inject(carrier)
        
        return carrier
    
    def extract_context(self, headers: Dict[str, str]):
        """Extract trace context from headers"""
        from opentelemetry.propagate import extract
        
        return extract(headers)


class ZipkinTracer:
    """Zipkin distributed tracing integration"""
    
    def __init__(self, endpoint: str = 'http://localhost:9411/api/v2/spans'):
        self.endpoint = endpoint
        self.service_name = settings.SERVICE_NAME
        
        # Initialize OpenTelemetry
        self.provider = TracerProvider()
        trace.set_tracer_provider(self.provider)
        
        # Configure Zipkin exporter
        zipkin_exporter = ZipkinExporter(endpoint=endpoint)
        
        self.provider.add_span_processor(
            BatchSpanProcessor(zipkin_exporter)
        )
        
        self.tracer = trace.get_tracer(__name__)


class CustomTracer:
    """Custom lightweight tracer"""
    
    def __init__(self):
        self.active_traces: Dict[str, Trace] = {}
        self.active_spans: Dict[str, Span] = {}
        self.span_stack: List[str] = []
    
    def start_trace(self, operation_name: str, tags: Dict[str, Any] = None) -> str:
        """Start a new trace"""
        trace_id = str(uuid.uuid4()).replace('-', '')[:32]
        span_id = str(uuid.uuid4()).replace('-', '')[:16]
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation_name=operation_name,
            service_name=settings.SERVICE_NAME,
            start_time=datetime.utcnow(),
            tags=tags or {}
        )
        
        trace_obj = Trace(
            trace_id=trace_id,
            spans=[span],
            root_span_id=span_id,
            start_time=datetime.utcnow()
        )
        
        self.active_traces[trace_id] = trace_obj
        self.active_spans[span_id] = span
        self.span_stack.append(span_id)
        
        # Set context
        current_trace_id.set(trace_id)
        current_span_id.set(span_id)
        
        return trace_id
    
    def start_span(
        self,
        operation_name: str,
        parent_span_id: str = None,
        tags: Dict[str, Any] = None
    ) -> str:
        """Start a new span within current trace"""
        trace_id = current_trace_id.get()
        
        if not trace_id or trace_id not in self.active_traces:
            # Start new trace
            return self.start_trace(operation_name, tags)
        
        span_id = str(uuid.uuid4()).replace('-', '')[:16]
        
        # Use provided parent or current span
        if not parent_span_id:
            parent_span_id = current_span_id.get()
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=settings.SERVICE_NAME,
            start_time=datetime.utcnow(),
            tags=tags or {}
        )
        
        self.active_traces[trace_id].spans.append(span)
        self.active_spans[span_id] = span
        self.span_stack.append(span_id)
        
        current_span_id.set(span_id)
        
        return span_id
    
    def finish_span(self, span_id: str = None, status: str = 'ok'):
        """Finish a span"""
        if not span_id:
            span_id = current_span_id.get()
        
        if span_id and span_id in self.active_spans:
            span = self.active_spans[span_id]
            span.finish(status)
            
            # Pop from stack
            if span_id in self.span_stack:
                self.span_stack.remove(span_id)
            
            # Update current span
            if self.span_stack:
                current_span_id.set(self.span_stack[-1])
            
            del self.active_spans[span_id]
    
    def finish_trace(self, trace_id: str = None):
        """Finish a trace"""
        if not trace_id:
            trace_id = current_trace_id.get()
        
        if trace_id and trace_id in self.active_traces:
            trace_obj = self.active_traces[trace_id]
            trace_obj.end_time = datetime.utcnow()
            
            # Clean up
            del self.active_traces[trace_id]
            
            current_trace_id.set(None)
            current_span_id.set(None)
            self.span_stack = []
    
    def add_tag(self, key: str, value: Any, span_id: str = None):
        """Add tag to span"""
        if not span_id:
            span_id = current_span_id.get()
        
        if span_id and span_id in self.active_spans:
            self.active_spans[span_id].tags[key] = value
    
    def log_event(self, event: str, payload: Dict[str, Any] = None, span_id: str = None):
        """Log an event to span"""
        if not span_id:
            span_id = current_span_id.get()
        
        if span_id and span_id in self.active_spans:
            self.active_spans[span_id].logs.append({
                'timestamp': datetime.utcnow().isoformat(),
                'event': event,
                'payload': payload or {}
            })
    
    def get_current_trace_id(self) -> Optional[str]:
        """Get current trace ID"""
        return current_trace_id.get()
    
    def get_current_span_id(self) -> Optional[str]:
        """Get current span ID"""
        return current_span_id.get()
    
    def inject_context(self) -> Dict[str, str]:
        """Get context for propagation"""
        return {
            'X-Trace-Id': current_trace_id.get() or '',
            'X-Span-Id': current_span_id.get() or ''
        }
    
    def extract_context(self, headers: Dict[str, str]):
        """Extract context from headers"""
        trace_id = headers.get('X-Trace-Id') or headers.get('x-trace-id')
        span_id = headers.get('X-Span-Id') or headers.get('x-span-id')
        
        if trace_id:
            current_trace_id.set(trace_id)
        if span_id:
            current_span_id.set(span_id)


# Global tracer
tracer = CustomTracer()


class TraceMiddleware:
    """Middleware for automatic request tracing"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        
        # Extract trace context from headers
        headers = dict(scope.get('headers', []))
        headers = {k.decode(): v.decode() for k, v in headers.items()}
        tracer.extract_context(headers)
        
        # Start trace
        path = scope.get('path', '/')
        method = scope.get('method', 'GET')
        
        trace_id = tracer.start_trace(
            operation_name=f"{method} {path}",
            tags={
                'http.method': method,
                'http.path': path,
                'http.host': headers.get('host', 'unknown')
            }
        )
        
        try:
            await self.app(scope, receive, send)
            tracer.finish_span(status='ok')
        except Exception as e:
            tracer.add_tag('error', str(e))
            tracer.finish_span(status='error')
            raise
        finally:
            tracer.finish_trace(trace_id)


def trace_function(operation_name: str = None):
    """Decorator to trace function execution"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            span_name = operation_name or func.__name__
            span_id = tracer.start_span(span_name)
            
            try:
                tracer.add_tag('function.args', str(args))
                tracer.add_tag('function.kwargs', str(kwargs))
                
                result = await func(*args, **kwargs)
                
                tracer.finish_span(span_id, status='ok')
                return result
            except Exception as e:
                tracer.add_tag('error', str(e))
                tracer.finish_span(span_id, status='error')
                raise
        
        def sync_wrapper(*args, **kwargs):
            span_name = operation_name or func.__name__
            span_id = tracer.start_span(span_name)
            
            try:
                tracer.add_tag('function.args', str(args))
                tracer.add_tag('function.kwargs', str(kwargs))
                
                result = func(*args, **kwargs)
                
                tracer.finish_span(span_id, status='ok')
                return result
            except Exception as e:
                tracer.add_tag('error', str(e))
                tracer.finish_span(span_id, status='error')
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
