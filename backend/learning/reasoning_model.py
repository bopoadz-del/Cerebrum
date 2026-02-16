"""Reasoning model stub."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class ReasoningResult:
    answer: str
    confidence: float = 0.0
    traces: Dict[str, Any] = None

async def infer(prompt: str, **kwargs: Any) -> ReasoningResult:
    return ReasoningResult(answer="stub", confidence=0.0, traces={"prompt": prompt})
