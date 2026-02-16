"""
Google Drive Delta Sync Engine with pageToken tracking
Implements efficient incremental synchronization using Google Drive API changes.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set, AsyncIterator, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from app.core.logging import get_logger
from app.integrations.google_drive.oauth import get_oauth_manager

logger = get_logger(__name__)


class ChangeType(Enum):
    """Types of changes in Google Drive."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    TRASH = "trash"
    UNTRASH = "untrash"
    MOVE = "move"


@dataclass
class FileChange:
    """Represents a single file change."""
    file_id: str
    change_type: ChangeType
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    parent_ids: List[str] = field(default_factory=list)
    modified_time: Optional[datetime] = None
    size: Optional[int] = None
    md5_checksum: Optional[str] = None
    is_folder: bool = False
    trashed: bool = False
    
    @property
    def is_structural_change(self) -> bool:
        """Check if change affects folder structure."""
        return self.change_type in (ChangeType.MOVE, ChangeType.CREATE, ChangeType.DELETE)


@dataclass
class SyncCheckpoint:
    """Sync checkpoint for resumable synchronization."""
    page_token: str
    timestamp: datetime
    synced_file_ids: Set[str] = field(default_factory=set)
    folder_structure_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_token": self.page_token,
            "timestamp": self.timestamp.isoformat(),
            "synced_file_ids": list(self.synced_file_ids),
            "folder_structure_hash": self.folder_structure_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncCheckpoint':
        return cls(
            page_token=data["page_token"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            synced_file_ids=set(data.get("synced_file_ids", [])),
            folder_structure_hash=data.get("folder_structure_hash")
        )


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    changes: List[FileChange]
    new_page_token: str
    files_synced: int
    folders_synced: int
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class DeltaSyncEngine:
    """
    Google Drive delta sync engine using pageToken tracking.
    Implements efficient incremental synchronization.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._service: Optional[Any] = None
        self._checkpoint: Optional[SyncCheckpoint] = None
        self._change_handlers: List[Callable[[FileChange], None]] = []
        self._batch_size = 100
        self._max_retries = 3
        
    async def initialize(self) -> bool:
        """Initialize sync engine with user credentials."""
        try:
            credentials = await asyncio.to_thread(
                get_oauth_manager().get_credentials,
                self.user_id
            )
            
            if not credentials:
                logger.error(f"No credentials found for user {self.user_id}")
                return False
            
            self._service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
            
            # Load or create checkpoint
            self._checkpoint = await self._load_checkpoint()
            if not self._checkpoint:
                # Start fresh - get initial page token
                start_page_token = await self._get_start_page_token()
                self._checkpoint = SyncCheckpoint(
                    page_token=start_page_token,
                    timestamp=datetime.utcnow()
                )
                await self._save_checkpoint()
            
            logger.info(f"Sync engine initialized for user {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sync engine: {e}")
            return False
    
    async def sync(
        self, 
        folder_id: Optional[str] = None,
        include_trashed: bool = False
    ) -> SyncResult:
        """
        Perform delta sync from last checkpoint.
        
        Args:
            folder_id: Optional folder to limit sync scope
            include_trashed: Whether to include trashed items
        """
        start_time = datetime.utcnow()
        changes: List[FileChange] = []
        errors: List[str] = []
        files_synced = 0
        folders_synced = 0
        
        try:
            if not self._service:
                await self.initialize()
            
            page_token = self._checkpoint.page_token if self._checkpoint else None
            
            while True:
                try:
                    response = await self._fetch_changes_page(
                        page_token=page_token,
                        folder_id=folder_id,
                        include_trashed=include_trashed
                    )
                    
                    for change in response.get('changes', []):
                        file_change = self._parse_change(change)
                        if file_change:
                            changes.append(file_change)
                            
                            if file_change.is_folder:
                                folders_synced += 1
                            else:
                                files_synced += 1
                            
                            # Notify handlers
                            for handler in self._change_handlers:
                                try:
                                    handler(file_change)
                                except Exception as e:
                                    logger.error(f"Change handler error: {e}")
                    
                    # Update checkpoint
                    page_token = response.get('newStartPageToken', page_token)
                    
                    # Check if more pages
                    if not response.get('nextPageToken'):
                        break
                        
                except HttpError as e:
                    if e.resp.status == 410:  # Gone - need full resync
                        logger.warning("Page token expired, performing full resync")
                        page_token = await self._get_start_page_token()
                        continue
                    raise
            
            # Update checkpoint
            self._checkpoint = SyncCheckpoint(
                page_token=page_token,
                timestamp=datetime.utcnow(),
                synced_file_ids=self._checkpoint.synced_file_ids if self._checkpoint else set()
            )
            await self._save_checkpoint()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                f"Sync completed: {files_synced} files, {folders_synced} folders, "
                f"{len(changes)} changes in {duration:.2f}s"
            )
            
            return SyncResult(
                success=True,
                changes=changes,
                new_page_token=page_token,
                files_synced=files_synced,
                folders_synced=folders_synced,
                duration_seconds=duration
            )
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            errors.append(str(e))
            
            return SyncResult(
                success=False,
                changes=changes,
                new_page_token=self._checkpoint.page_token if self._checkpoint else "",
                files_synced=files_synced,
                folders_synced=folders_synced,
                errors=errors,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds()
            )
    
    async def sync_stream(
        self, 
        folder_id: Optional[str] = None
    ) -> AsyncIterator[FileChange]:
        """Stream changes as they are fetched."""
        if not self._service:
            await self.initialize()
        
        page_token = self._checkpoint.page_token if self._checkpoint else None
        
        while True:
            response = await self._fetch_changes_page(
                page_token=page_token,
                folder_id=folder_id
            )
            
            for change in response.get('changes', []):
                file_change = self._parse_change(change)
                if file_change:
                    yield file_change
            
            page_token = response.get('newStartPageToken', page_token)
            
            if not response.get('nextPageToken'):
                break
        
        # Update checkpoint
        self._checkpoint = SyncCheckpoint(
            page_token=page_token,
            timestamp=datetime.utcnow()
        )
        await self._save_checkpoint()
    
    async def full_resync(self, folder_id: Optional[str] = None) -> SyncResult:
        """Perform full resync by resetting page token."""
        logger.info("Starting full resync")
        
        # Reset checkpoint
        start_page_token = await self._get_start_page_token()
        self._checkpoint = SyncCheckpoint(
            page_token=start_page_token,
            timestamp=datetime.utcnow(),
            synced_file_ids=set()
        )
        await self._save_checkpoint()
        
        return await self.sync(folder_id=folder_id)
    
    def register_change_handler(self, handler: Callable[[FileChange], None]) -> None:
        """Register a handler for change notifications."""
        self._change_handlers.append(handler)
    
    async def _fetch_changes_page(
        self,
        page_token: str,
        folder_id: Optional[str] = None,
        include_trashed: bool = False
    ) -> Dict[str, Any]:
        """Fetch a single page of changes."""
        params = {
            'pageToken': page_token,
            'spaces': 'drive',
            'pageSize': self._batch_size,
            'includeRemoved': True,
            'includeItemsFromAllDrives': True,
            'supportsAllDrives': True
        }
        
        if folder_id:
            # Filter changes to specific folder
            params['driveId'] = folder_id
            params['includeCorpusRemovals'] = True
        
        return await asyncio.to_thread(
            self._service.changes().list(**params).execute
        )
    
    async def _get_start_page_token(self) -> str:
        """Get starting page token for sync."""
        response = await asyncio.to_thread(
            self._service.changes().getStartPageToken().execute
        )
        return response.get('startPageToken')
    
    def _parse_change(self, change: Dict[str, Any]) -> Optional[FileChange]:
        """Parse Google Drive change into FileChange."""
        file_data = change.get('file', {})
        
        if not file_data and not change.get('removed'):
            return None
        
        # Determine change type
        if change.get('removed'):
            change_type = ChangeType.DELETE
        elif file_data.get('trashed'):
            change_type = ChangeType.TRASH
        elif change.get('changeType') == 'file':
            # Check if new or updated
            file_id = file_data.get('id')
            if file_id and self._checkpoint and file_id in self._checkpoint.synced_file_ids:
                change_type = ChangeType.UPDATE
            else:
                change_type = ChangeType.CREATE
        else:
            change_type = ChangeType.UPDATE
        
        # Update synced set
        if file_data.get('id') and self._checkpoint:
            self._checkpoint.synced_file_ids.add(file_data.get('id'))
        
        return FileChange(
            file_id=file_data.get('id') or change.get('fileId'),
            change_type=change_type,
            file_name=file_data.get('name'),
            mime_type=file_data.get('mimeType'),
            parent_ids=file_data.get('parents', []),
            modified_time=datetime.fromisoformat(
                file_data.get('modifiedTime', '').replace('Z', '+00:00')
            ) if file_data.get('modifiedTime') else None,
            size=int(file_data.get('size', 0)) if file_data.get('size') else None,
            md5_checksum=file_data.get('md5Checksum'),
            is_folder=file_data.get('mimeType') == 'application/vnd.google-apps.folder',
            trashed=file_data.get('trashed', False)
        )
    
    async def _load_checkpoint(self) -> Optional[SyncCheckpoint]:
        """Load sync checkpoint from storage."""
        # Implementation would load from database
        return None
    
    async def _save_checkpoint(self) -> None:
        """Save sync checkpoint to storage."""
        # Implementation would save to database
        pass
    
    async def get_folder_tree(self, folder_id: str = 'root') -> Dict[str, Any]:
        """Get complete folder tree structure."""
        tree = {
            'id': folder_id,
            'name': 'Root',
            'children': [],
            'path': []
        }
        
        try:
            # Get folder metadata
            folder = await asyncio.to_thread(
                self._service.files().get(
                    fileId=folder_id,
                    fields='id, name, parents'
                ).execute
            )
            tree['name'] = folder.get('name', 'Root')
            
            # Get children
            children = await self._list_folder_children(folder_id)
            
            for child in children:
                if child.get('mimeType') == 'application/vnd.google-apps.folder':
                    # Recursively get subfolder
                    subtree = await self.get_folder_tree(child['id'])
                    tree['children'].append(subtree)
                else:
                    tree['children'].append({
                        'id': child['id'],
                        'name': child['name'],
                        'mimeType': child['mimeType'],
                        'size': child.get('size'),
                        'modifiedTime': child.get('modifiedTime')
                    })
            
            return tree
            
        except Exception as e:
            logger.error(f"Failed to get folder tree: {e}")
            return tree
    
    async def _list_folder_children(self, folder_id: str) -> List[Dict[str, Any]]:
        """List all children of a folder."""
        children = []
        page_token = None
        
        while True:
            params = {
                'q': f"'{folder_id}' in parents and trashed = false",
                'spaces': 'drive',
                'fields': 'nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)',
                'pageSize': 1000,
                'includeItemsFromAllDrives': True,
                'supportsAllDrives': True
            }
            
            if page_token:
                params['pageToken'] = page_token
            
            response = await asyncio.to_thread(
                self._service.files().list(**params).execute
            )
            
            children.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            
            if not page_token:
                break
        
        return children


class SyncManager:
    """Manages sync engines for multiple users."""
    
    def __init__(self):
        self._engines: Dict[str, DeltaSyncEngine] = {}
        self._sync_intervals: Dict[str, int] = {}  # seconds
    
    def get_engine(self, user_id: str) -> DeltaSyncEngine:
        """Get or create sync engine for user."""
        if user_id not in self._engines:
            self._engines[user_id] = DeltaSyncEngine(user_id)
        return self._engines[user_id]
    
    async def schedule_sync(
        self, 
        user_id: str, 
        interval_seconds: int = 300
    ) -> None:
        """Schedule periodic sync for user."""
        self._sync_intervals[user_id] = interval_seconds
        
        while True:
            try:
                engine = self.get_engine(user_id)
                result = await engine.sync()
                
                if not result.success:
                    logger.error(f"Scheduled sync failed for {user_id}: {result.errors}")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Sync scheduler error for {user_id}: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error
    
    def stop_sync(self, user_id: str) -> None:
        """Stop scheduled sync for user."""
        if user_id in self._sync_intervals:
            del self._sync_intervals[user_id]


# Singleton instance
sync_manager = SyncManager()


def get_sync_manager() -> SyncManager:
    """Get sync manager instance."""
    return sync_manager
