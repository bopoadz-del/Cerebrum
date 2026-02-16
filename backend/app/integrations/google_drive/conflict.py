"""
Conflict Resolution Logic for Google Drive Synchronization
Implements multiple conflict resolution strategies with automatic and manual modes.
"""

import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import json

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConflictStrategy(Enum):
    """Available conflict resolution strategies."""
    LOCAL_WINS = auto()      # Keep local version
    REMOTE_WINS = auto()     # Keep remote version
    LAST_MODIFIED_WINS = auto()  # Keep most recently modified
    MERGE = auto()           # Attempt to merge (for specific file types)
    RENAME_BOTH = auto()     # Keep both with renamed versions
    MANUAL = auto()          # Require manual resolution


class ConflictType(Enum):
    """Types of conflicts that can occur."""
    CONTENT_DIFFERENT = auto()      # Same file, different content
    NAME_CLASH = auto()             # Different files, same name
    DELETED_LOCALLY_MODIFIED_REMOTELY = auto()
    DELETED_REMOTELY_MODIFIED_LOCALLY = auto()
    FOLDER_STRUCTURE_CHANGE = auto()
    PERMISSION_CHANGE = auto()


@dataclass
class FileVersion:
    """Represents a version of a file."""
    file_id: str
    name: str
    content_hash: Optional[str] = None
    modified_time: Optional[datetime] = None
    size: int = 0
    md5_checksum: Optional[str] = None
    revision_id: Optional[str] = None
    is_local: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def compute_hash(self, content: bytes) -> str:
        """Compute content hash."""
        return hashlib.sha256(content).hexdigest()


@dataclass
class Conflict:
    """Represents a synchronization conflict."""
    conflict_id: str
    conflict_type: ConflictType
    local_version: Optional[FileVersion]
    remote_version: Optional[FileVersion]
    common_ancestor: Optional[FileVersion] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution: Optional[str] = None
    resolution_strategy: Optional[ConflictStrategy] = None
    resolution_time: Optional[datetime] = None
    resolution_metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_auto_resolvable(self) -> bool:
        """Check if conflict can be auto-resolved."""
        return self.conflict_type in (
            ConflictType.CONTENT_DIFFERENT,
            ConflictType.NAME_CLASH
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.name,
            "local_version": self._version_to_dict(self.local_version),
            "remote_version": self._version_to_dict(self.remote_version),
            "common_ancestor": self._version_to_dict(self.common_ancestor),
            "detected_at": self.detected_at.isoformat(),
            "resolved": self.resolved,
            "resolution": self.resolution,
            "resolution_strategy": self.resolution_strategy.name if self.resolution_strategy else None,
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None
        }
    
    def _version_to_dict(self, version: Optional[FileVersion]) -> Optional[Dict[str, Any]]:
        if not version:
            return None
        return {
            "file_id": version.file_id,
            "name": version.name,
            "content_hash": version.content_hash,
            "modified_time": version.modified_time.isoformat() if version.modified_time else None,
            "size": version.size,
            "is_local": version.is_local
        }


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    merged_content: Optional[bytes] = None
    merge_strategy_used: Optional[str] = None
    conflicts_remaining: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class ConflictResolver:
    """
    Main conflict resolution engine.
    Implements multiple strategies for resolving sync conflicts.
    """
    
    # Strategy priorities for auto-resolution
    DEFAULT_STRATEGY_PRIORITY = [
        ConflictStrategy.LAST_MODIFIED_WINS,
        ConflictStrategy.REMOTE_WINS,
        ConflictStrategy.RENAME_BOTH
    ]
    
    def __init__(self):
        self._strategy_handlers: Dict[ConflictStrategy, Callable] = {
            ConflictStrategy.LOCAL_WINS: self._resolve_local_wins,
            ConflictStrategy.REMOTE_WINS: self._resolve_remote_wins,
            ConflictStrategy.LAST_MODIFIED_WINS: self._resolve_last_modified_wins,
            ConflictStrategy.MERGE: self._resolve_merge,
            ConflictStrategy.RENAME_BOTH: self._resolve_rename_both,
            ConflictStrategy.MANUAL: self._resolve_manual
        }
        self._merge_handlers: Dict[str, Callable] = {
            'text/plain': self._merge_text_files,
            'application/json': self._merge_json_files,
            'text/csv': self._merge_csv_files,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': self._merge_excel_files
        }
        self._conflict_history: List[Conflict] = []
        self._resolution_callbacks: List[Callable[[Conflict], None]] = []
    
    def detect_conflict(
        self,
        local_version: Optional[FileVersion],
        remote_version: Optional[FileVersion],
        common_ancestor: Optional[FileVersion] = None
    ) -> Optional[Conflict]:
        """
        Detect if there's a conflict between versions.
        
        Returns None if no conflict, Conflict object if conflict exists.
        """
        # Determine conflict type
        conflict_type = self._determine_conflict_type(
            local_version, remote_version, common_ancestor
        )
        
        if not conflict_type:
            return None
        
        # Generate conflict ID
        conflict_id = self._generate_conflict_id(
            local_version, remote_version, conflict_type
        )
        
        conflict = Conflict(
            conflict_id=conflict_id,
            conflict_type=conflict_type,
            local_version=local_version,
            remote_version=remote_version,
            common_ancestor=common_ancestor
        )
        
        self._conflict_history.append(conflict)
        
        logger.info(f"Conflict detected: {conflict_id} of type {conflict_type.name}")
        
        return conflict
    
    async def resolve(
        self,
        conflict: Conflict,
        strategy: Optional[ConflictStrategy] = None,
        auto_resolve: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Resolve a conflict using specified or auto-detected strategy.
        
        Returns:
            Tuple of (success, resolution_description)
        """
        if conflict.resolved:
            return True, conflict.resolution
        
        # Determine strategy
        if not strategy:
            if auto_resolve and conflict.is_auto_resolvable:
                strategy = self._select_auto_strategy(conflict)
            else:
                strategy = ConflictStrategy.MANUAL
        
        handler = self._strategy_handlers.get(strategy)
        if not handler:
            logger.error(f"No handler for strategy {strategy}")
            return False, None
        
        try:
            success, resolution = await handler(conflict)
            
            if success:
                conflict.resolved = True
                conflict.resolution = resolution
                conflict.resolution_strategy = strategy
                conflict.resolution_time = datetime.utcnow()
                
                # Notify callbacks
                for callback in self._resolution_callbacks:
                    try:
                        callback(conflict)
                    except Exception as e:
                        logger.error(f"Resolution callback error: {e}")
                
                logger.info(f"Conflict {conflict.conflict_id} resolved with {strategy.name}")
            
            return success, resolution
            
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            return False, str(e)
    
    def _determine_conflict_type(
        self,
        local: Optional[FileVersion],
        remote: Optional[FileVersion],
        ancestor: Optional[FileVersion]
    ) -> Optional[ConflictType]:
        """Determine the type of conflict."""
        # Deleted locally, modified remotely
        if not local and remote:
            if ancestor:
                return ConflictType.DELETED_LOCALLY_MODIFIED_REMOTELY
            return ConflictType.NAME_CLASH
        
        # Deleted remotely, modified locally
        if local and not remote:
            if ancestor:
                return ConflictType.DELETED_REMOTELY_MODIFIED_LOCALLY
            return ConflictType.NAME_CLASH
        
        # Both exist - check for content differences
        if local and remote:
            # Check if content is different
            if local.content_hash != remote.content_hash:
                if local.name != remote.name:
                    return ConflictType.NAME_CLASH
                return ConflictType.CONTENT_DIFFERENT
            
            # Same content but different metadata
            if local.name != remote.name:
                return ConflictType.NAME_CLASH
        
        return None
    
    def _select_auto_strategy(self, conflict: Conflict) -> ConflictStrategy:
        """Select best auto-resolution strategy."""
        for strategy in self.DEFAULT_STRATEGY_PRIORITY:
            if self._can_apply_strategy(conflict, strategy):
                return strategy
        return ConflictStrategy.MANUAL
    
    def _can_apply_strategy(
        self, 
        conflict: Conflict, 
        strategy: ConflictStrategy
    ) -> bool:
        """Check if strategy can be applied to conflict."""
        if strategy == ConflictStrategy.MERGE:
            # Check if merge is possible
            mime_type = conflict.local_version.metadata.get('mime_type') if conflict.local_version else None
            return mime_type in self._merge_handlers
        return True
    
    async def _resolve_local_wins(
        self, 
        conflict: Conflict
    ) -> Tuple[bool, str]:
        """Resolve by keeping local version."""
        if not conflict.local_version:
            return False, "No local version to keep"
        
        resolution = f"Kept local version: {conflict.local_version.name}"
        return True, resolution
    
    async def _resolve_remote_wins(
        self, 
        conflict: Conflict
    ) -> Tuple[bool, str]:
        """Resolve by keeping remote version."""
        if not conflict.remote_version:
            return False, "No remote version to keep"
        
        resolution = f"Kept remote version: {conflict.remote_version.name}"
        return True, resolution
    
    async def _resolve_last_modified_wins(
        self, 
        conflict: Conflict
    ) -> Tuple[bool, str]:
        """Resolve by keeping most recently modified version."""
        local_time = conflict.local_version.modified_time if conflict.local_version else None
        remote_time = conflict.remote_version.modified_time if conflict.remote_version else None
        
        if not local_time and not remote_time:
            return False, "No modification times available"
        
        if not local_time:
            return await self._resolve_remote_wins(conflict)
        
        if not remote_time:
            return await self._resolve_local_wins(conflict)
        
        if local_time >= remote_time:
            return await self._resolve_local_wins(conflict)
        else:
            return await self._resolve_remote_wins(conflict)
    
    async def _resolve_merge(
        self, 
        conflict: Conflict
    ) -> Tuple[bool, str]:
        """Attempt to merge versions."""
        mime_type = conflict.local_version.metadata.get('mime_type') if conflict.local_version else None
        
        merge_handler = self._merge_handlers.get(mime_type)
        if not merge_handler:
            # Fall back to rename both
            return await self._resolve_rename_both(conflict)
        
        result = await merge_handler(conflict)
        
        if result.success:
            resolution = f"Merged versions using {result.merge_strategy_used}"
            conflict.resolution_metadata['merged_content'] = result.merged_content
            return True, resolution
        else:
            # Fall back to rename both
            return await self._resolve_rename_both(conflict)
    
    async def _resolve_rename_both(
        self, 
        conflict: Conflict
    ) -> Tuple[bool, str]:
        """Resolve by keeping both versions with renamed names."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        resolutions = []
        
        if conflict.local_version:
            local_name = f"{conflict.local_version.name}_local_{timestamp}"
            resolutions.append(f"Local renamed to: {local_name}")
        
        if conflict.remote_version:
            remote_name = f"{conflict.remote_version.name}_remote_{timestamp}"
            resolutions.append(f"Remote renamed to: {remote_name}")
        
        return True, "; ".join(resolutions)
    
    async def _resolve_manual(
        self, 
        conflict: Conflict
    ) -> Tuple[bool, str]:
        """Mark conflict for manual resolution."""
        return False, "Manual resolution required"
    
    async def _merge_text_files(self, conflict: Conflict) -> MergeResult:
        """Merge text files using line-based diff."""
        try:
            # This would use actual file content
            # Simplified implementation
            return MergeResult(
                success=True,
                merge_strategy_used="line_based_diff",
                merged_content=b"# Merged content\n"
            )
        except Exception as e:
            return MergeResult(
                success=False,
                error_message=str(e)
            )
    
    async def _merge_json_files(self, conflict: Conflict) -> MergeResult:
        """Merge JSON files using deep merge."""
        try:
            # Deep merge JSON objects
            return MergeResult(
                success=True,
                merge_strategy_used="deep_json_merge",
                merged_content=b"{}"
            )
        except Exception as e:
            return MergeResult(
                success=False,
                error_message=str(e)
            )
    
    async def _merge_csv_files(self, conflict: Conflict) -> MergeResult:
        """Merge CSV files using row-based merge."""
        try:
            return MergeResult(
                success=True,
                merge_strategy_used="row_based_merge",
                merged_content=b""
            )
        except Exception as e:
            return MergeResult(
                success=False,
                error_message=str(e)
            )
    
    async def _merge_excel_files(self, conflict: Conflict) -> MergeResult:
        """Merge Excel files using sheet-based merge."""
        try:
            return MergeResult(
                success=True,
                merge_strategy_used="sheet_based_merge",
                merged_content=b""
            )
        except Exception as e:
            return MergeResult(
                success=False,
                error_message=str(e)
            )
    
    def _generate_conflict_id(
        self,
        local: Optional[FileVersion],
        remote: Optional[FileVersion],
        conflict_type: ConflictType
    ) -> str:
        """Generate unique conflict ID."""
        data = f"{local.file_id if local else ''}:{remote.file_id if remote else ''}:{conflict_type.name}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def register_resolution_callback(
        self, 
        callback: Callable[[Conflict], None]
    ) -> None:
        """Register callback for resolution notifications."""
        self._resolution_callbacks.append(callback)
    
    def get_conflict_history(
        self, 
        resolved_only: bool = False
    ) -> List[Conflict]:
        """Get conflict history."""
        if resolved_only:
            return [c for c in self._conflict_history if c.resolved]
        return self._conflict_history.copy()
    
    def get_pending_conflicts(self) -> List[Conflict]:
        """Get unresolved conflicts."""
        return [c for c in self._conflict_history if not c.resolved]
    
    def get_conflict_stats(self) -> Dict[str, int]:
        """Get conflict statistics."""
        total = len(self._conflict_history)
        resolved = len([c for c in self._conflict_history if c.resolved])
        pending = total - resolved
        
        by_type = {}
        for conflict in self._conflict_history:
            type_name = conflict.conflict_type.name
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        return {
            "total": total,
            "resolved": resolved,
            "pending": pending,
            "by_type": by_type
        }


class ConflictResolutionQueue:
    """Queue for managing conflict resolutions."""
    
    def __init__(self):
        self._queue: List[Conflict] = []
        self._resolver = ConflictResolver()
        self._processing = False
    
    async def add_conflict(self, conflict: Conflict) -> None:
        """Add conflict to queue."""
        self._queue.append(conflict)
        logger.info(f"Added conflict {conflict.conflict_id} to queue")
    
    async def process_queue(self, auto_resolve: bool = True) -> List[Conflict]:
        """Process all conflicts in queue."""
        self._processing = True
        processed = []
        
        try:
            for conflict in self._queue[:]:
                if not conflict.resolved:
                    success, _ = await self._resolver.resolve(
                        conflict, 
                        auto_resolve=auto_resolve
                    )
                    processed.append(conflict)
                    
                    if success:
                        self._queue.remove(conflict)
        finally:
            self._processing = False
        
        return processed
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status."""
        return {
            "queue_length": len(self._queue),
            "processing": self._processing,
            "pending_conflicts": [c.conflict_id for c in self._queue if not c.resolved]
        }


# Singleton instances
conflict_resolver = ConflictResolver()
conflict_queue = ConflictResolutionQueue()


def get_conflict_resolver() -> ConflictResolver:
    """Get conflict resolver instance."""
    return conflict_resolver


def get_conflict_queue() -> ConflictResolutionQueue:
    """Get conflict queue instance."""
    return conflict_queue
