"""
Forwarder for CI runs where CWD=backend.

Allows `import backend.api.analytics` to resolve by forwarding to the top-level
compatibility package at `api.analytics`.
"""
from __future__ import annotations

from api.analytics import *  # noqa: F401,F403
