"""Compatibility validation shim."""
from __future__ import annotations
from typing import Any, Dict

def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "payload_keys": sorted(list(payload.keys()))}
