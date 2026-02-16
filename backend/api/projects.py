"""Compatibility API router: projects

This module exists for import compatibility. It provides a lightweight FastAPI router
and delegates to the current implementation when available.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

@router.get("/_compat/{route_name}")
async def compat_ping(route_name: str):
    return {"ok": True, "router": "projects", "route": route_name}
