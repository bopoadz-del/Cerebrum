"""
Connector Factory

Factory pattern for creating service connectors with environment-based stub switching.

Usage:
    from app.connectors import get_connector
    
    # Automatically returns stub or real connector based on USE_STUB_CONNECTORS env var
    procore = get_connector("procore")
    result = procore.get_projects()
"""

import os
import logging
from typing import Any, Dict, Optional, Callable
from functools import lru_cache

from app.core.config import settings
from app.stubs import get_stub, BaseStub

logger = logging.getLogger(__name__)

# Type alias for connector factory functions
ConnectorFactory = Callable[[], Any]


class ConnectorFactoryRegistry:
    """
    Registry for connector factories.
    
    Supports both stub and production implementations.
    Automatically selects based on environment configuration.
    """
    
    def __init__(self):
        self._stubs: Dict[str, ConnectorFactory] = {}
        self._production: Dict[str, ConnectorFactory] = {}
        self._status_cache: Dict[str, Dict[str, Any]] = {}
    
    def register_stub(self, name: str, factory: ConnectorFactory) -> None:
        """Register a stub connector factory."""
        self._stubs[name.lower()] = factory
        logger.debug(f"Registered stub connector: {name}")
    
    def register_production(self, name: str, factory: ConnectorFactory) -> None:
        """Register a production connector factory."""
        self._production[name.lower()] = factory
        logger.debug(f"Registered production connector: {name}")
    
    def get_connector(self, name: str) -> Any:
        """
        Get a connector instance.
        
        Automatically selects stub or production based on:
        1. USE_STUB_CONNECTORS environment variable
        2. Feature-specific stub settings
        3. Availability of production connector
        
        Args:
            name: Connector name (e.g., "procore", "google_drive")
            
        Returns:
            Connector instance (stub or production)
        """
        name = name.lower()
        use_stubs = self._should_use_stubs(name)
        
        if use_stubs:
            # Try to get stub
            if name in self._stubs:
                logger.debug(f"Using stub connector for {name}")
                return self._stubs[name]()
            
            # Fallback to generic stub
            try:
                return get_stub(name)
            except ValueError:
                pass
        
        # Try production
        if name in self._production:
            logger.debug(f"Using production connector for {name}")
            return self._production[name]()
        
        # No production connector available - use stub if available
        if name in self._stubs:
            logger.warning(f"Production connector {name} not available, using stub")
            return self._stubs[name]()
        
        # Last resort - try generic stub
        try:
            return get_stub(name)
        except ValueError:
            pass
        
        raise ValueError(f"No connector available for: {name}")
    
    def _should_use_stubs(self, name: str) -> bool:
        """Determine if stubs should be used for a connector."""
        # Global stub setting
        if settings.USE_STUB_CONNECTORS:
            return True
        
        # Service-specific settings
        if name == "slack" and settings.USE_STUB_NOTIFICATIONS:
            return True
        
        if name in ["openai", "ml"] and settings.USE_STUB_ML:
            return True
        
        # Check environment variable override
        env_var = f"USE_STUB_{name.upper()}"
        if os.getenv(env_var, "").lower() == "true":
            return True
        
        return False
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered connectors."""
        status = {}
        all_names = set(self._stubs.keys()) | set(self._production.keys())
        
        for name in all_names:
            has_stub = name in self._stubs
            has_prod = name in self._production
            use_stub = self._should_use_stubs(name)
            
            status[name] = {
                "stub_available": has_stub,
                "production_available": has_prod,
                "using_stub": use_stub,
                "mode": "stub" if use_stub else "production",
            }
        
        return status
    
    def list_connectors(self) -> list:
        """List all registered connector names."""
        return sorted(set(self._stubs.keys()) | set(self._production.keys()))


# Global registry instance
_registry = ConnectorFactoryRegistry()


def register_connector(name: str, stub_factory: Optional[ConnectorFactory] = None, 
                       production_factory: Optional[ConnectorFactory] = None) -> None:
    """
    Register a connector with the factory.
    
    Args:
        name: Connector name
        stub_factory: Factory function for stub implementation
        production_factory: Factory function for production implementation
    """
    if stub_factory:
        _registry.register_stub(name, stub_factory)
    if production_factory:
        _registry.register_production(name, production_factory)


def get_connector(name: str) -> Any:
    """
    Get a connector instance by name.
    
    Automatically selects stub or production based on environment.
    
    Args:
        name: Connector name (e.g., "procore", "google_drive")
        
    Returns:
        Connector instance
    """
    return _registry.get_connector(name)


def get_connector_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all connectors."""
    return _registry.get_status()


def list_connectors() -> list:
    """List all available connector names."""
    return _registry.list_connectors()


# =============================================================================
# Built-in Connector Registration
# =============================================================================

def _register_builtin_connectors():
    """Register all built-in connector stubs."""
    from app.stubs import (
        ProcoreStub, AconexStub, PrimaveraStub,
        GoogleDriveStub, SlackStub, OpenAIStub
    )
    
    register_connector(
        "procore",
        stub_factory=ProcoreStub,
    )
    register_connector(
        "aconex",
        stub_factory=AconexStub,
    )
    register_connector(
        "primavera",
        stub_factory=PrimaveraStub,
    )
    register_connector(
        "primavera_p6",
        stub_factory=PrimaveraStub,
    )
    register_connector(
        "p6",
        stub_factory=PrimaveraStub,
    )

    register_connector(
        "google_drive",
        stub_factory=GoogleDriveStub,
    )
    register_connector(
        "drive",
        stub_factory=GoogleDriveStub,
    )
    register_connector(
        "slack",
        stub_factory=SlackStub,
    )
    register_connector(
        "openai",
        stub_factory=OpenAIStub,
    )


# Register built-in connectors on module load
_register_builtin_connectors()
