"""
FastAPI Route Registration

Dynamic route add/remove at runtime for hot-swapping.
"""
import inspect
from typing import Dict, List, Optional, Any, Callable, Type
from fastapi import FastAPI, APIRouter, Request, Response
from fastapi.routing import APIRoute
from fastapi.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)


class RouteRegistry:
    """
    Manages dynamic route registration for FastAPI.
    
    Features:
    - Add routes at runtime
    - Remove routes at runtime
    - List registered routes
    - Route versioning
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        self._dynamic_routes: Dict[str, Dict[str, Any]] = {}
        self._original_routes: Dict[str, APIRoute] = {}
        self._routers: Dict[str, APIRouter] = {}
    
    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: List[str] = None,
        tags: List[str] = None,
        summary: str = None,
        description: str = None,
        response_model: Type = None,
        router_prefix: str = "/api/v1"
    ) -> bool:
        """
        Add a new route at runtime.
        
        Args:
            path: Route path (e.g., "/items")
            endpoint: Handler function
            methods: HTTP methods (GET, POST, etc.)
            tags: OpenAPI tags
            summary: Route summary
            description: Route description
            response_model: Pydantic response model
            router_prefix: Router prefix
        
        Returns:
            True if route was added successfully
        """
        try:
            full_path = f"{router_prefix}{path}"
            
            # Check if route already exists
            if full_path in self._dynamic_routes:
                logger.warning(f"Route {full_path} already exists, removing first")
                self.remove_route(path, router_prefix)
            
            # Get or create router
            router = self._get_or_create_router(router_prefix)
            
            # Add route to router
            router.add_api_route(
                path=path,
                endpoint=endpoint,
                methods=methods or ["GET"],
                tags=tags or ["dynamic"],
                summary=summary,
                description=description,
                response_model=response_model
            )
            
            # Store route info
            self._dynamic_routes[full_path] = {
                "path": path,
                "full_path": full_path,
                "methods": methods or ["GET"],
                "endpoint": endpoint.__name__,
                "router_prefix": router_prefix,
                "added_at": "now"
            }
            
            logger.info(f"Added route {full_path} [{', '.join(methods or ['GET'])}]")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add route {path}: {e}")
            return False
    
    def remove_route(self, path: str, router_prefix: str = "/api/v1") -> bool:
        """
        Remove a route at runtime.
        
        Args:
            path: Route path
            router_prefix: Router prefix
        
        Returns:
            True if route was removed
        """
        try:
            full_path = f"{router_prefix}{path}"
            
            if full_path not in self._dynamic_routes:
                logger.warning(f"Route {full_path} not found")
                return False
            
            # Get router
            router = self._routers.get(router_prefix)
            if not router:
                return False
            
            # Find and remove the route from router
            routes_to_remove = [
                r for r in router.routes 
                if hasattr(r, 'path') and r.path == path
            ]
            
            for route in routes_to_remove:
                router.routes.remove(route)
            
            # Remove from tracking
            del self._dynamic_routes[full_path]
            
            logger.info(f"Removed route {full_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to remove route {path}: {e}")
            return False
    
    def add_router(self, router: APIRouter, prefix: str = "") -> bool:
        """
        Add an entire router at runtime.
        
        Args:
            router: APIRouter instance
            prefix: URL prefix
        
        Returns:
            True if router was added
        """
        try:
            self.app.include_router(router, prefix=prefix)
            
            # Track routes
            for route in router.routes:
                if hasattr(route, 'path'):
                    full_path = f"{prefix}{route.path}"
                    self._dynamic_routes[full_path] = {
                        "path": route.path,
                        "full_path": full_path,
                        "methods": list(route.methods) if hasattr(route, 'methods') else ["GET"],
                        "router_prefix": prefix,
                        "is_router": True
                    }
            
            self._routers[prefix] = router
            
            logger.info(f"Added router with prefix {prefix}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add router: {e}")
            return False
    
    def remove_router(self, prefix: str) -> bool:
        """
        Remove a router and all its routes.
        
        Args:
            prefix: Router prefix
        
        Returns:
            True if router was removed
        """
        try:
            # Remove tracked routes
            routes_to_remove = [
                path for path in self._dynamic_routes
                if self._dynamic_routes[path].get("router_prefix") == prefix
            ]
            
            for path in routes_to_remove:
                del self._dynamic_routes[path]
            
            # Remove from app routers
            self.app.router.routes = [
                r for r in self.app.router.routes
                if not (hasattr(r, 'path') and r.path.startswith(prefix))
            ]
            
            # Remove from tracking
            if prefix in self._routers:
                del self._routers[prefix]
            
            logger.info(f"Removed router with prefix {prefix}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to remove router: {e}")
            return False
    
    def list_routes(self) -> List[Dict[str, Any]]:
        """List all dynamically registered routes."""
        return list(self._dynamic_routes.values())
    
    def get_route(self, path: str) -> Optional[Dict[str, Any]]:
        """Get route information by path."""
        return self._dynamic_routes.get(path)
    
    def route_exists(self, path: str) -> bool:
        """Check if a route exists."""
        return path in self._dynamic_routes
    
    def _get_or_create_router(self, prefix: str) -> APIRouter:
        """Get existing router or create new one."""
        if prefix not in self._routers:
            router = APIRouter(prefix=prefix)
            self.app.include_router(router)
            self._routers[prefix] = router
        
        return self._routers[prefix]
    
    def update_route(
        self,
        path: str,
        new_endpoint: Callable,
        router_prefix: str = "/api/v1"
    ) -> bool:
        """
        Update an existing route with a new endpoint.
        
        Args:
            path: Route path
            new_endpoint: New handler function
            router_prefix: Router prefix
        
        Returns:
            True if route was updated
        """
        # Remove and re-add
        if not self.remove_route(path, router_prefix):
            return False
        
        # Get original route info
        full_path = f"{router_prefix}{path}"
        original_info = self._original_routes.get(full_path)
        
        methods = ["GET"]
        if original_info and hasattr(original_info, 'methods'):
            methods = list(original_info.methods)
        
        return self.add_route(
            path=path,
            endpoint=new_endpoint,
            methods=methods,
            router_prefix=router_prefix
        )
    
    def create_endpoint_from_code(
        self,
        path: str,
        code: str,
        function_name: str = "endpoint",
        methods: List[str] = None,
        router_prefix: str = "/api/v1"
    ) -> bool:
        """
        Create and register an endpoint from code string.
        
        Args:
            path: Route path
            code: Python code containing the endpoint function
            function_name: Name of the endpoint function
            methods: HTTP methods
            router_prefix: Router prefix
        
        Returns:
            True if endpoint was created
        """
        from .dynamic_import import dynamic_importer
        
        try:
            # Create unique module name
            module_name = f"dynamic_endpoint_{path.replace('/', '_').strip('_')}"
            
            # Load the module
            info = dynamic_importer.load_from_code(code, module_name)
            
            # Get the endpoint function
            endpoint = dynamic_importer.get_attribute(module_name, function_name)
            
            if not endpoint:
                logger.error(f"Function {function_name} not found in generated code")
                return False
            
            # Register the route
            return self.add_route(
                path=path,
                endpoint=endpoint,
                methods=methods,
                router_prefix=router_prefix
            )
        
        except Exception as e:
            logger.error(f"Failed to create endpoint from code: {e}")
            return False
    
    def get_openapi_schema(self) -> Dict[str, Any]:
        """Get OpenAPI schema for dynamic routes."""
        routes = []
        for path, info in self._dynamic_routes.items():
            routes.append({
                "path": path,
                "methods": info.get("methods", ["GET"]),
                "endpoint": info.get("endpoint", "unknown")
            })
        
        return {
            "dynamic_routes": routes,
            "total": len(routes)
        }


class RouteVersionManager:
    """Manages route versioning for A/B testing and gradual rollouts."""
    
    def __init__(self, route_registry: RouteRegistry):
        self.route_registry = route_registry
        self._versions: Dict[str, Dict[str, Any]] = {}
        self._active_versions: Dict[str, str] = {}  # path -> version
    
    def register_version(
        self,
        path: str,
        version: str,
        endpoint: Callable,
        traffic_percentage: float = 0
    ):
        """Register a new version of a route."""
        if path not in self._versions:
            self._versions[path] = {}
        
        self._versions[path][version] = {
            "endpoint": endpoint,
            "traffic_percentage": traffic_percentage,
            "registered_at": "now"
        }
    
    def set_active_version(self, path: str, version: str):
        """Set the active version for a route."""
        if path not in self._versions:
            raise ValueError(f"No versions registered for {path}")
        
        if version not in self._versions[path]:
            raise ValueError(f"Version {version} not found for {path}")
        
        self._active_versions[path] = version
        
        # Update the route
        version_info = self._versions[path][version]
        self.route_registry.update_route(path, version_info["endpoint"])
    
    def get_version_for_request(self, path: str, request_context: Dict = None) -> str:
        """Determine which version to use for a request."""
        import random
        
        if path not in self._versions:
            return "default"
        
        # Check for active version
        if path in self._active_versions:
            return self._active_versions[path]
        
        # Use traffic percentage for A/B testing
        versions = self._versions[path]
        roll = random.random() * 100
        
        cumulative = 0
        for version, info in versions.items():
            cumulative += info["traffic_percentage"]
            if roll <= cumulative:
                return version
        
        return list(versions.keys())[0]
