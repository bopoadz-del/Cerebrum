"""
Capability Registry Module

Self-coding capability lifecycle management with dependency resolution.
"""
from .models import (
    Capability,
    CapabilityCreate,
    CapabilityUpdate,
    CapabilityStatus,
    CapabilityType,
    DependencyGraph,
    CapabilityDB
)
from .crud import CapabilityCRUD
from .dependencies import DependencyResolver, VersionConstraint, PipDependencyResolver
from .endpoints import router

__all__ = [
    # Models
    "Capability",
    "CapabilityCreate", 
    "CapabilityUpdate",
    "CapabilityStatus",
    "CapabilityType",
    "DependencyGraph",
    "CapabilityDB",
    # CRUD
    "CapabilityCRUD",
    # Dependencies
    "DependencyResolver",
    "VersionConstraint",
    "PipDependencyResolver",
    # Endpoints
    "router"
]
