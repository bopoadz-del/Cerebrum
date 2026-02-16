"""Google Drive connector stub (compat)."""
from __future__ import annotations
from typing import Any, Dict, List

async def list_files(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    return []

async def download_file(*args: Any, **kwargs: Any) -> bytes:
    return b""
