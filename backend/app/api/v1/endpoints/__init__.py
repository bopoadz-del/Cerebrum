"""API v1 endpoints package."""

# Import routers for easy access
from . import auth, admin, documents, safety

__all__ = [
    "auth",
    "admin", 
    "documents",
    "safety",
]
