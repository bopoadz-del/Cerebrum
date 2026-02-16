"""
Forwarder for CI runs where CWD=backend.

Allows `import backend.api.projects` to resolve by forwarding to the top-level
compatibility package at `api.projects`.
"""
from __future__ import annotations

from api.projects import *  # noqa: F401,F403
