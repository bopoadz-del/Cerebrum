"""
Upload router - root-level file upload endpoints.
"""

from fastapi import APIRouter

router = APIRouter(tags=["upload"])


@router.get("/upload/status")
async def upload_status():
    """Upload service status."""
    return {"status": "ok", "service": "upload", "version": "v1"}
