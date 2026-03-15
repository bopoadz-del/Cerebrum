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

# Import construction/industry endpoints (these have prefixes already)
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

# Import or create stub endpoints for missing routers (no prefix in stubs)
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

# Import agent endpoints
try:
    from app.agent.endpoints import router as agent_router
    AGENT_AVAILABLE = True
    logger.info("Agent endpoints loaded")
except Exception as e:
    AGENT_AVAILABLE = False
    logger.warning(f"Agent endpoints not available: {e}")

# Import enhanced agent endpoints
try:
    from app.agent.enhanced_endpoints import router as enhanced_agent_router
    ENHANCED_AGENT_AVAILABLE = True
    logger.info("Enhanced agent endpoints loaded")
except Exception as e:
    ENHANCED_AGENT_AVAILABLE = False
    logger.warning(f"Enhanced agent endpoints not available: {e}")


# Create main router - MUST BE NAMED api_v1_router for main.py
api_v1_router = APIRouter()

# Include core endpoints (auth, admin, dejavu, formulas, sessions, connectors already have prefixes)
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth.router)  # prefix="/auth" already in router
api_v1_router.include_router(admin.router)  # prefix="/admin" already in router
api_v1_router.include_router(dejavu.router)  # prefix="/dejavu" already in router
api_v1_router.include_router(formulas.router)  # prefix="/formulas" already in router
api_v1_router.include_router(sessions.router)  # prefix="/sessions" already in router
api_v1_router.include_router(connectors.router)  # prefix="/connectors" already in router

# Include stubs (need prefix added)
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_v1_router.include_router(registry.router, prefix="/registry", tags=["registry"])
api_v1_router.include_router(coding.router, prefix="/coding", tags=["coding"])
api_v1_router.include_router(quality.router, prefix="/quality", tags=["quality"])

# Include construction/industry endpoints (already have prefixes)
api_v1_router.include_router(bim.router)  # prefix="/bim" already in router
api_v1_router.include_router(economics.router)  # prefix="/economics" already in router
api_v1_router.include_router(vdc.router)  # prefix="/vdc" already in router
api_v1_router.include_router(integrations.router)  # prefix="/integrations" already in router
api_v1_router.include_router(warehouse.router, prefix="/warehouse", tags=["warehouse"])  # no prefix in router
api_v1_router.include_router(ml.router)  # prefix="/ml" already in router
api_v1_router.include_router(edge.router)  # prefix="/edge" already in router
api_v1_router.include_router(enterprise.router)  # prefix="/enterprise" already in router
api_v1_router.include_router(portal.router)  # prefix="/portal" already in router

# Include optional endpoints conditionally
if DOCUMENTS_AVAILABLE:
    api_v1_router.include_router(documents.router)  # prefix="/documents" already in router

if IOT_AVAILABLE:
    api_v1_router.include_router(iot.router, prefix="/iot", tags=["iot"])

if SAFETY_AVAILABLE:
    api_v1_router.include_router(safety.router)  # prefix="/safety" already in router

# Include agent endpoints
if AGENT_AVAILABLE:
    api_v1_router.include_router(agent_router, prefix="/agent", tags=["agent"])

# Include enhanced agent endpoints
if ENHANCED_AGENT_AVAILABLE:
    api_v1_router.include_router(enhanced_agent_router, prefix="/agent/v2", tags=["agent-enhanced"])
