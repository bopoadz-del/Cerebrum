"""
Forwarder for CI runs where CWD=backend.

Allows `import backend.api.upload` to resolve by forwarding to the top-level
compatibility package at `api.upload`.
"""
from __future__ import annotations

from api.upload import *  # noqa: F401,F403
