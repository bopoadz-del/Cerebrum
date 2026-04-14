"""
Execute router - root-level block execution endpoints.
"""

from fastapi import APIRouter

router = APIRouter(tags=["execute"])


@router.get("/execute/status")
async def execute_status():
    """Execution service status."""
    return {"status": "ok", "service": "execute", "version": "v1"}
