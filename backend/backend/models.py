"""
Legacy models shim: backend.backend.models

External tests may import ORM models from this path. The real SQLAlchemy models live
under `app/models`.
"""
from __future__ import annotations

try:
    from app.models import *  # noqa: F401,F403
except Exception:  # pragma: no cover
    class BaseModel:
        """Placeholder base model."""
        pass
