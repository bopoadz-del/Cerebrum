"""
Dynamic Module Import/Reload

Handles dynamic module loading and reloading using importlib.
"""
import os
import sys
import importlib
import importlib.util
import tempfile
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """Information about a dynamically loaded module."""
    name: str
    path: str
    module: Any
    version: str
    loaded_at: float
    is_reloadable: bool


class DynamicImporter:
    """
    Dynamic module importer with hot-reload support.
    
    Features:
    - Load modules from code strings
    - Reload modules without restart
    - Track module versions
    - Isolate module namespaces
    """
    
    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._original_modules: Dict[str, Any] = {}
        self._temp_dir = tempfile.mkdtemp(prefix="cerebrum_modules_")
    
    def load_from_code(
        self,
        code: str,
        module_name: str,
        version: str = "1.0.0"
    ) -> ModuleInfo:
        """
        Load a module from code string.
        
        Args:
            code: Python code to load
            module_name: Name for the module
            version: Module version
        
        Returns:
            ModuleInfo for the loaded module
        """
        import time
        
        # Create module file
        module_path = os.path.join(self._temp_dir, f"{module_name}.py")
        with open(module_path, 'w') as f:
            f.write(code)
        
        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(module)
        
        # Store module info
        info = ModuleInfo(
            name=module_name,
            path=module_path,
            module=module,
            version=version,
            loaded_at=time.time(),
            is_reloadable=True
        )
        
        self._modules[module_name] = info
        
        logger.info(f"Loaded module {module_name} v{version} from {module_path}")
        return info
    
    def load_from_file(
        self,
        file_path: str,
        module_name: Optional[str] = None,
        version: str = "1.0.0"
    ) -> ModuleInfo:
        """
        Load a module from file.
        
        Args:
            file_path: Path to Python file
            module_name: Optional module name (defaults to filename)
            version: Module version
        
        Returns:
            ModuleInfo for the loaded module
        """
        import time
        
        if module_name is None:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        
        # Execute the module
        spec.loader.exec_module(module)
        
        # Store module info
        info = ModuleInfo(
            name=module_name,
            path=file_path,
            module=module,
            version=version,
            loaded_at=time.time(),
            is_reloadable=True
        )
        
        self._modules[module_name] = info
        
        logger.info(f"Loaded module {module_name} v{version} from {file_path}")
        return info
    
    def reload(self, module_name: str) -> Optional[ModuleInfo]:
        """
        Reload a module.
        
        Args:
            module_name: Name of module to reload
        
        Returns:
            Updated ModuleInfo or None if not found
        """
        info = self._modules.get(module_name)
        if not info:
            logger.warning(f"Module {module_name} not found for reload")
            return None
        
        if not info.is_reloadable:
            logger.warning(f"Module {module_name} is not reloadable")
            return None
        
        # Reload using importlib
        import time
        
        if module_name in sys.modules:
            # Remove from sys.modules to force reload
            del sys.modules[module_name]
        
        # Reload the module
        spec = importlib.util.spec_from_file_location(module_name, info.path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Update info
        info.module = module
        info.loaded_at = time.time()
        
        logger.info(f"Reloaded module {module_name}")
        return info
    
    def unload(self, module_name: str) -> bool:
        """
        Unload a module.
        
        Args:
            module_name: Name of module to unload
        
        Returns:
            True if unloaded successfully
        """
        info = self._modules.get(module_name)
        if not info:
            return False
        
        # Remove from sys.modules
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        # Remove from tracking
        del self._modules[module_name]
        
        # Remove temp file if it exists
        if info.path.startswith(self._temp_dir):
            try:
                os.unlink(info.path)
            except:
                pass
        
        logger.info(f"Unloaded module {module_name}")
        return True
    
    def get_module(self, module_name: str) -> Optional[Any]:
        """Get a loaded module by name."""
        info = self._modules.get(module_name)
        return info.module if info else None
    
    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        """Get module info by name."""
        return self._modules.get(module_name)
    
    def list_modules(self) -> List[ModuleInfo]:
        """List all loaded modules."""
        return list(self._modules.values())
    
    def call_function(
        self,
        module_name: str,
        function_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Call a function from a loaded module.
        
        Args:
            module_name: Name of the module
            function_name: Name of the function
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        """
        module = self.get_module(module_name)
        if not module:
            raise ValueError(f"Module {module_name} not found")
        
        func = getattr(module, function_name, None)
        if not func:
            raise ValueError(f"Function {function_name} not found in {module_name}")
        
        if not callable(func):
            raise ValueError(f"{function_name} is not callable")
        
        return func(*args, **kwargs)
    
    def get_attribute(
        self,
        module_name: str,
        attribute_name: str
    ) -> Any:
        """Get an attribute from a loaded module."""
        module = self.get_module(module_name)
        if not module:
            raise ValueError(f"Module {module_name} not found")
        
        return getattr(module, attribute_name, None)
    
    @contextmanager
    def isolated_import(self, module_name: str, code: str):
        """
        Context manager for isolated module import.
        
        Usage:
            with importer.isolated_import("temp_module", code) as module:
                result = module.some_function()
        """
        info = None
        try:
            info = self.load_from_code(code, module_name)
            yield info.module
        finally:
            if info:
                self.unload(module_name)
    
    def cleanup(self):
        """Clean up all loaded modules and temp files."""
        # Unload all modules
        for module_name in list(self._modules.keys()):
            self.unload(module_name)
        
        # Remove temp directory
        try:
            import shutil
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except:
            pass
        
        logger.info("Cleaned up dynamic importer")


class ModuleCache:
    """Cache for compiled modules to improve reload performance."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        import time
        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set item in cache with LRU eviction."""
        import time
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest = min(self._access_times, key=self._access_times.get)
            del self._cache[oldest]
            del self._access_times[oldest]
        
        self._cache[key] = value
        self._access_times[key] = time.time()
    
    def invalidate(self, key: str):
        """Invalidate a cache entry."""
        if key in self._cache:
            del self._cache[key]
            del self._access_times[key]
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._access_times.clear()


# Singleton instance
dynamic_importer = DynamicImporter()
