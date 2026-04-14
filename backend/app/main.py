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

# Auto-register infrastructure blocks
import app.blocks.llm_enhancer, app.blocks.cache_manager, app.blocks.async_processor, app.blocks.file_hasher  # noqa: F401, E401
configure_logging()
logger = get_logger(__name__)


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

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.cors_methods_list,
        allow_headers=settings.cors_headers_list,
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.onrender.com", "localhost", "127.0.0.1", "*.web.app", "*.run.app", "*.firebaseapp.com"])

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

    # Middleware
    app.middleware("http")(add_correlation_id)
    app.middleware("http")(log_requests)

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.RELOAD, log_level="info", access_log=True)
