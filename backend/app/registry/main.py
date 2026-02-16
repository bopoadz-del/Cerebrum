"""
Self-Coding Registry System - Main Router Aggregation

Aggregates all routers from the self-coding system for integration
with the main FastAPI application.
"""

from fastapi import APIRouter

# Import all endpoint routers
from app.registry.endpoints import router as registry_router
from app.coding.endpoints import router as coding_router
from app.validation.endpoints import router as validation_router
from app.hotswap.endpoints import router as hotswap_router
from app.healing.endpoints import router as healing_router
from app.prompts.endpoints import router as prompts_router


def create_self_coding_router() -> APIRouter:
    """
    Create the main self-coding router with all sub-routers.
    
    Returns:
        APIRouter with all self-coding endpoints
    """
    router = APIRouter(prefix="/api/v1/self-coding", tags=["Self-Coding System"])
    
    # Include all sub-routers
    router.include_router(registry_router)
    router.include_router(coding_router)
    router.include_router(validation_router)
    router.include_router(hotswap_router)
    router.include_router(healing_router)
    router.include_router(prompts_router)
    
    return router


# Create the main router instance
self_coding_router = create_self_coding_router()


# Health check endpoint for the self-coding system
@self_coding_router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check for the self-coding system.
    
    Returns status of all subsystems.
    """
    return {
        "status": "healthy",
        "system": "self-coding",
        "version": "1.0.0",
        "subsystems": {
            "registry": "healthy",
            "coding": "healthy",
            "validation": "healthy",
            "hotswap": "healthy",
            "healing": "healthy",
            "prompts": "healthy",
        },
    }


# System overview endpoint
@self_coding_router.get("/overview", tags=["System"])
async def system_overview():
    """
    Get an overview of the self-coding system.
    
    Returns statistics and capabilities of the system.
    """
    return {
        "system": "Cerebrum AI Self-Coding Platform",
        "version": "1.0.0",
        "description": "Meta-cognition system that allows the platform to modify itself",
        "capabilities": [
            {
                "name": "Capability Registry",
                "description": "Manage AI-generated capabilities with lifecycle management",
                "endpoints": [
                    "POST /registry/capabilities",
                    "GET /registry/capabilities",
                    "PATCH /registry/capabilities/{id}/validate",
                    "PATCH /registry/capabilities/{id}/deprecate",
                ],
            },
            {
                "name": "Code Generation",
                "description": "Generate code from natural language using AI",
                "endpoints": [
                    "POST /coding/generate",
                    "POST /coding/preview",
                    "GET /coding/templates",
                ],
            },
            {
                "name": "Validation Pipeline",
                "description": "Validate code through multiple security checks",
                "endpoints": [
                    "POST /validation/{capability_id}/run",
                    "GET /validation/{capability_id}/status",
                    "GET /validation/{capability_id}/report",
                ],
            },
            {
                "name": "Hot Swap System",
                "description": "Deploy capabilities at runtime without restart",
                "endpoints": [
                    "POST /hotswap/{capability_id}/deploy",
                    "POST /hotswap/{capability_id}/rollback",
                    "GET /hotswap/active",
                ],
            },
            {
                "name": "Self-Healing",
                "description": "Auto-detect and fix errors",
                "endpoints": [
                    "GET /healing/incidents",
                    "POST /healing/incidents/{id}/analyze",
                    "GET /healing/patches",
                ],
            },
            {
                "name": "Prompt Registry",
                "description": "Versioned prompts with A/B testing",
                "endpoints": [
                    "GET /prompts",
                    "POST /prompts",
                    "PATCH /prompts/{id}/activate",
                ],
            },
        ],
        "workflow": {
            "title": "5-Minute Feature Deployment",
            "steps": [
                "1. User: 'Add a drywall quantity calculator'",
                "2. AI generates code via POST /coding/generate",
                "3. Code validated via POST /validation/{id}/run",
                "4. Human reviews and approves",
                "5. Deployed via POST /hotswap/{id}/deploy",
                "6. Available in UI within 5 minutes!",
            ],
        },
    }


# Export all routers for individual use
__all__ = [
    "self_coding_router",
    "create_self_coding_router",
    "registry_router",
    "coding_router",
    "validation_router",
    "hotswap_router",
    "healing_router",
    "prompts_router",
]
