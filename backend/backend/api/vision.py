"""
Forwarder for CI runs where CWD=backend.

Allows `import backend.api.vision` to resolve by forwarding to the top-level
compatibility package at `api.vision`.
"""
from __future__ import annotations

from api.vision import *  # noqa: F401,F403
