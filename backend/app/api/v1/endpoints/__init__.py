"""API v1 endpoints package."""

# Import routers for easy access
from . import auth, admin, documents, google_drive, safety

__all__ = [
    "auth",
    "admin", 
    "documents",
    "google_drive",
    "safety",
]
