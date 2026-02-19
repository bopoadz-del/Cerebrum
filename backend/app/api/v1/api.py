"""
API Version 1 Router

Defines the v1 API routes and versioning configuration.
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Import endpoints with error handling for missing dependencies
from app.api.v1.endpoints import auth, admin, dejavu, formulas, sessions, connectors
from app.api.health import router as health_router

# Try to import optional endpoints that may have external dependencies
from app.api.v1.endpoints import google_drive
GOOGLE_DRIVE_AVAILABLE = True
logger.info("Google Drive endpoints loaded")

try:
    from app.api.v1.endpoints import documents
    DOCUMENTS_AVAILABLE = True
    logger.info("Documents endpoints loaded")
except Exception as e:
    DOCUMENTS_AVAILABLE = False
    logger.warning(f"Documents endpoints not available: {e}")

try:
    from app.api.v1.endpoints import safety
    SAFETY_AVAILABLE = True
    logger.info("Safety endpoints loaded")
except Exception as e:
    SAFETY_AVAILABLE = False
    logger.warning(f"Safety endpoints not available: {e}")

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

api_v1_router.include_router(
    sessions.router,
    tags=["Sessions"],
)

api_v1_router.include_router(
    connectors.router,
    tags=["Connectors"],
)

api_v1_router.include_router(
    health_router,
    prefix="/health",
    tags=["Health"],
)

if GOOGLE_DRIVE_AVAILABLE:
    api_v1_router.include_router(
        google_drive.router,
        prefix="/drive",
        tags=["Google Drive"],
    )

if DOCUMENTS_AVAILABLE:
    api_v1_router.include_router(
        documents.router,
        prefix="/documents",
        tags=["Document AI"],
    )

if SAFETY_AVAILABLE:
    api_v1_router.include_router(
        safety.router,
        prefix="/safety",
        tags=["Safety Analysis"],
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
