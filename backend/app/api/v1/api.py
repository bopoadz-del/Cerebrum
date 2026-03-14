"""
API Version 1 Router
Defines the v1 API routes and versioning configuration.
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Import core endpoints
from app.api.v1.endpoints import auth, admin, dejavu, formulas, sessions, connectors
from app.api.health import router as health_router

# Import construction/endustry endpoints
from app.api.v1.endpoints import bim, economics, vdc, edge, enterprise, portal
from app.api.v1.endpoints import integrations, warehouse, ml

# Try to import optional endpoints
try:
    from app.api.v1.endpoints import documents
    DOCUMENTS_AVAILABLE = True
    logger.info("Documents endpoints loaded")
except Exception as e:
    DOCUMENTS_AVAILABLE = False
    logger.warning(f"Documents endpoints not available: {e}")

try:
    from app.api.v1.endpoints import iot
    IOT_AVAILABLE = True
    logger.info("IoT endpoints loaded")
except Exception as e:
    IOT_AVAILABLE = False
    logger.warning(f"IoT endpoints not available: {e}")

try:
    from app.api.v1.endpoints import safety
    SAFETY_AVAILABLE = True
    logger.info("Safety endpoints loaded")
except Exception as e:
    SAFETY_AVAILABLE = False
    logger.warning(f"Safety endpoints not available: {e}")

# Import or create stub endpoints for missing routers
try:
    from app.api.v1.endpoints import users
    logger.info("Users endpoints loaded")
except Exception as e:
    logger.warning(f"Users endpoints not available, using stub: {e}")
    from app.api.v1.endpoints.stub_users import router as users

try:
    from app.api.v1.endpoints import projects
    logger.info("Projects endpoints loaded")
except Exception as e:
    logger.warning(f"Projects endpoints not available, using stub: {e}")
    from app.api.v1.endpoints.stub_projects import router as projects

try:
    from app.api.v1.endpoints import registry
    logger.info("Registry endpoints loaded")
except Exception as e:
    logger.warning(f"Registry endpoints not available, using stub: {e}")
    from app.api.v1.endpoints.stub_registry import router as registry

try:
    from app.api.v1.endpoints import coding
    logger.info("Coding endpoints loaded")
except Exception as e:
    logger.warning(f"Coding endpoints not available, using stub: {e}")
    from app.api.v1.endpoints.stub_coding import router as coding

try:
    from app.api.v1.endpoints import quality
    logger.info("Quality endpoints loaded")
except Exception as e:
    logger.warning(f"Quality endpoints not available, using stub: {e}")
    from app.api.v1.endpoints.stub_quality import router as quality


# Create main router - MUST BE NAMED api_v1_router for main.py
api_v1_router = APIRouter()

# Include core endpoints
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth.router, tags=["authentication"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_v1_router.include_router(dejavu.router, prefix="/dejavu", tags=["dejavu"])
api_v1_router.include_router(formulas.router, prefix="/formulas", tags=["formulas"])
api_v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_v1_router.include_router(connectors.router, tags=["connectors"])

# Include construction/endustry endpoints
api_v1_router.include_router(bim.router, prefix="/bim", tags=["bim"])
api_v1_router.include_router(economics.router, prefix="/economics", tags=["economics"])
api_v1_router.include_router(vdc.router, prefix="/vdc", tags=["vdc"])
api_v1_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_v1_router.include_router(warehouse.router, prefix="/warehouse", tags=["warehouse"])
api_v1_router.include_router(ml.router, prefix="/ml", tags=["ml"])
api_v1_router.include_router(edge.router, prefix="/edge", tags=["edge"])
api_v1_router.include_router(enterprise.router, prefix="/enterprise", tags=["enterprise"])
api_v1_router.include_router(portal.router, prefix="/portal", tags=["portal"])
api_v1_router.include_router(registry.router, prefix="/registry", tags=["registry"])
api_v1_router.include_router(coding.router, prefix="/coding", tags=["coding"])
api_v1_router.include_router(quality.router, prefix="/quality", tags=["quality"])

# Include optional endpoints conditionally
if DOCUMENTS_AVAILABLE:
    api_v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])

if IOT_AVAILABLE:
    api_v1_router.include_router(iot.router, prefix="/iot", tags=["iot"])

if SAFETY_AVAILABLE:
    api_v1_router.include_router(safety.router, prefix="/safety", tags=["safety"])
