"""
Compatibility service wrappers.

Each module provides `available()` and `run()` to avoid import-time failures.
"""

from . import google_drive  # noqa: F401

__all__ = ["google_drive"]
