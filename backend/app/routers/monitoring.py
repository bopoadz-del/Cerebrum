"""
Monitoring router - Prometheus metrics and health information.
"""

import time
from fastapi import APIRouter, Response

from app.core.config import settings
from app.monitoring.metrics import get_metrics_response, REGISTRY

router = APIRouter(tags=["monitoring"])

START_TIME = time.time()


@router.get("/health")
async def health():
    """Basic health check endpoint."""
    uptime = time.time() - START_TIME
    return {
        "status": "healthy",
        "uptime_seconds": uptime,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
    }


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format for scraping.
    Includes:
    - HTTP request metrics
    - Formula execution metrics
    - Celery worker metrics
    - Database metrics
    - LLM service metrics
    """
    content, media_type = get_metrics_response()
    return Response(content=content, media_type=media_type)


@router.get("/ready")
async def ready():
    """Kubernetes readiness probe."""
    return {"status": "ready"}


@router.get("/live")
async def live():
    """Kubernetes liveness probe."""
    return {"status": "alive"}
