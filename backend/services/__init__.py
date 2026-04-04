"""
Compatibility service wrappers.

Each module provides `available()` and `run()` to avoid import-time failures.
"""

# Google Drive integration removed - import removed to prevent circular imports
# from . import google_drive  # noqa: F401

__all__ = []
