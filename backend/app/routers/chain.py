"""
Chain router - root-level workflow chaining endpoints.
"""

from fastapi import APIRouter

router = APIRouter(tags=["chain"])


@router.get("/chain/status")
async def chain_status():
    """Chain service status."""
    return {"status": "ok", "service": "chain", "version": "v1"}
