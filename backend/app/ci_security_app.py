"""Lean FastAPI app for Backend CI security-tests job (fast import/start)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.health import router as health_router
from app.api.v1.endpoints import admin, auth, dejavu
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.base_class import Base
from app.db.session import db_manager
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models.user import User  # noqa: F401 — register metadata

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def ci_security_lifespan(app: FastAPI):
    db_manager.initialize()
    async with db_manager.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with db_manager.async_session_factory() as session:
        await session.execute(text("SELECT 1"))
    logger.info("CI security app ready", version=settings.APP_VERSION)
    yield
    await db_manager.close()


app = FastAPI(
    title=f"{settings.APP_NAME} (CI security)",
    version=settings.APP_VERSION,
    lifespan=ci_security_lifespan,
)
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(health_router)
# auth.router already prefixes /auth → /api/v1/auth/*
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
# admin.router already prefixes /admin → /api/v1/admin/users (matches CI curl)
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
# dejavu.router already prefixes /dejavu → /api/v1/dejavu/schema
app.include_router(dejavu.router, prefix="/api/v1", tags=["dejavu"])
