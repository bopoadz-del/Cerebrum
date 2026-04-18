"""
Cerebrum Prometheus Metrics Module

Provides Prometheus instrumentation for FastAPI endpoints, Celery workers,
PostgreSQL database, and custom business metrics.

Usage:
    from app.monitoring.metrics import metrics, FormulaMetrics
    
    # In endpoint:
    metrics.http_request_total.labels(method="GET", endpoint="/api/v1/formulas").inc()
    
    # In formula execution:
    FormulaMetrics.record_execution(domain="structural", success=True, duration=0.5)
"""

import time
from functools import wraps
from typing import Callable, Optional

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    multiprocess,
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# =============================================================================
# Registry Configuration
# =============================================================================

# Use multi-process registry for production (gunicorn with multiple workers)
# Falls back to default registry for single-process development
REGISTRY = CollectorRegistry()
try:
    multiprocess.MultiProcessCollector(REGISTRY)
except Exception:
    # Not running in multi-process mode
    pass

# =============================================================================
# FastAPI HTTP Metrics
# =============================================================================

http_request_total = Counter(
    "cerebrum_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "cerebrum_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=REGISTRY,
)

http_request_in_progress = Gauge(
    "cerebrum_http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
    registry=REGISTRY,
)

http_response_size_bytes = Histogram(
    "cerebrum_http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
    registry=REGISTRY,
)

# =============================================================================
# Business Metrics - Formula Execution
# =============================================================================

formula_execution_total = Counter(
    "cerebrum_formula_executions_total",
    "Total formula executions",
    ["domain", "formula_id", "status"],  # status: success, error, timeout
    registry=REGISTRY,
)

formula_execution_duration_seconds = Histogram(
    "cerebrum_formula_execution_duration_seconds",
    "Formula execution duration in seconds",
    ["domain", "formula_id"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=REGISTRY,
)

formula_validation_errors_total = Counter(
    "cerebrum_formula_validation_errors_total",
    "Total formula validation errors",
    ["error_type", "domain"],  # error_type: invalid_input, division_by_zero, unit_mismatch, etc.
    registry=REGISTRY,
)

formula_cache_hits_total = Counter(
    "cerebrum_formula_cache_hits_total",
    "Total formula cache hits",
    ["formula_id"],
    registry=REGISTRY,
)

formula_cache_misses_total = Counter(
    "cerebrum_formula_cache_misses_total",
    "Total formula cache misses",
    ["formula_id"],
    registry=REGISTRY,
)

# =============================================================================
# Business Metrics - Validation Pipeline
# =============================================================================

validation_total = Counter(
    "cerebrum_validations_total",
    "Total validation runs",
    ["stage", "status"],  # stage: security, sandbox, integration; status: passed, failed
    registry=REGISTRY,
)

validation_duration_seconds = Histogram(
    "cerebrum_validation_duration_seconds",
    "Validation duration in seconds",
    ["stage"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=REGISTRY,
)

security_issues_total = Counter(
    "cerebrum_security_issues_total",
    "Total security issues found",
    ["severity", "scanner"],  # severity: critical, high, medium, low
    registry=REGISTRY,
)

sandbox_execution_total = Counter(
    "cerebrum_sandbox_executions_total",
    "Total sandbox executions",
    ["language", "status"],  # language: python, javascript, etc.
    registry=REGISTRY,
)

# =============================================================================
# Celery Worker Metrics
# =============================================================================

celery_task_total = Counter(
    "cerebrum_celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],  # status: received, started, success, failure, retry
    registry=REGISTRY,
)

celery_task_duration_seconds = Histogram(
    "cerebrum_celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
    registry=REGISTRY,
)

celery_task_retry_total = Counter(
    "cerebrum_celery_task_retries_total",
    "Total Celery task retries",
    ["task_name"],
    registry=REGISTRY,
)

celery_workers_active = Gauge(
    "cerebrum_celery_workers_active",
    "Number of active Celery workers",
    registry=REGISTRY,
)

celery_queue_length = Gauge(
    "cerebrum_celery_queue_length",
    "Current length of Celery queues",
    ["queue_name"],
    registry=REGISTRY,
)

# =============================================================================
# PostgreSQL Database Metrics
# =============================================================================

db_connections_active = Gauge(
    "cerebrum_db_connections_active",
    "Active database connections",
    registry=REGISTRY,
)

db_connections_idle = Gauge(
    "cerebrum_db_connections_idle",
    "Idle database connections",
    registry=REGISTRY,
)

db_query_duration_seconds = Histogram(
    "cerebrum_db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],  # query_type: select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=REGISTRY,
)

db_query_total = Counter(
    "cerebrum_db_queries_total",
    "Total database queries",
    ["query_type", "table"],
    registry=REGISTRY,
)

db_transaction_total = Counter(
    "cerebrum_db_transactions_total",
    "Total database transactions",
    ["status"],  # status: committed, rolled_back
    registry=REGISTRY,
)

db_pool_size = Gauge(
    "cerebrum_db_pool_size",
    "Database connection pool size",
    registry=REGISTRY,
)

db_pool_overflow = Gauge(
    "cerebrum_db_pool_overflow",
    "Database connection pool overflow",
    registry=REGISTRY,
)

# =============================================================================
# LLM/AI Service Metrics
# =============================================================================

llm_request_total = Counter(
    "cerebrum_llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"],  # provider: openai, deepseek, etc.
    registry=REGISTRY,
)

llm_request_duration_seconds = Histogram(
    "cerebrum_llm_request_duration_seconds",
    "LLM API request duration in seconds",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

llm_tokens_total = Counter(
    "cerebrum_llm_tokens_total",
    "Total LLM tokens processed",
    ["provider", "type"],  # type: prompt, completion
    registry=REGISTRY,
)

llm_cost_dollars = Counter(
    "cerebrum_llm_cost_dollars_total",
    "Estimated LLM API cost in dollars",
    ["provider", "model"],
    registry=REGISTRY,
)

# =============================================================================
# Document Processing Metrics
# =============================================================================

document_upload_total = Counter(
    "cerebrum_document_uploads_total",
    "Total document uploads",
    ["mime_type", "status"],
    registry=REGISTRY,
)

document_processing_duration_seconds = Histogram(
    "cerebrum_document_processing_duration_seconds",
    "Document processing duration in seconds",
    ["mime_type", "operation"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=REGISTRY,
)

document_size_bytes = Histogram(
    "cerebrum_document_size_bytes",
    "Document size in bytes",
    ["mime_type"],
    buckets=[1024, 10240, 102400, 1048576, 10485760, 52428800],
    registry=REGISTRY,
)

vector_search_duration_seconds = Histogram(
    "cerebrum_vector_search_duration_seconds",
    "Vector search duration in seconds",
    ["index_name"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

# =============================================================================
# System/Application Info
# =============================================================================

app_info = Info(
    "cerebrum_app",
    "Application information",
    registry=REGISTRY,
)

# Set initial app info
app_info.info({
    "name": "Cerebrum AI Platform",
    "version": "1.0.0",
    "python_version": "3.11",
})

# =============================================================================
# Metric Helper Classes
# =============================================================================

class FormulaMetrics:
    """Helper class for formula-related metrics."""
    
    @staticmethod
    def record_execution(domain: str, formula_id: str, success: bool, duration: float) -> None:
        """Record a formula execution."""
        status = "success" if success else "error"
        formula_execution_total.labels(
            domain=domain,
            formula_id=formula_id,
            status=status
        ).inc()
        formula_execution_duration_seconds.labels(
            domain=domain,
            formula_id=formula_id
        ).observe(duration)
    
    @staticmethod
    def record_validation_error(error_type: str, domain: str) -> None:
        """Record a formula validation error."""
        formula_validation_errors_total.labels(
            error_type=error_type,
            domain=domain
        ).inc()
    
    @staticmethod
    def record_cache_hit(formula_id: str) -> None:
        """Record a formula cache hit."""
        formula_cache_hits_total.labels(formula_id=formula_id).inc()
    
    @staticmethod
    def record_cache_miss(formula_id: str) -> None:
        """Record a formula cache miss."""
        formula_cache_misses_total.labels(formula_id=formula_id).inc()


class ValidationMetrics:
    """Helper class for validation pipeline metrics."""
    
    @staticmethod
    def record_validation(stage: str, passed: bool, duration: float) -> None:
        """Record a validation run."""
        status = "passed" if passed else "failed"
        validation_total.labels(stage=stage, status=status).inc()
        validation_duration_seconds.labels(stage=stage).observe(duration)
    
    @staticmethod
    def record_security_issue(severity: str, scanner: str) -> None:
        """Record a security issue."""
        security_issues_total.labels(severity=severity, scanner=scanner).inc()
    
    @staticmethod
    def record_sandbox_execution(language: str, success: bool) -> None:
        """Record a sandbox execution."""
        status = "success" if success else "failure"
        sandbox_execution_total.labels(language=language, status=status).inc()


class CeleryMetrics:
    """Helper class for Celery worker metrics."""
    
    @staticmethod
    def record_task_received(task_name: str) -> None:
        """Record task received."""
        celery_task_total.labels(task_name=task_name, status="received").inc()
    
    @staticmethod
    def record_task_started(task_name: str) -> None:
        """Record task started."""
        celery_task_total.labels(task_name=task_name, status="started").inc()
    
    @staticmethod
    def record_task_success(task_name: str, duration: float) -> None:
        """Record task success."""
        celery_task_total.labels(task_name=task_name, status="success").inc()
        celery_task_duration_seconds.labels(task_name=task_name).observe(duration)
    
    @staticmethod
    def record_task_failure(task_name: str) -> None:
        """Record task failure."""
        celery_task_total.labels(task_name=task_name, status="failure").inc()
    
    @staticmethod
    def record_task_retry(task_name: str) -> None:
        """Record task retry."""
        celery_task_retry_total.labels(task_name=task_name).inc()


class DatabaseMetrics:
    """Helper class for database metrics."""
    
    @staticmethod
    def record_query(query_type: str, table: str, duration: float) -> None:
        """Record a database query."""
        db_query_total.labels(query_type=query_type, table=table).inc()
        db_query_duration_seconds.labels(query_type=query_type).observe(duration)
    
    @staticmethod
    def record_transaction(committed: bool) -> None:
        """Record a database transaction."""
        status = "committed" if committed else "rolled_back"
        db_transaction_total.labels(status=status).inc()


class LLMMetrics:
    """Helper class for LLM service metrics."""
    
    @staticmethod
    def record_request(provider: str, model: str, success: bool, duration: float) -> None:
        """Record an LLM request."""
        status = "success" if success else "error"
        llm_request_total.labels(provider=provider, model=model, status=status).inc()
        llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration)
    
    @staticmethod
    def record_tokens(provider: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token usage."""
        llm_tokens_total.labels(provider=provider, type="prompt").inc(prompt_tokens)
        llm_tokens_total.labels(provider=provider, type="completion").inc(completion_tokens)
    
    @staticmethod
    def record_cost(provider: str, model: str, cost: float) -> None:
        """Record estimated cost."""
        llm_cost_dollars.labels(provider=provider, model=model).inc(cost)


# =============================================================================
# Decorators for Easy Instrumentation
# =============================================================================

def timed(metric: Histogram, labels: Optional[dict] = None):
    """Decorator to time function execution and record to histogram."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                label_values = labels or {}
                metric.labels(**label_values).observe(duration)
        return wrapper
    return decorator


def counted(metric: Counter, labels: Optional[dict] = None):
    """Decorator to count function calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            label_values = labels or {}
            metric.labels(**label_values).inc()
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# FastAPI Middleware for Automatic HTTP Metrics
# =============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic Prometheus metrics collection.
    
    Tracks:
    - Request count by method, endpoint, status code
    - Request duration
    - Requests in progress
    - Response size
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = request.url.path
        
        # Track in-progress requests
        http_request_in_progress.labels(method=method, endpoint=path).inc()
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Record response size if available
            if hasattr(response, 'body'):
                response_size = len(response.body) if response.body else 0
                http_response_size_bytes.labels(
                    method=method, endpoint=path
                ).observe(response_size)
            
            return response
            
        except Exception as e:
            status_code = 500
            raise
            
        finally:
            # Record metrics
            duration = time.time() - start_time
            
            http_request_total.labels(
                method=method,
                endpoint=path,
                status_code=str(status_code)
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            http_request_in_progress.labels(method=method, endpoint=path).dec()


# =============================================================================
# Metrics Export Endpoint
# =============================================================================

def get_metrics_response() -> tuple:
    """
    Generate Prometheus metrics response.
    
    Returns:
        Tuple of (content, content_type) for HTTP response
    """
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


# =============================================================================
# Unified Metrics Interface
# =============================================================================

class Metrics:
    """
    Unified metrics interface for easy access to all metric types.
    
    This provides a single object to import for common metric operations.
    """
    
    # HTTP Metrics
    http_request_total = http_request_total
    http_request_duration_seconds = http_request_duration_seconds
    http_request_in_progress = http_request_in_progress
    http_response_size_bytes = http_response_size_bytes
    
    # Formula Metrics
    formula_execution_total = formula_execution_total
    formula_execution_duration_seconds = formula_execution_duration_seconds
    formula_validation_errors_total = formula_validation_errors_total
    formula_cache_hits_total = formula_cache_hits_total
    formula_cache_misses_total = formula_cache_misses_total
    
    # Validation Metrics
    validation_total = validation_total
    validation_duration_seconds = validation_duration_seconds
    security_issues_total = security_issues_total
    sandbox_execution_total = sandbox_execution_total
    
    # Celery Metrics
    celery_task_total = celery_task_total
    celery_task_duration_seconds = celery_task_duration_seconds
    celery_task_retry_total = celery_task_retry_total
    celery_workers_active = celery_workers_active
    celery_queue_length = celery_queue_length
    
    # Database Metrics
    db_connections_active = db_connections_active
    db_connections_idle = db_connections_idle
    db_query_duration_seconds = db_query_duration_seconds
    db_query_total = db_query_total
    db_transaction_total = db_transaction_total
    db_pool_size = db_pool_size
    db_pool_overflow = db_pool_overflow
    
    # LLM Metrics
    llm_request_total = llm_request_total
    llm_request_duration_seconds = llm_request_duration_seconds
    llm_tokens_total = llm_tokens_total
    llm_cost_dollars = llm_cost_dollars
    
    # Helper Classes
    FormulaMetrics = FormulaMetrics
    ValidationMetrics = ValidationMetrics
    CeleryMetrics = CeleryMetrics
    DatabaseMetrics = DatabaseMetrics
    LLMMetrics = LLMMetrics
    
    # Middleware
    PrometheusMiddleware = PrometheusMiddleware
    
    # Export
    get_metrics_response = get_metrics_response
    REGISTRY = REGISTRY


# Singleton metrics instance
metrics = Metrics()


# =============================================================================
# Legacy compatibility - keep existing module imports working
# =============================================================================

# Make metrics module available as 'metrics'
__all__ = [
    # Main metrics object
    "metrics",
    # Metrics
    "http_request_total",
    "http_request_duration_seconds",
    "http_request_in_progress",
    "formula_execution_total",
    "formula_execution_duration_seconds",
    "formula_validation_errors_total",
    "celery_task_total",
    "celery_task_duration_seconds",
    "db_query_duration_seconds",
    "llm_request_total",
    # Helpers
    "FormulaMetrics",
    "ValidationMetrics",
    "CeleryMetrics",
    "DatabaseMetrics",
    "LLMMetrics",
    # Middleware
    "PrometheusMiddleware",
    # Export
    "get_metrics_response",
    "REGISTRY",
]