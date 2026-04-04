"""
Local Filesystem Document Watcher

Watches local folder for new documents and integrates with the existing
trigger system for auto-processing. Works entirely offline for local development.
"""

import os
import time
import asyncio
import hashlib
import mimetypes
from pathlib import Path
from typing import Callable, Set, Optional
from datetime import datetime

from app.core.logging import get_logger
from app.core.config import settings

# Optional watchdog import (graceful fallback if not available)
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileCreatedEvent = None

# Import trigger system
from app.triggers.engine import EventType, event_bus

logger = get_logger(__name__)


class LocalDocumentWatcher(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """
    Watches local folder for new documents and emits FILE_UPLOADED events.
    Works entirely offline - integrates with existing trigger engine.
    """
    
    def __init__(
        self,
        watch_path: str,
        file_extensions: Optional[Set[str]] = None,
        enable_processing: bool = True
    ):
        """
        Initialize the local document watcher.
        
        Args:
            watch_path: Path to watch for new files
            file_extensions: Set of file extensions to watch (default: common docs)
            enable_processing: Whether to auto-process detected files
        """
        self.watch_path = Path(watch_path)
        self.enable_processing = enable_processing
        self.processed_files: Set[str] = set()
        self.observer: Optional[Observer] = None
        
        # Default document extensions
        self.file_extensions = file_extensions or {
            '.pdf', '.doc', '.docx', '.txt', '.html', '.htm',
            '.xls', '.xlsx', '.ppt', '.pptx',
            '.ifc', '.dwg', '.dxf',  # BIM/CAD files
            '.png', '.jpg', '.jpeg', '.gif', '.bmp',  # Images
        }
        
        # Ensure watch directory exists
        self.watch_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local document watcher initialized", watch_path=str(self.watch_path))
        
    def on_created(self, event):
        """Handle file creation event from watchdog."""
        if not WATCHDOG_AVAILABLE:
            return
            
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if file extension is in our watch list
        if file_path.suffix.lower() not in self.file_extensions:
            return
        
        logger.info(f"New file detected: {file_path}")
        
        # Process asynchronously
        asyncio.create_task(self._process_file(file_path))
    
    async def _process_file(self, file_path: Path):
        """
        Process a newly detected file.
        
        Waits for file to finish writing, computes hash, and emits
        FILE_UPLOADED event to the trigger engine.
        """
        try:
            # Wait for file to finish writing (simple heuristic)
            await self._wait_for_file_complete(file_path)
            
            # Compute file hash
            file_hash = await self._compute_file_hash(file_path)
            
            # Skip if already processed
            if file_hash in self.processed_files:
                logger.debug(f"File already processed, skipping", path=str(file_path))
                return
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # Build file metadata
            file_stat = file_path.stat()
            metadata = {
                "file_id": file_hash[:16],  # Use hash prefix as ID
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_hash": file_hash,
                "mime_type": mime_type or "application/octet-stream",
                "size_bytes": file_stat.st_size,
                "source": "local_filesystem",
                "detected_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                "Local file detected, emitting FILE_UPLOADED event",
                file_name=file_path.name,
                mime_type=mime_type,
                size=file_stat.st_size,
            )
            
            # Emit event to trigger engine (integrates with existing file_triggers.py)
            event = event_bus.create_event(
                event_type=EventType.FILE_UPLOADED,
                source="local_filesystem.watcher",
                payload=metadata,
            )
            await event_bus.emit(event)
            
            # Track processed file
            self.processed_files.add(file_hash)
            
        except Exception as e:
            logger.error(
                "Failed to process local file",
                path=str(file_path),
                error=str(e),
            )
    
    async def _wait_for_file_complete(self, file_path: Path, timeout: int = 30):
        """
        Wait for file to finish being written.
        
        Args:
            file_path: Path to file
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        last_size = -1
        stable_count = 0
        
        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size
                
                if current_size == last_size and current_size > 0:
                    stable_count += 1
                    if stable_count >= 2:  # Size stable for 2 checks
                        await asyncio.sleep(0.5)  # Small buffer
                        return
                else:
                    stable_count = 0
                    last_size = current_size
                    
                await asyncio.sleep(1)
                
            except FileNotFoundError:
                await asyncio.sleep(0.5)
                continue
    
    async def _compute_file_hash(self, file_path: Path) -> str:
        """
        Compute MD5 hash of file contents.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of file hash
        """
        hash_md5 = hashlib.md5()
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_hash_file, file_path)
        except Exception as e:
            logger.warning(f"Failed to hash file, using timestamp fallback", error=str(e))
            return f"{file_path.name}_{time.time()}"
    
    def _sync_hash_file(self, file_path: Path) -> str:
        """Synchronous file hashing (runs in thread pool)."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def start(self):
        """Start watching the directory."""
        if not WATCHDOG_AVAILABLE:
            logger.warning(
                "watchdog not installed, local file watching disabled. "
                "Install with: pip install watchdog"
            )
            return False
        
        if self.observer is not None:
            logger.warning("Watcher already running")
            return True
        
        try:
            self.observer = Observer()
            self.observer.schedule(self, str(self.watch_path), recursive=True)
            self.observer.start()
            logger.info(
                "Local file watcher started",
                watch_path=str(self.watch_path),
                extensions=list(self.file_extensions),
            )
            return True
        except Exception as e:
            logger.error("Failed to start file watcher", error=str(e))
            return False
    
    def stop(self):
        """Stop watching the directory."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Local file watcher stopped")


# Global watcher instance
_watcher_instance: Optional[LocalDocumentWatcher] = None


def init_watcher(watch_path: Optional[str] = None) -> Optional[LocalDocumentWatcher]:
    """
    Initialize and start the local file watcher.
    
    Args:
        watch_path: Path to watch (default: from LOCAL_DATA_PATH env or ./data)
        
    Returns:
        Watcher instance or None if disabled/failed
    """
    global _watcher_instance
    
    # Check if local file watching is enabled
    if os.getenv("WATCH_LOCAL_FILES", "false").lower() != "true":
        logger.info("Local file watching disabled (set WATCH_LOCAL_FILES=true to enable)")
        return None
    
    # Get watch path
    watch_path = watch_path or os.getenv("LOCAL_DATA_PATH", "/data/diriyah_docs")
    
    if not os.path.isdir(watch_path):
        logger.warning(
            "Watch path does not exist, creating",
            path=watch_path,
        )
        os.makedirs(watch_path, exist_ok=True)
    
    # Create and start watcher
    _watcher_instance = LocalDocumentWatcher(watch_path)
    success = _watcher_instance.start()
    
    if success:
        logger.info("Local file watcher initialized successfully")
        return _watcher_instance
    else:
        _watcher_instance = None
        return None


def stop_watcher():
    """Stop the global watcher instance."""
    global _watcher_instance
    if _watcher_instance:
        _watcher_instance.stop()
        _watcher_instance = None


def get_watcher() -> Optional[LocalDocumentWatcher]:
    """Get the global watcher instance."""
    return _watcher_instance
