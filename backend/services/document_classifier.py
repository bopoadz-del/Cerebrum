"""
Service wrapper: document_classifier

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
    return {"ok": True, "service": "document_classifier", "args": list(args), "kwargs": kwargs}
