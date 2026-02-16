"""
Service wrapper: google_drive

Import-safe stub that keeps external imports stable. If a modern implementation
exists under `app.services` or elsewhere, this module should delegate to it.
"""
from __future__ import annotations

from typing import Any, Dict

class ServiceError(RuntimeError):
    pass

def available() -> bool:
    return True

async def run(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return {"ok": True, "service": "google_drive", "args": list(args), "kwargs": kwargs}
