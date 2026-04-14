"""
Health router - root-level health probes.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def root_health():
    """Root-level health check for Docker/Railway/Render."""
    from app.api.health import liveness
    return await liveness()


@router.get("/healthz")
async def root_healthz():
    """Root-level Kubernetes liveness probe."""
    from app.api.health import liveness
    return await liveness()


@router.get("/readyz")
async def root_readyz():
    """Root-level Kubernetes readiness probe."""
    from app.api.health import readiness
    return await readiness()
