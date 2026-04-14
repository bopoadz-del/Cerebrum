"""
Monitoring router - metrics and uptime information.
"""

import time
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["monitoring"])

START_TIME = time.time()


@router.get("/metrics")
async def metrics():
    """Basic metrics endpoint for monitoring."""
    uptime = time.time() - START_TIME
    return {
        "uptime_seconds": uptime,
        "uptime_formatted": (
            f"{int(uptime / 86400)}d "
            f"{int(uptime % 86400 / 3600)}h "
            f"{int(uptime % 3600 / 60)}m"
        ),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
    }
