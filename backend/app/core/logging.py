"""
Structured Logging Configuration

Provides structured JSON logging using structlog for production
observability and debugging.
"""

import logging
import logging.config
import re
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog
from structlog.processors import JSONRenderer

from app.core.config import settings


# =============================================================================
# Secret Redaction Filter
# =============================================================================

class SecretFilter(logging.Filter):
    """
    Filter to redact sensitive values from logs.
    
    Prevents accidental leakage of secrets like SECRET_KEY,
    passwords, tokens, and API keys in log output.
    """
    
    # Patterns to redact
    SENSITIVE_PATTERNS = [
        (r'["\']?secret[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', '***REDACTED***'),
        (r'["\']?password["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', '***REDACTED***'),
        (r'["\']?token["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', '***REDACTED***'),
        (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', '***REDACTED***'),
        (r'["\']?private[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s]+["\']?', '***REDACTED***'),
        (r'Bearer\s+[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', 'Bearer ***REDACTED***'),
    ]
    
    def __init__(self, secrets: Optional[list] = None):
        """Initialize filter with optional additional secrets."""
        super().__init__()
        self.secrets = secrets or []
        if settings.SECRET_KEY:
            self.secrets.append(settings.SECRET_KEY)
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive information from log record."""
        # Redact from message
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        
        # Redact from args
        if record.args:
            record.args = tuple(
                self._redact(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def _redact(self, text: str) -> str:
        """Redact sensitive patterns from text."""
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Redact any configured secrets
        for secret in self.secrets:
            if secret and len(secret) > 3:  # Avoid replacing short strings
                text = text.replace(secret, '***REDACTED***')
        
        return text

# Correlation ID context variable for distributed tracing
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


# =============================================================================
# Logging Configuration
# =============================================================================

def configure_logging() -> None:
    """
    Configure structured logging for the application.
    
    Sets up both standard library logging and structlog for
    consistent JSON-formatted logs in production.
    """
    # Determine log format based on environment
    is_json = settings.LOG_FORMAT == "json" and not settings.is_development
    
    # Standard library logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": JSONRenderer(),
                "foreign_pre_chain": [
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.add_logger_name,
                    structlog.processors.TimeStamper(fmt="iso"),
                ],
            },
            "console": {
                "format": '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}',
            },
        },
        "filters": {
            "secret_filter": {
                "()": SecretFilter,
            },
        },
        "handlers": {
            "default": {
                "level": settings.LOG_LEVEL.value,
                "class": "logging.StreamHandler",
                "formatter": "json" if is_json else "console",
                "stream": sys.stdout,
                "filters": ["secret_filter"],
            },
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": settings.LOG_LEVEL.value,
                "propagate": True,
            },
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["default"],
                "level": "WARNING" if not settings.DEBUG else "INFO",
                "propagate": False,
            },
        },
    }
    
    # Add file handler if configured
    if settings.LOG_FILE:
        logging_config["handlers"]["file"] = {
            "level": settings.LOG_LEVEL.value,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.LOG_FILE,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json" if is_json else "console",
        }
        logging_config["loggers"][""]["handlers"].append("file")
    
    logging.config.dictConfig(logging_config)
    
    # Configure structlog
    structlog_processors = [
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if is_json:
        structlog_processors.append(JSONRenderer())
    else:
        structlog_processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=structlog_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# =============================================================================
# Logger Factory
# =============================================================================

def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (defaults to caller module)
        
    Returns:
        Structured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("User logged in", user_id="123", ip="192.168.1.1")
    """
    return structlog.get_logger(name)


# =============================================================================
# Context Binding
# =============================================================================

class LogContext:
    """
    Context manager for adding context to logs.
    
    Example:
        with LogContext(request_id="abc123", user_id="user456"):
            logger.info("Processing request")
            # Logs will include request_id and user_id
    """
    
    def __init__(self, **context: Any) -> None:
        """
        Initialize log context.
        
        Args:
            **context: Key-value pairs to add to log context
        """
        self.context = context
        self.token = None
    
    def __enter__(self) -> "LogContext":
        """Enter context."""
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context."""
        structlog.contextvars.reset_contextvars(self.token)


def bind_context(**context: Any) -> None:
    """
    Bind context variables to all subsequent logs.
    
    Args:
        **context: Key-value pairs to bind
        
    Example:
        bind_context(request_id="abc123")
        logger.info("Processing")  # Will include request_id
    """
    structlog.contextvars.bind_contextvars(**context)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


# =============================================================================
# Request Logging Middleware
# =============================================================================

class RequestLoggingMiddleware:
    """
    Middleware for logging HTTP requests.
    
    Logs request details including method, path, status code,
    and processing time.
    """
    
    def __init__(self) -> None:
        """Initialize middleware."""
        self.logger = get_logger("http.request")
    
    async def __call__(self, request: Any, call_next: Any) -> Any:
        """
        Process request and log details.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        import time
        
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        request_id = request.headers.get("x-request-id")
        
        # Bind context
        with LogContext(
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
        ):
            self.logger.info(
                "Request started",
                method=method,
                path=path,
            )
            
            try:
                response = await call_next(request)
                
                duration = time.time() - start_time
                
                self.logger.info(
                    "Request completed",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                )
                
                return response
                
            except Exception as e:
                duration = time.time() - start_time
                
                self.logger.error(
                    "Request failed",
                    method=method,
                    path=path,
                    error=str(e),
                    duration_ms=round(duration * 1000, 2),
                )
                
                raise


# =============================================================================
# Performance Logging
# =============================================================================

class PerformanceLogger:
    """
    Utility for logging performance metrics.
    
    Example:
        with PerformanceLogger("database_query"):
            result = await db.execute(query)
    """
    
    def __init__(self, operation: str, logger: Optional[Any] = None) -> None:
        """
        Initialize performance logger.
        
        Args:
            operation: Operation name
            logger: Logger instance
        """
        self.operation = operation
        self.logger = logger or get_logger("performance")
        self.start_time: Optional[float] = None
    
    def __enter__(self) -> "PerformanceLogger":
        """Start timing."""
        import time
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Log duration."""
        import time
        
        if self.start_time:
            duration = time.time() - self.start_time
            
            log_data = {
                "operation": self.operation,
                "duration_ms": round(duration * 1000, 2),
            }
            
            if exc_type:
                log_data["error"] = str(exc_val)
                self.logger.warning("Operation failed", **log_data)
            else:
                self.logger.debug("Operation completed", **log_data)


# Initialize logging on module import
configure_logging()
