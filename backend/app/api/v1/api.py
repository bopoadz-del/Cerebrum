"""
API Version 1 Router
Defines the v1 API routes and versioning configuration.
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Import endpoints with error handling for missing dependencies
from app.api.health import router as health_router

# Core endpoints - REQUIRED for frontend
# Import one by one with graceful fallback

try:
    from app.api.v1.endpoints import auth
    logger.info("Auth endpoints loaded")
    AUTH_AVAILABLE = True
except Exception as e:
    logger.error(f"Auth import failed: {e}")
    AUTH_AVAILABLE = False
    auth = None

try:
    from app.api.v1.endpoints import admin
    logger.info("Admin endpoints loaded")
    ADMIN_AVAILABLE = True
except Exception as e:
    logger.error(f"Admin import failed: {e}")
    ADMIN_AVAILABLE = False
    admin = None

try:
    from app.api.v1.endpoints import dejavu
    logger.info("Dejavu endpoints loaded")
    DEJAVU_AVAILABLE = True
except Exception as e:
    logger.error(f"Dejavu import failed: {e}")
    DEJAVU_AVAILABLE = False
    dejavu = None

try:
    from app.api.v1.endpoints import formulas
    logger.info("Formulas endpoints loaded")
    FORMULAS_AVAILABLE = True
except Exception as e:
    logger.error(f"Formulas import failed: {e}")
    FORMULAS_AVAILABLE = False
    formulas = None

try:
    from app.api.v1.endpoints import sessions
    logger.info("Sessions endpoints loaded")
    SESSIONS_AVAILABLE = True
except Exception as e:
    logger.error(f"Sessions import failed: {e}")
    SESSIONS_AVAILABLE = False
    sessions = None

try:
    from app.api.v1.endpoints import connectors
    logger.info("Connectors endpoints loaded")
    CONNECTORS_AVAILABLE = True
except Exception as e:
    logger.error(f"Connectors import failed: {e}")
    CONNECTORS_AVAILABLE = False
    connectors = None

try:
    from app.api.v1.endpoints import chat
    logger.info("Chat endpoints loaded")
    CHAT_AVAILABLE = True
except Exception as e:
    logger.error(f"Chat import failed: {e}")
    CHAT_AVAILABLE = False
    chat = None

# USERS - Required for frontend
try:
    from app.api.v1.endpoints import stub_users as users
    logger.info("Users endpoints loaded")
    USERS_AVAILABLE = True
except Exception as e:
    logger.error(f"Users import failed: {e}")
    USERS_AVAILABLE = False
    users = None

# PROJECTS - Required for frontend
try:
    from app.api.v1.endpoints import stub_projects as projects
    logger.info("Projects endpoints loaded")
    PROJECTS_AVAILABLE = True
except Exception as e:
    logger.error(f"Projects import failed: {e}")
    PROJECTS_AVAILABLE = False
    projects = None

# REGISTRY
try:
    from app.api.v1.endpoints import stub_registry as registry
    logger.info("Registry endpoints loaded")
    REGISTRY_AVAILABLE = True
except Exception as e:
    logger.error(f"Registry import failed: {e}")
    REGISTRY_AVAILABLE = False
    registry = None

# QUALITY
try:
    from app.api.v1.endpoints import stub_quality as quality
    logger.info("Quality endpoints loaded")
    QUALITY_AVAILABLE = True
except Exception as e:
    logger.error(f"Quality import failed: {e}")
    QUALITY_AVAILABLE = False
    quality = None

# CODING
try:
    from app.api.v1.endpoints import stub_coding as coding
    logger.info("Coding endpoints loaded")
    CODING_AVAILABLE = True
except Exception as e:
    logger.error(f"Coding import failed: {e}")
    CODING_AVAILABLE = False
    coding = None

try:
    from app.agent.enhanced_endpoints import router as agent_router
    logger.info("Agent endpoints loaded")
    AGENT_AVAILABLE = True
except Exception as e:
    logger.error(f"Agent import failed: {e}")
    AGENT_AVAILABLE = False
    agent_router = None

try:
    from app.agent.web_search_endpoints import router as web_search_router
    logger.info("Web search endpoints loaded")
    WEB_SEARCH_AVAILABLE = True
except Exception as e:
    logger.warning(f"Web search endpoints not available: {e}")
    WEB_SEARCH_AVAILABLE = False
    web_search_router = None

# Try to import optional endpoints
try:
    from app.api.v1.endpoints import documents
    DOCUMENTS_AVAILABLE = True
    logger.info("Documents endpoints loaded")
except Exception as e:
    DOCUMENTS_AVAILABLE = False
    logger.warning(f"Documents endpoints not available: {e}")

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
    from app.api.v1.endpoints import construction
    CONSTRUCTION_AVAILABLE = True
    logger.info("Construction endpoints loaded")
except Exception as e:
    CONSTRUCTION_AVAILABLE = False
    logger.warning(f"Construction endpoints not available: {e}")

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

try:
    from app.recommendations.endpoints import router as recommendations_router
    RECOMMENDATIONS_AVAILABLE = True
    logger.info("Recommendations endpoints loaded")
except Exception as e:
    RECOMMENDATIONS_AVAILABLE = False
    logger.warning(f"Recommendations endpoints not available: {e}")

try:
    from app.executor.endpoints import router as executor_router
    EXECUTOR_AVAILABLE = True
    logger.info("Formula executor endpoints loaded")
except Exception as e:
    EXECUTOR_AVAILABLE = False
    logger.warning(f"Formula executor endpoints not available: {e}")


# Create main router - MUST BE NAMED api_v1_router for main.py
api_v1_router = APIRouter()

# Include core endpoints conditionally
api_v1_router.include_router(health_router, tags=["health"])

if AUTH_AVAILABLE and auth:
    api_v1_router.include_router(auth.router, tags=["authentication"])

if ADMIN_AVAILABLE and admin:
    api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])

if DEJAVU_AVAILABLE and dejavu:
    api_v1_router.include_router(dejavu.router, prefix="/dejavu", tags=["dejavu"])

if FORMULAS_AVAILABLE and formulas:
    api_v1_router.include_router(formulas.router, prefix="/formulas", tags=["formulas"])

if SESSIONS_AVAILABLE and sessions:
    api_v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

if CONNECTORS_AVAILABLE and connectors:
    api_v1_router.include_router(connectors.router, tags=["connectors"])

if CHAT_AVAILABLE and chat:
    api_v1_router.include_router(chat.router, tags=["chat"])

# USERS - Required for frontend
if USERS_AVAILABLE and users:
    api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
    logger.info("Users router included successfully")

# PROJECTS - Required for frontend
if PROJECTS_AVAILABLE and projects:
    api_v1_router.include_router(projects.router, prefix="/projects", tags=["projects"])
    logger.info("Projects router included successfully")

if AGENT_AVAILABLE and agent_router:
    api_v1_router.include_router(agent_router)
    logger.info("Agent router included successfully")

if WEB_SEARCH_AVAILABLE and web_search_router:
    api_v1_router.include_router(web_search_router)
    logger.info("Web search router included successfully")

# ORCHESTRATOR - Smart Orchestrator (39 actions)
try:
    from app.orchestrator.endpoints import router as orchestrator_router
    ORCHESTRATOR_AVAILABLE = True
    logger.info("Orchestrator endpoints loaded")
except Exception as e:
    ORCHESTRATOR_AVAILABLE = False
    logger.warning(f"Orchestrator endpoints not available: {e}")

if ORCHESTRATOR_AVAILABLE and orchestrator_router:
    api_v1_router.include_router(orchestrator_router, prefix="/orchestrator", tags=["orchestrator"])
    logger.info("Orchestrator router included successfully")

# REASONING - Heavy Reasoning Engine (SymPy-based)
try:
    from app.reasoning.endpoints import router as reasoning_router
    REASONING_AVAILABLE = True
    logger.info("Reasoning endpoints loaded")
except Exception as e:
    REASONING_AVAILABLE = False
    logger.warning(f"Reasoning endpoints not available: {e}")

if REASONING_AVAILABLE and reasoning_router:
    api_v1_router.include_router(reasoning_router, prefix="/reasoning", tags=["reasoning"])
    logger.info("Reasoning router included successfully")

# Include optional endpoints conditionally
if DOCUMENTS_AVAILABLE:
    api_v1_router.include_router(documents.router)

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
    api_v1_router.include_router(voice.router, prefix="/voice", tags=["voice"])

if IOT_AVAILABLE:
    api_v1_router.include_router(iot.router, tags=["iot"])

if INTEGRATIONS_AVAILABLE:
    api_v1_router.include_router(integrations.router, tags=["integrations"])

if WAREHOUSE_AVAILABLE:
    api_v1_router.include_router(warehouse.router, tags=["warehouse"])

if STATE_AVAILABLE:
    api_v1_router.include_router(state.router, tags=["state"])

if CONSTRUCTION_AVAILABLE:
    api_v1_router.include_router(construction.router, tags=["construction"])

if RECOMMENDATIONS_AVAILABLE:
    api_v1_router.include_router(recommendations_router, tags=["recommendations"])

if REGISTRY_AVAILABLE and registry:
    api_v1_router.include_router(registry.router, prefix="/registry", tags=["registry"])
    logger.info("Registry router included successfully")

if QUALITY_AVAILABLE and quality:
    api_v1_router.include_router(quality.router, prefix="/quality", tags=["quality"])
    logger.info("Quality router included successfully")

if CODING_AVAILABLE and coding:
    api_v1_router.include_router(coding.router, prefix="/coding", tags=["coding"])
    logger.info("Coding router included successfully")

if EXECUTOR_AVAILABLE:
    api_v1_router.include_router(executor_router, tags=["executor"])
    logger.info("Formula executor router included successfully")

# Log all registered routes
logger.info(f"All registered routes: {[r.path for r in api_v1_router.routes]}")
