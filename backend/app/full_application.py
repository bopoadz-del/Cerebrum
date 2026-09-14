"""
Cerebrum AI - Construction Intelligence Platform
Main FastAPI Application Entry Point
"""

import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.api import api_v1_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.logging import configure_logging, get_logger
from app.middleware.exception import setup_exception_handlers
from app.middleware.rate_limit import limiter, safe_rate_limit_handler
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.correlation import add_correlation_id
from app.middleware.logging import log_requests
from app.monitoring.metrics import PrometheusMiddleware
from app.routers import (
    blocks_router,
    chat_router,
    chain_router,
    execute_router,
    health_router_root,
    monitoring_router,
    root_router,
    upload_router,
)
from app.learning.endpoints import router as learning_router

configure_logging()
logger = get_logger(__name__)

# MLflow router (optional)
try:
    from app.routers.mlflow import router as mlflow_router
    MLFLOW_AVAILABLE = True
except Exception:
    MLFLOW_AVAILABLE = False
    mlflow_router = None

# Orchestrator and Reasoning routers
try:
    from app.orchestrator.endpoints import router as orchestrator_router
    ORCHESTRATOR_AVAILABLE = True
except Exception as e:
    logger.warning(f"Orchestrator router not available: {e}")
    ORCHESTRATOR_AVAILABLE = False
    orchestrator_router = None

try:
    from app.reasoning.endpoints import router as reasoning_router
    REASONING_AVAILABLE = True
except Exception as e:
    logger.warning(f"Reasoning router not available: {e}")
    REASONING_AVAILABLE = False
    reasoning_router = None

# Auto-register infrastructure blocks
import app.blocks.llm_enhancer, app.blocks.cache_manager, app.blocks.async_processor, app.blocks.file_hasher  # noqa: F401, E401


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Construction Intelligence Platform - 14-Layer Architecture",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, safe_rate_limit_handler)

    # Add Prometheus middleware first to capture all requests
    app.add_middleware(PrometheusMiddleware)

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=settings.CORS_ORIGINS_REGEX,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.cors_methods_list,
        allow_headers=settings.cors_headers_list,
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "*.onrender.com",
            "localhost",
            "127.0.0.1",
            "*.web.app",
            "*.run.app",
            "*.firebaseapp.com",
            "cerebrum.ai",
            "*.cerebrum.ai",
        ],
    )

    setup_exception_handlers(app)

    # Core routers
    app.include_router(health_router, tags=["health"])
    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1", tags=["health"])

    # Root-level routers
    app.include_router(health_router_root)
    app.include_router(blocks_router)
    app.include_router(root_router)
    app.include_router(monitoring_router)
    app.include_router(chat_router)
    app.include_router(upload_router)
    app.include_router(execute_router)
    app.include_router(chain_router)
    
    # MLflow router
    if MLFLOW_AVAILABLE and mlflow_router:
        app.include_router(mlflow_router)
    app.include_router(learning_router)
    
    # Orchestrator and Reasoning routers
    if ORCHESTRATOR_AVAILABLE and orchestrator_router:
        app.include_router(orchestrator_router, prefix="/api/v1")
        logger.info("Orchestrator router included")
    
    if REASONING_AVAILABLE and reasoning_router:
        app.include_router(reasoning_router, prefix="/api/v1")
        logger.info("Reasoning router included")

    # Middleware
    app.middleware("http")(add_correlation_id)
    app.middleware("http")(log_requests)

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.RELOAD, log_level="info", access_log=True)
