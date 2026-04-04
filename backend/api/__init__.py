"""
Compatibility API routers.

External tests may import modules from `backend.api.*`. Each module exposes a FastAPI
`router`. The application can include them via `get_compat_router()`.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import analytics, analytics_reports_system, upload, vision, openai_test, projects, users

def get_compat_router(prefix: str = "/api/compat") -> APIRouter:
    r = APIRouter(prefix=prefix, tags=["compat"])
    r.include_router(analytics.router, prefix="/analytics")
    r.include_router(analytics_reports_system.router, prefix="/analytics-reports")
    r.include_router(upload.router, prefix="/upload")
    r.include_router(vision.router, prefix="/vision")
    r.include_router(openai_test.router, prefix="/openai-test")
    r.include_router(projects.router, prefix="/projects")
    r.include_router(users.router, prefix="/users")
    return r
