import os
import time
from pathlib import Path
from typing import Callable, Set
import hashlib
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LocalDocumentWatcher(FileSystemEventHandler):
    """Watches local folder for new documents - works entirely offline"""
    
    def __init__(self, watch_path: str, callback: Callable):
        self.watch_path = Path(watch_path)
        self.callback = callback
        self.processed_files: Set[str] = set()
        self.observer = Observer()
        self.watch_path.mkdir(parents=True, exist_ok=True)
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        print(f"New file detected: {file_path}")
        
        # Simple async wrapper
        asyncio.create_task(self._process(file_path))
    
    async def _process(self, file_path: Path):
        await asyncio.sleep(2)  # Wait for file to finish writing
        file_hash = self._hash_file(file_path)
        if file_hash not in self.processed_files:
            self.callback(file_path, file_hash)
            self.processed_files.add(file_hash)
    
    def _hash_file(self, file_path: Path) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return str(time.time())  # Fallback
    
    def start(self):
        self.observer.schedule(self, str(self.watch_path), recursive=True)
        self.observer.start()
        print(f"Watching folder: {self.watch_path}")
    
    def stop(self):
        self.observer.stop()
        self.observer.join()

# Global watcher instance (initialized on startup)
watcher_instance = None

def init_watcher(watch_path: str, callback: Callable):
    global watcher_instance
    watcher_instance = LocalDocumentWatcher(watch_path, callback)
    watcher_instance.start()
    return watcher_instance
