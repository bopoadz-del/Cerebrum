"""
Forwarder for CI runs where CWD=backend.

Allows `import backend.api.users` to resolve by forwarding to the top-level
compatibility package at `api.users`.
"""
from __future__ import annotations

from api.users import *  # noqa: F401,F403
