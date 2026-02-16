"""
API Version 1 Router

Defines the v1 API routes and versioning configuration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, admin, dejavu, formulas

# Create v1 router
api_v1_router = APIRouter()

# Include endpoint routers - NO prefix here, prefixes are in endpoint files
api_v1_router.include_router(
    auth.router,
    tags=["Authentication"],
)

api_v1_router.include_router(
    admin.router,
    tags=["Admin"],
)

api_v1_router.include_router(
    dejavu.router,
    tags=["Dejavu - Database Visualization"],
)

api_v1_router.include_router(
    formulas.router,
    tags=["Formulas"],
)


# API version info endpoint
@api_v1_router.get("/", tags=["Info"])
async def api_info() -> dict:
    """
    Get API version information.
    
    Returns:
        API version details
    """
    return {
        "version": "1.0.0",
        "name": "Cerebrum AI Platform API",
        "status": "stable",
        "documentation": "/api/docs",
    }
