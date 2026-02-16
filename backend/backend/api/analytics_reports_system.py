"""
Forwarder for CI runs where CWD=backend.

Allows `import backend.api.analytics_reports_system` to resolve by forwarding to the top-level
compatibility package at `api.analytics_reports_system`.
"""
from __future__ import annotations

from api.analytics_reports_system import *  # noqa: F401,F403
