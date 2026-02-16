"""app.api.health

Health endpoints intended for platform probes (Render / Kubernetes style).

Design goals:
- /health/live  (liveness): must be *fast* and must *not* depend on external services.
- /health/ready (readiness): verifies critical dependencies (DB + Redis) with lightweight checks.

Note:
Render's healthCheckPath is polled very frequently. Keep it trivial.
"""

from __future__ import annotations

import time
from typing import Any, Dict

import redis.asyncio as redis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import db_manager

logger = get_logger(__name__)

START_TIME = time.monotonic()

router = APIRouter(prefix="/health", tags=["health"])


def _uptime_seconds() -> int:
    return int(time.monotonic() - START_TIME)


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness() -> Dict[str, Any]:
    """Liveness probe.

    Always returns 200 if the process is running.
    """
    return {
        "ok": True,
        "service": "cerebrum-api",
        "uptime_seconds": _uptime_seconds(),
    }


async def _check_database() -> Dict[str, Any]:
    """Lightweight DB check."""
    if db_manager._async_session_factory is None:  # pylint: disable=protected-access
        return {"ok": False, "error": "db_not_initialized"}

    try:
        async with db_manager.async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        logger.warning("DB readiness check failed", error=str(e))
        return {"ok": False, "error": "db_unreachable", "detail": str(e)}


async def _check_redis() -> Dict[str, Any]:
    """Lightweight Redis check."""
    try:
        r = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            await r.ping()
        finally:
            await r.close()
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        logger.warning("Redis readiness check failed", error=str(e))
        return {"ok": False, "error": "redis_unreachable", "detail": str(e)}


@router.get("/ready")
async def readiness() -> Dict[str, Any]:
    """Readiness probe.

    Returns 200 only when critical dependencies are reachable.
    """
    db = await _check_database()
    rd = await _check_redis()

    ok = bool(db.get("ok")) and bool(rd.get("ok"))
    payload = {
        "ok": ok,
        "service": "cerebrum-api",
        "uptime_seconds": _uptime_seconds(),
        "checks": {
            "db": db,
            "redis": rd,
        },
    }

    if ok:
        return payload

    # Readiness should return 503 when not ready
    payload["status"] = "not_ready"
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def health_metrics() -> Dict[str, Any]:
    """Tiny metrics payload (not Prometheus format)."""
    return {
        "service": "cerebrum-api",
        "uptime_seconds": _uptime_seconds(),
    }


# =============================================================================
# Standard Kubernetes/Render Health Check Aliases
# =============================================================================

@router.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz() -> Dict[str, Any]:
    """Kubernetes-style liveness probe alias."""
    return await liveness()


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def readyz() -> Dict[str, Any]:
    """Kubernetes-style readiness probe alias."""
    return await readiness()
