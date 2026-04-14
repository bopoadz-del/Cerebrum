"""
Chat router - root-level chat endpoints.
Proxies to the v1 chat completions API.
"""

from fastapi import APIRouter

router = APIRouter(tags=["chat"])


@router.get("/chat/status")
async def chat_status():
    """Chat service status."""
    return {"status": "ok", "service": "chat", "version": "v1"}
