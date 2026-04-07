"""
Connectors Module

Provides factory-based access to external service connectors with stub support.

Quick Start:
    from app.connectors import get_connector
    
    procore = get_connector("procore")
    projects = procore.get_projects()
    
    local_drive = get_connector("local_drive")
    files = local_drive.list_files("documents")
    
    smartphone = get_connector("smartphone")
    photos = smartphone.list_photos()

Environment Variables:
    USE_STUB_CONNECTORS=true       # Enable all stubs
    USE_STUB_LOCAL_DRIVE=true      # Enable stub for local drive
    USE_STUB_SMARTPHONE=true       # Enable stub for smartphone
    LOCAL_DRIVE_ROOT=/path/to/folder   # Set local drive root path
    SMARTPHONE_MODE=syncthing      # Set smartphone connection mode (usb, mtp, syncthing, folder)
    SMARTPHONE_PATH=/path/to/sync      # Set smartphone sync folder path
"""

from .factory import (
    get_connector,
    get_connector_status,
    list_connectors,
    register_connector,
    ConnectorFactoryRegistry,
)
from .local_drive import LocalDriveConnector
from .smartphone import SmartphoneConnector

__all__ = [
    "get_connector",
    "get_connector_status",
    "list_connectors",
    "register_connector",
    "ConnectorFactoryRegistry",
    "LocalDriveConnector",
    "SmartphoneConnector",
]
