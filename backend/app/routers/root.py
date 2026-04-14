"""
Root router - API root information.
"""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["root"])


@router.get("/")
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


@router.get("/api")
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
