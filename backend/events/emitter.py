"""Event emitter stub."""
from __future__ import annotations
from typing import Any, Dict, List, Callable

_subscribers: List[Callable[[Dict[str, Any]], None]] = []

def subscribe(fn: Callable[[Dict[str, Any]], None]) -> None:
    _subscribers.append(fn)

def emit(event: Dict[str, Any]) -> None:
    for fn in list(_subscribers):
        try:
            fn(event)
        except Exception:
            pass
