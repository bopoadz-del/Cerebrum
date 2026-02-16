"""
Legacy DB shim: backend.backend.db

Provides minimal symbols commonly imported by older code/tests.
Delegates to the current database session manager when available.
"""
from __future__ import annotations

from typing import Any, Generator

try:
    from app.db.session import get_db_session as _get_db_session
except Exception:  # pragma: no cover
    _get_db_session = None

def get_db() -> Generator[Any, None, None]:
    """Yield a DB session if available; otherwise yield None."""
    if _get_db_session is None:
        yield None
        return
    yield from _get_db_session()
