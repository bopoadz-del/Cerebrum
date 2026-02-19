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

# Try to import optional endpoints
try:
    from app.api.v1.endpoints import google_drive
    GOOGLE_DRIVE_AVAILABLE = True
    logger.info("Google Drive endpoints loaded")
except Exception as e:
    GOOGLE_DRIVE_AVAILABLE = False
    logger.error(f"GOOGLE_DRIVE IMPORT FAILED: {e}")

try:
    from app.api.v1.endpoints import documents
    DOCUMENTS_AVAILABLE = True
    logger.info("Documents endpoints loaded")
except Exception as e:
    DOCUMENTS_AVAILABLE = False
    logger.warning(f"Documents endpoints not available: {e}")

# Create main router
router = APIRouter()

# Include core endpoints
router.include_router(health_router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(dejavu.router, prefix="/dejavu", tags=["dejavu"])
router.include_router(formulas.router, prefix="/formulas", tags=["formulas"])
router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
router.include_router(connectors.router, prefix="/connectors", tags=["connectors"])

# Include optional endpoints conditionally
if GOOGLE_DRIVE_AVAILABLE:
    router.include_router(google_drive.router, prefix="/drive", tags=["google-drive"])
    
if DOCUMENTS_AVAILABLE:
    router.include_router(documents.router, prefix="/documents", tags=["documents"])
