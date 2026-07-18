"""Minimal FastAPI entry for CI smoke tests (fast startup under uvicorn)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.health import router as health_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import db_manager

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def smoke_lifespan(app: FastAPI):
    db_manager.initialize()
    async with db_manager.async_session_factory() as session:
        await session.execute(text("SELECT 1"))
    logger.info("CI smoke app ready", version=settings.APP_VERSION)
    yield
    await db_manager.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=smoke_lifespan,
)
app.include_router(health_router)
