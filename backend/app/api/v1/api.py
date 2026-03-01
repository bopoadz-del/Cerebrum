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
    from app.api.v1.endpoints import documents
    DOCUMENTS_AVAILABLE = True
    logger.info("Documents endpoints loaded")
except Exception as e:
    DOCUMENTS_AVAILABLE = False
    logger.warning(f"Documents endpoints not available: {e}")

try:
    from app.api.v1.endpoints import google_drive
    GOOGLE_DRIVE_AVAILABLE = True
    logger.info("Google Drive endpoints loaded")
except Exception as e:
    GOOGLE_DRIVE_AVAILABLE = False
    logger.warning(f"Google Drive endpoints not available: {e}")



# Create main router - MUST BE NAMED api_v1_router for main.py
api_v1_router = APIRouter()

# Include core endpoints
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth.router, tags=["authentication"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_v1_router.include_router(dejavu.router, prefix="/dejavu", tags=["dejavu"])
api_v1_router.include_router(formulas.router, prefix="/formulas", tags=["formulas"])
api_v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_v1_router.include_router(connectors.router, tags=["connectors"])

# Include optional endpoints conditionally
if DOCUMENTS_AVAILABLE:
    api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])

# Google Drive endpoints are already included via connectors.router
# The connectors.py module provides /connectors/google-drive/* endpoints
# DO NOT include google_drive.router separately - it would cause route conflicts
