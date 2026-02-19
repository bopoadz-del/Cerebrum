"""
Cerebrum AI - Construction Intelligence Platform
Main FastAPI Application Entry Point

This module initializes the FastAPI application with all routes,
middleware, and configurations for the 14-layer architecture.
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

from app.core.cors import setup_cors
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.api import api_v1_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.sentry import init_sentry
from app.db.session import db_manager, get_db_session
from app.db.redis import redis_manager
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.exception import setup_exception_handlers
from app.triggers import (
    event_bus,
    file_trigger_manager,
    ml_trigger_manager,
    safety_trigger_manager,
    audit_trigger_manager,
)

# Configure structured logging
configure_logging()
logger = get_logger(__name__)


# Global rate limiter with default limits
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute", "1000/hour"],
    storage_uri=settings.redis_url,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Cerebrum AI Platform", version=settings.APP_VERSION)
    
    # =============================================================================
    # H18: Production Config Validation Block
    # =============================================================================
    
    # Validate DATABASE_URL
    if not settings.DATABASE_URL:
        logger.critical("FATAL: DATABASE_URL environment variable is missing")
        sys.exit(1)
    
    # Validate REDIS_URL
    if not settings.REDIS_URL:
        logger.critical("FATAL: REDIS_URL environment variable is missing")
        sys.exit(1)
    
    # Validate CORS_ORIGINS in production
    if not settings.DEBUG:
        if not settings.CORS_ORIGINS:
            logger.critical("FATAL: CORS_ORIGINS must be set in production")
            sys.exit(1)
    
    # =============================================================================
    # A3: Enforce Strong SECRET_KEY
    # =============================================================================
    
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        logger.critical("FATAL: SECRET_KEY must be at least 32 characters")
        sys.exit(1)
    
    logger.info("Security configuration validated")
    
    # =============================================================================
    # C7: Explicit Redis Storage Failure Policy
    # =============================================================================
    
    try:
        # Verify Redis connection for rate limiting
        import redis.asyncio as redis
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        logger.info("Rate limiter storage (Redis) verified")
        # Initialize shared Redis connection pools (cache/queue/sessions/ratelimit)
        await redis_manager.initialize()
    except Exception as e:
        logger.critical("FATAL: Rate limiter storage (Redis) unavailable", error=str(e))
        sys.exit(1)
    
    # Initialize Sentry
    init_sentry()
    
    # Initialize database
    db_manager.initialize()
    
    # Test database connection
    try:
        async with db_manager.async_session_factory() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as e:
        logger.critical("FATAL: Database connection failed", error=str(e))
        sys.exit(1)
    
    # Initialize trigger engine
    logger.info("Initializing trigger engine")
    await event_bus.start()
    
    # Log trigger manager status
    logger.info(
        "Trigger managers initialized",
        file_triggers=True,
        ml_triggers=True,
        safety_triggers=True,
        audit_triggers=True,
    )
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cerebrum AI Platform")
    await event_bus.stop()
    try:
        await redis_manager.close()
    except Exception:
        pass
    await db_manager.close()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Construction Intelligence Platform - 14-Layer Architecture",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Attach rate limiter to app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add middleware (order matters - last added = first executed)
    
    # Rate limiting middleware (must be early) - use SlowAPIMiddleware
    app.add_middleware(SlowAPIMiddleware)
    
    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Trusted Host Middleware (OWASP security)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.onrender.com", "localhost", "127.0.0.1"]
    )
    
    # CORS - dynamic Render domains
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.cors_methods_list,
        allow_headers=settings.cors_headers_list,
        expose_headers=["X-Request-ID"],
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    app.include_router(health_router, tags=["health"])
    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    
    # Root-level health aliases for compatibility
    @app.get("/healthz", tags=["health"])
    async def root_healthz():
        """Root-level Kubernetes liveness probe."""
        from app.api.health import liveness
        return await liveness()
    
    @app.get("/readyz", tags=["health"])
    async def root_readyz():
        """Root-level Kubernetes readiness probe."""
        from app.api.health import readiness
        return await readiness()
    
    return app


# Create the application instance
app = create_application()


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Construction Intelligence Platform",
        "documentation": "/api/docs",
        "health": "/health",
        "status": "operational",
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_version": "v1",
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "projects": "/api/v1/projects",
            "documents": "/api/v1/documents",
            "bim": "/api/v1/bim",
            "ml": "/api/v1/ml",
            "economics": "/api/v1/economics",
            "vdc": "/api/v1/vdc",
            "integrations": "/api/v1/integrations",
            "warehouse": "/api/v1/warehouse",
            "quality": "/api/v1/quality",
            "edge": "/api/v1/edge",
            "enterprise": "/api/v1/enterprise",
            "portal": "/api/v1/portal",
            "registry": "/api/v1/registry",
            "coding": "/api/v1/coding",
        },
    }


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add OWASP security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # HSTS only on HTTPS (enterprise requirement)
    if request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    return response


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID for distributed tracing."""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Structured access logging middleware."""
    import time
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=f"{duration:.2f}",
        client_host=request.client.host if request.client else None,
    )
    return response


# =============================================================================
# Metrics Endpoint
# =============================================================================

START_TIME = __import__('time').time()
REQUEST_COUNTER = 0

@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint for monitoring."""
    import time
    return {
        "uptime_seconds": time.time() - START_TIME,
        "uptime_formatted": f"{int((time.time() - START_TIME) / 86400)}d {int((time.time() - START_TIME) % 86400 / 3600)}h {int((time.time() - START_TIME) % 3600 / 60)}m",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level="info",
        access_log=True,
    )
