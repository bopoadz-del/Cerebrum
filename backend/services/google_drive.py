"""
Service wrapper: google_drive

Import-safe stub that keeps external imports stable.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def available() -> bool:
    return True


async def run(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return {"ok": True, "service": "google_drive", "args": list(args), "kwargs": kwargs}


def list_files(folder_id: Optional[str] = None) -> Dict[str, Any]:
    return {"ok": True, "files": []}


def search_files(query: str) -> Dict[str, Any]:
    return {"ok": True, "query": query, "files": []}
