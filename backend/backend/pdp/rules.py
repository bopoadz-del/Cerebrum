"""
PDP compatibility stub: rules.py

This is a lightweight, import-safe placeholder. Real PDP logic lives in the main app
(`app/core/security`, `app/core/rate_limit`, etc.) and can be wired later.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class PDPDecision:
    allowed: bool = True
    reason: str = "stub-allow"
    metadata: Dict[str, Any] = None

def evaluate(*args: Any, **kwargs: Any) -> PDPDecision:
    return PDPDecision(allowed=True, reason="stub-allow", metadata={})
