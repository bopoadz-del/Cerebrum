"""
Connectors Module

Provides factory-based access to external service connectors with stub support.

Quick Start:
    from app.connectors import get_connector
    
    procore = get_connector("procore")
    projects = procore.get_projects()

Environment Variables:
    USE_STUB_CONNECTORS=true   # Enable all stubs
    USE_STUB_PROCORE=true      # Enable stub for specific service
    USE_STUB_NOTIFICATIONS=true  # Enable notification stubs
    USE_STUB_ML=true           # Enable ML stubs
"""

from .factory import (
    get_connector,
    get_connector_status,
    list_connectors,
    register_connector,
    ConnectorFactoryRegistry,
)

__all__ = [
    "get_connector",
    "get_connector_status",
    "list_connectors",
    "register_connector",
    "ConnectorFactoryRegistry",
]
