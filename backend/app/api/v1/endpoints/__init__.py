"""API v1 endpoints package."""

# Import routers for easy access
from . import auth, admin, documents, safety
from .stub_users import router as users
from .stub_projects import router as projects
from .stub_registry import router as registry
from .stub_coding import router as coding
from .stub_quality import router as quality

__all__ = [
    "auth",
    "admin", 
    "documents",
    "safety",
    "users",
    "projects",
    "registry",
    "coding",
    "quality",
]
