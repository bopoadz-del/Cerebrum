"""
Forwarder for CI runs where CWD=backend.

Allows `import backend.api.openai_test` to resolve by forwarding to the top-level
compatibility package at `api.openai_test`.
"""
from __future__ import annotations

from api.openai_test import *  # noqa: F401,F403
