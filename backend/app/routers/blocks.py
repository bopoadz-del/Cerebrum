"""
Blocks router - list registered domain and infrastructure blocks.
"""

from fastapi import APIRouter

from app.core.block_registry import BLOCK_REGISTRY

router = APIRouter(tags=["blocks"])


@router.get("/blocks")
async def list_blocks():
    """List all registered domain and infrastructure blocks."""
    return {
        "status": "success",
        "blocks": BLOCK_REGISTRY.list_blocks(),
    }
