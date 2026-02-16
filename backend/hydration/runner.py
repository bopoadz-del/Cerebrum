"""Hydration runner stub."""
from __future__ import annotations
from typing import Any, Dict

async def run_now(workspace_id: str, dry_run: bool = False, **kwargs: Any) -> Dict[str, Any]:
    return {"ok": True, "workspace_id": workspace_id, "dry_run": dry_run, "detail": "stub"}
