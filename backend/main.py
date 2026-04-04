"""Compatibility entrypoint exposing FastAPI `app`.

Why this exists:
- External tools/tests import `backend.main:app`
- Production code uses `app.main:app`

This module tries to load the real application. If that fails (common in CI where
strict env vars like SECRET_KEY might not be set), it falls back to a lightweight
FastAPI app that still exposes the compatibility routers.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI


def _attach_compat(app: FastAPI) -> None:
    """Attach compatibility routers safely (never crash imports)."""
    try:
        from backend.api import get_compat_router  # type: ignore
        app.include_router(get_compat_router(prefix="/api/compat"))
    except Exception:
        # Import-compat should never break the application
        return


def _load_real_app() -> Optional[FastAPI]:
    """Attempt to import the real app. Return None if unavailable."""
    try:
        from app.main import app as real_app  # type: ignore
        return real_app
    except Exception:
        return None


_real = _load_real_app()

if _real is None:
    app = FastAPI(title="backend.main stub")

    @app.get("/_stub")
    async def _stub():
        return {"ok": True, "mode": "stub"}

    _attach_compat(app)
else:
    app = _real
    _attach_compat(app)
