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

# Core endpoints - REQUIRED for frontend
from app.api.v1.endpoints import chat
from app.agent.enhanced_endpoints import router as agent_router

# Try to import optional endpoints
try:
    from app.api.v1.endpoints import documents
    DOCUMENTS_AVAILABLE = True
    logger.info("Documents endpoints loaded")
except Exception as e:
    DOCUMENTS_AVAILABLE = False
    logger.warning(f"Documents endpoints not available: {e}")

# Try to import other optional endpoints
try:
    from app.api.v1.endpoints import bim
    BIM_AVAILABLE = True
    logger.info("BIM endpoints loaded")
except Exception as e:
    BIM_AVAILABLE = False
    logger.warning(f"BIM endpoints not available: {e}")

try:
    from app.api.v1.endpoints import economics
    ECONOMICS_AVAILABLE = True
    logger.info("Economics endpoints loaded")
except Exception as e:
    ECONOMICS_AVAILABLE = False
    logger.warning(f"Economics endpoints not available: {e}")

try:
    from app.api.v1.endpoints import vdc
    VDC_AVAILABLE = True
    logger.info("VDC endpoints loaded")
except Exception as e:
    VDC_AVAILABLE = False
    logger.warning(f"VDC endpoints not available: {e}")

try:
    from app.api.v1.endpoints import portal
    PORTAL_AVAILABLE = True
    logger.info("Portal endpoints loaded")
except Exception as e:
    PORTAL_AVAILABLE = False
    logger.warning(f"Portal endpoints not available: {e}")

try:
    from app.api.v1.endpoints import ml
    ML_AVAILABLE = True
    logger.info("ML endpoints loaded")
except Exception as e:
    ML_AVAILABLE = False
    logger.warning(f"ML endpoints not available: {e}")

try:
    from app.api.v1.endpoints import edge
    EDGE_AVAILABLE = True
    logger.info("Edge endpoints loaded")
except Exception as e:
    EDGE_AVAILABLE = False
    logger.warning(f"Edge endpoints not available: {e}")

try:
    from app.api.v1.endpoints import safety
    SAFETY_AVAILABLE = True
    logger.info("Safety endpoints loaded")
except Exception as e:
    SAFETY_AVAILABLE = False
    logger.warning(f"Safety endpoints not available: {e}")

try:
    from app.api.v1.endpoints import voice
    VOICE_AVAILABLE = True
    logger.info("Voice endpoints loaded")
except Exception as e:
    VOICE_AVAILABLE = False
    logger.warning(f"Voice endpoints not available: {e}")

try:
    from app.api.v1.endpoints import iot
    IOT_AVAILABLE = True
    logger.info("IoT endpoints loaded")
except Exception as e:
    IOT_AVAILABLE = False
    logger.warning(f"IoT endpoints not available: {e}")

try:
    from app.api.v1.endpoints import integrations
    INTEGRATIONS_AVAILABLE = True
    logger.info("Integrations endpoints loaded")
except Exception as e:
    INTEGRATIONS_AVAILABLE = False
    logger.warning(f"Integrations endpoints not available: {e}")

try:
    from app.api.v1.endpoints import warehouse
    WAREHOUSE_AVAILABLE = True
    logger.info("Warehouse endpoints loaded")
except Exception as e:
    WAREHOUSE_AVAILABLE = False
    logger.warning(f"Warehouse endpoints not available: {e}")

try:
    from app.api.v1.endpoints import state
    STATE_AVAILABLE = True
    logger.info("State endpoints loaded")
except Exception as e:
    STATE_AVAILABLE = False
    logger.warning(f"State endpoints not available: {e}")

try:
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

# Chat endpoints (REQUIRED - used by frontend)
api_v1_router.include_router(chat.router, tags=["chat"])

# Agent endpoints (REQUIRED - used by frontend)
api_v1_router.include_router(agent_router, prefix="/agent", tags=["agent"])

# Include optional endpoints conditionally
if DOCUMENTS_AVAILABLE:
    api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])

if BIM_AVAILABLE:
    api_v1_router.include_router(bim.router, tags=["bim"])

if ECONOMICS_AVAILABLE:
    api_v1_router.include_router(economics.router, tags=["economics"])

if VDC_AVAILABLE:
    api_v1_router.include_router(vdc.router, tags=["vdc"])

if PORTAL_AVAILABLE:
    api_v1_router.include_router(portal.router, tags=["portal"])

if ML_AVAILABLE:
    api_v1_router.include_router(ml.router, tags=["ml"])

if EDGE_AVAILABLE:
    api_v1_router.include_router(edge.router, tags=["edge"])

if SAFETY_AVAILABLE:
    api_v1_router.include_router(safety.router, tags=["safety"])

if VOICE_AVAILABLE:
    api_v1_router.include_router(voice.router, tags=["voice"])

if IOT_AVAILABLE:
    api_v1_router.include_router(iot.router, tags=["iot"])

if INTEGRATIONS_AVAILABLE:
    api_v1_router.include_router(integrations.router, tags=["integrations"])

if WAREHOUSE_AVAILABLE:
    api_v1_router.include_router(warehouse.router, tags=["warehouse"])

if STATE_AVAILABLE:
    api_v1_router.include_router(state.router, tags=["state"])
