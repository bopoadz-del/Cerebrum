"""
Application lifespan manager for startup and shutdown events.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import get_logger
from app.core.sentry import init_sentry
from app.db.redis import redis_manager
from app.db.session import db_manager
from app.triggers import (
    event_bus,
    file_trigger_manager,
    ml_trigger_manager,
    safety_trigger_manager,
    audit_trigger_manager,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Cerebrum AI Platform", version=settings.APP_VERSION)

    if not settings.DATABASE_URL:
        logger.critical("FATAL: DATABASE_URL environment variable is missing")
        sys.exit(1)
    if not settings.REDIS_URL:
        logger.warning("REDIS_URL not set — Redis features (caching, rate-limiting) will be disabled")
    if not settings.DEBUG and not settings.CORS_ORIGINS:
        logger.warning("CORS_ORIGINS not set — defaulting to open CORS (set this in production)")
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        logger.critical("FATAL: SECRET_KEY must be at least 32 characters")
        sys.exit(1)

    logger.info("Security configuration validated")

    try:
        import redis.asyncio as redis
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        logger.info("Rate limiter storage (Redis) verified")
        await redis_manager.initialize()
    except Exception as e:
        # Redis is optional — used for caching/rate-limiting only.
        # Degrade gracefully so Cloud Run can start without a Redis instance.
        logger.warning(
            "Redis unavailable — rate limiting and caching disabled",
            error=str(e),
        )

    init_sentry()
    db_manager.initialize()

    try:
        async with db_manager.async_session_factory() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as e:
        logger.critical("FATAL: Database connection failed", error=str(e))
        sys.exit(1)

    logger.info("Initializing trigger engine")
    await event_bus.start()
    logger.info(
        "Trigger managers initialized",
        file_triggers=True,
        ml_triggers=True,
        safety_triggers=True,
        audit_triggers=True,
    )

    local_watcher = None
    if os.getenv("WATCH_LOCAL_FILES", "false").lower() == "true":
        from app.platform.local_filesystem.watcher import init_watcher
        local_watcher = init_watcher()
        if local_watcher:
            logger.info("Local filesystem watcher active")

    yield

    if local_watcher:
        from app.platform.local_filesystem.watcher import stop_watcher
        stop_watcher()

    logger.info("Shutting down Cerebrum AI Platform")
    await event_bus.stop()
    try:
        await redis_manager.close()
    except Exception:
        pass
    await db_manager.close()
