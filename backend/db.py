"""Compatibility DB shim: backend.db"""
from __future__ import annotations
from typing import Any, Generator

try:
    from app.db.session import get_db_session as _get_db_session
except Exception:  # pragma: no cover
    _get_db_session = None

def get_db() -> Generator[Any, None, None]:
    if _get_db_session is None:
        yield None
        return
    yield from _get_db_session()
