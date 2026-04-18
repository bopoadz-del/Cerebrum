"""
Permission System for Cerebrum 14-Layer Architecture

Defines granular permissions for each layer of the construction intelligence platform.
"""

from enum import Enum
from typing import List, Set, Optional
from dataclasses import dataclass


class PermissionScope(str, Enum):
    """Permission scopes for resource access."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class LayerPermission(str, Enum):
    """
    Granular permissions for Cerebrum's 14-layer architecture.
    
    Each layer has 6 permission types: create, read, update, delete, execute, admin
    """
    
    # Layer 1: Foundation - Core infrastructure
    FOUNDATION_CREATE = "foundation:create"
    FOUNDATION_READ = "foundation:read"
    FOUNDATION_UPDATE = "foundation:update"
    FOUNDATION_DELETE = "foundation:delete"
    FOUNDATION_EXECUTE = "foundation:execute"
    FOUNDATION_ADMIN = "foundation:admin"
    
    # Layer 2: Sensing - IoT sensors and data collection
    SENSING_CREATE = "sensing:create"
    SENSING_READ = "sensing:read"
    SENSING_UPDATE = "sensing:update"
    SENSING_DELETE = "sensing:delete"
    SENSING_EXECUTE = "sensing:execute"
    SENSING_ADMIN = "sensing:admin"
    
    # Layer 3: Connectivity - Network and protocols
    CONNECTIVITY_CREATE = "connectivity:create"
    CONNECTIVITY_READ = "connectivity:read"
    CONNECTIVITY_UPDATE = "connectivity:update"
    CONNECTIVITY_DELETE = "connectivity:delete"
    CONNECTIVITY_EXECUTE = "connectivity:execute"
    CONNECTIVITY_ADMIN = "connectivity:admin"
    
    # Layer 4: Edge - Edge computing and preprocessing
    EDGE_CREATE = "edge:create"
    EDGE_READ = "edge:read"
    EDGE_UPDATE = "edge:update"
    EDGE_DELETE = "edge:delete"
    EDGE_EXECUTE = "edge:execute"
    EDGE_ADMIN = "edge:admin"
    
    # Layer 5: Ingestion - Data ingestion pipelines
    INGESTION_CREATE = "ingestion:create"
    INGESTION_READ = "ingestion:read"
    INGESTION_UPDATE = "ingestion:update"
    INGESTION_DELETE = "ingestion:delete"
    INGESTION_EXECUTE = "ingestion:execute"
    INGESTION_ADMIN = "ingestion:admin"
    
    # Layer 6: Stream - Real-time data streaming
    STREAM_CREATE = "stream:create"
    STREAM_READ = "stream:read"
    STREAM_UPDATE = "stream:update"
    STREAM_DELETE = "stream:delete"
    STREAM_EXECUTE = "stream:execute"
    STREAM_ADMIN = "stream:admin"
    
    # Layer 7: Processing - Data processing and transformation
    PROCESSING_CREATE = "processing:create"
    PROCESSING_READ = "processing:read"
    PROCESSING_UPDATE = "processing:update"
    PROCESSING_DELETE = "processing:delete"
    PROCESSING_EXECUTE = "processing:execute"
    PROCESSING_ADMIN = "processing:admin"
    
    # Layer 8: Warehouse - Data storage and warehousing
    WAREHOUSE_CREATE = "warehouse:create"
    WAREHOUSE_READ = "warehouse:read"
    WAREHOUSE_UPDATE = "warehouse:update"
    WAREHOUSE_DELETE = "warehouse:delete"
    WAREHOUSE_EXECUTE = "warehouse:execute"
    WAREHOUSE_ADMIN = "warehouse:admin"
    
    # Layer 9: Intelligence - AI/ML model management
    INTELLIGENCE_CREATE = "intelligence:create"
    INTELLIGENCE_READ = "intelligence:read"
    INTELLIGENCE_UPDATE = "intelligence:update"
    INTELLIGENCE_DELETE = "intelligence:delete"
    INTELLIGENCE_EXECUTE = "intelligence:execute"
    INTELLIGENCE_ADMIN = "intelligence:admin"
    
    # Layer 10: Blocks - Modular function blocks
    BLOCKS_CREATE = "blocks:create"
    BLOCKS_READ = "blocks:read"
    BLOCKS_UPDATE = "blocks:update"
    BLOCKS_DELETE = "blocks:delete"
    BLOCKS_EXECUTE = "blocks:execute"
    BLOCKS_ADMIN = "blocks:admin"
    
    # Layer 11: Interface - User interfaces and APIs
    INTERFACE_CREATE = "interface:create"
    INTERFACE_READ = "interface:read"
    INTERFACE_UPDATE = "interface:update"
    INTERFACE_DELETE = "interface:delete"
    INTERFACE_EXECUTE = "interface:execute"
    INTERFACE_ADMIN = "interface:admin"
    
    # Layer 12: Intelligence Services - AI service orchestration
    INTELLIGENCE_SERVICES_CREATE = "intelligence_services:create"
    INTELLIGENCE_SERVICES_READ = "intelligence_services:read"
    INTELLIGENCE_SERVICES_UPDATE = "intelligence_services:update"
    INTELLIGENCE_SERVICES_DELETE = "intelligence_services:delete"
    INTELLIGENCE_SERVICES_EXECUTE = "intelligence_services:execute"
    INTELLIGENCE_SERVICES_ADMIN = "intelligence_services:admin"
    
    # Layer 13: Presentation - Visualization and reporting
    PRESENTATION_CREATE = "presentation:create"
    PRESENTATION_READ = "presentation:read"
    PRESENTATION_UPDATE = "presentation:update"
    PRESENTATION_DELETE = "presentation:delete"
    PRESENTATION_EXECUTE = "presentation:execute"
    PRESENTATION_ADMIN = "presentation:admin"
    
    # Layer 14: Application - End-user applications
    APPLICATION_CREATE = "application:create"
    APPLICATION_READ = "application:read"
    APPLICATION_UPDATE = "application:update"
    APPLICATION_DELETE = "application:delete"
    APPLICATION_EXECUTE = "application:execute"
    APPLICATION_ADMIN = "application:admin"
    
    # Cross-cutting permissions
    SYSTEM_ADMIN = "system:admin"
    USER_ADMIN = "user:admin"
    AUDIT_READ = "audit:read"
    AUDIT_ADMIN = "audit:admin"
    API_KEY_MANAGE = "api_key:manage"
    TENANT_ADMIN = "tenant:admin"


# Layer names for human-readable references
LAYER_NAMES = {
    "foundation": "Foundation (Infrastructure)",
    "sensing": "Sensing (IoT/Data Collection)",
    "connectivity": "Connectivity (Network)",
    "edge": "Edge (Edge Computing)",
    "ingestion": "Ingestion (Data Ingestion)",
    "stream": "Stream (Real-time Data)",
    "processing": "Processing (Data Processing)",
    "warehouse": "Warehouse (Data Storage)",
    "intelligence": "Intelligence (AI/ML Models)",
    "blocks": "Blocks (Modular Functions)",
    "interface": "Interface (UI/APIs)",
    "intelligence_services": "Intelligence Services (AI Orchestration)",
    "presentation": "Presentation (Visualization)",
    "application": "Application (End-user Apps)",
}


# Permission groups for easy role assignment
PERMISSION_GROUPS = {
    "viewer": [
        # Read-only access to all layers
        LayerPermission.FOUNDATION_READ,
        LayerPermission.SENSING_READ,
        LayerPermission.CONNECTIVITY_READ,
        LayerPermission.EDGE_READ,
        LayerPermission.INGESTION_READ,
        LayerPermission.STREAM_READ,
        LayerPermission.PROCESSING_READ,
        LayerPermission.WAREHOUSE_READ,
        LayerPermission.INTELLIGENCE_READ,
        LayerPermission.BLOCKS_READ,
        LayerPermission.INTERFACE_READ,
        LayerPermission.INTELLIGENCE_SERVICES_READ,
        LayerPermission.PRESENTATION_READ,
        LayerPermission.APPLICATION_READ,
        LayerPermission.AUDIT_READ,
    ],
    "engineer": [
        # Full operational access except admin
        LayerPermission.FOUNDATION_READ,
        LayerPermission.FOUNDATION_CREATE,
        LayerPermission.FOUNDATION_UPDATE,
        LayerPermission.FOUNDATION_DELETE,
        LayerPermission.FOUNDATION_EXECUTE,
        LayerPermission.SENSING_READ,
        LayerPermission.SENSING_CREATE,
        LayerPermission.SENSING_UPDATE,
        LayerPermission.SENSING_DELETE,
        LayerPermission.SENSING_EXECUTE,
        LayerPermission.CONNECTIVITY_READ,
        LayerPermission.CONNECTIVITY_CREATE,
        LayerPermission.CONNECTIVITY_UPDATE,
        LayerPermission.CONNECTIVITY_DELETE,
        LayerPermission.CONNECTIVITY_EXECUTE,
        LayerPermission.EDGE_READ,
        LayerPermission.EDGE_CREATE,
        LayerPermission.EDGE_UPDATE,
        LayerPermission.EDGE_DELETE,
        LayerPermission.EDGE_EXECUTE,
        LayerPermission.INGESTION_READ,
        LayerPermission.INGESTION_CREATE,
        LayerPermission.INGESTION_UPDATE,
        LayerPermission.INGESTION_DELETE,
        LayerPermission.INGESTION_EXECUTE,
        LayerPermission.STREAM_READ,
        LayerPermission.STREAM_CREATE,
        LayerPermission.STREAM_UPDATE,
        LayerPermission.STREAM_DELETE,
        LayerPermission.STREAM_EXECUTE,
        LayerPermission.PROCESSING_READ,
        LayerPermission.PROCESSING_CREATE,
        LayerPermission.PROCESSING_UPDATE,
        LayerPermission.PROCESSING_DELETE,
        LayerPermission.PROCESSING_EXECUTE,
        LayerPermission.WAREHOUSE_READ,
        LayerPermission.WAREHOUSE_CREATE,
        LayerPermission.WAREHOUSE_UPDATE,
        LayerPermission.WAREHOUSE_DELETE,
        LayerPermission.WAREHOUSE_EXECUTE,
        LayerPermission.INTELLIGENCE_READ,
        LayerPermission.INTELLIGENCE_CREATE,
        LayerPermission.INTELLIGENCE_UPDATE,
        LayerPermission.INTELLIGENCE_DELETE,
        LayerPermission.INTELLIGENCE_EXECUTE,
        LayerPermission.BLOCKS_READ,
        LayerPermission.BLOCKS_CREATE,
        LayerPermission.BLOCKS_UPDATE,
        LayerPermission.BLOCKS_DELETE,
        LayerPermission.BLOCKS_EXECUTE,
        LayerPermission.INTERFACE_READ,
        LayerPermission.INTERFACE_CREATE,
        LayerPermission.INTERFACE_UPDATE,
        LayerPermission.INTERFACE_DELETE,
        LayerPermission.INTERFACE_EXECUTE,
        LayerPermission.INTELLIGENCE_SERVICES_READ,
        LayerPermission.INTELLIGENCE_SERVICES_CREATE,
        LayerPermission.INTELLIGENCE_SERVICES_UPDATE,
        LayerPermission.INTELLIGENCE_SERVICES_DELETE,
        LayerPermission.INTELLIGENCE_SERVICES_EXECUTE,
        LayerPermission.PRESENTATION_READ,
        LayerPermission.PRESENTATION_CREATE,
        LayerPermission.PRESENTATION_UPDATE,
        LayerPermission.PRESENTATION_DELETE,
        LayerPermission.PRESENTATION_EXECUTE,
        LayerPermission.APPLICATION_READ,
        LayerPermission.APPLICATION_CREATE,
        LayerPermission.APPLICATION_UPDATE,
        LayerPermission.APPLICATION_DELETE,
        LayerPermission.APPLICATION_EXECUTE,
        LayerPermission.API_KEY_MANAGE,
    ],
    "admin": [
        # Full admin access including system administration
        *PERMISSION_GROUPS["engineer"],
        LayerPermission.FOUNDATION_ADMIN,
        LayerPermission.SENSING_ADMIN,
        LayerPermission.CONNECTIVITY_ADMIN,
        LayerPermission.EDGE_ADMIN,
        LayerPermission.INGESTION_ADMIN,
        LayerPermission.STREAM_ADMIN,
        LayerPermission.PROCESSING_ADMIN,
        LayerPermission.WAREHOUSE_ADMIN,
        LayerPermission.INTELLIGENCE_ADMIN,
        LayerPermission.BLOCKS_ADMIN,
        LayerPermission.INTERFACE_ADMIN,
        LayerPermission.INTELLIGENCE_SERVICES_ADMIN,
        LayerPermission.PRESENTATION_ADMIN,
        LayerPermission.APPLICATION_ADMIN,
        LayerPermission.SYSTEM_ADMIN,
        LayerPermission.USER_ADMIN,
        LayerPermission.AUDIT_ADMIN,
        LayerPermission.TENANT_ADMIN,
    ],
}


def get_layer_permissions(layer: str, scope: Optional[PermissionScope] = None) -> List[LayerPermission]:
    """
    Get permissions for a specific layer.
    
    Args:
        layer: Layer name (e.g., "foundation", "sensing")
        scope: Optional scope filter (e.g., PermissionScope.READ)
        
    Returns:
        List of LayerPermission enums for the layer
    """
    layer = layer.lower()
    permissions = []
    
    for perm in LayerPermission:
        if perm.value.startswith(f"{layer}:"):
            if scope is None or perm.value.endswith(f":{scope.value}"):
                permissions.append(perm)
    
    return permissions


def get_all_permissions() -> List[LayerPermission]:
    """Get all defined permissions."""
    return list(LayerPermission)


def validate_permission(permission: str) -> bool:
    """
    Validate if a permission string is valid.
    
    Args:
        permission: Permission string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        LayerPermission(permission)
        return True
    except ValueError:
        return False


def get_permission_description(permission: LayerPermission) -> str:
    """
    Get human-readable description for a permission.
    
    Args:
        permission: LayerPermission enum
        
    Returns:
        Description string
    """
    parts = permission.value.split(":")
    if len(parts) != 2:
        return permission.value
    
    layer, scope = parts
    layer_name = LAYER_NAMES.get(layer, layer.replace("_", " ").title())
    scope_name = scope.upper()
    
    return f"{scope_name} access to {layer_name}"


@dataclass
class PermissionCheck:
    """Result of a permission check."""
    granted: bool
    permission: str
    user_roles: List[str]
    missing_permissions: List[str]
    
    def __bool__(self) -> bool:
        return self.granted
