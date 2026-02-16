"""
Resumable Uploads with Progress Tracking for Google Drive
Implements chunked resumable uploads with real-time progress monitoring.
"""

import os
import asyncio
from typing import Optional, Dict, Any, Callable, BinaryIO, AsyncIterator, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import hashlib
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from app.core.logging import get_logger
from app.integrations.google_drive.oauth import get_oauth_manager

logger = get_logger(__name__)


class UploadStatus(Enum):
    """Upload status states."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    UPLOADING = "uploading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class UploadProgress:
    """Upload progress information."""
    upload_id: str
    bytes_uploaded: int
    total_bytes: int
    status: UploadStatus
    speed_bps: float = 0.0
    eta_seconds: Optional[float] = None
    percent_complete: float = 0.0
    chunk_number: int = 0
    total_chunks: int = 0
    error_message: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        return self.status == UploadStatus.COMPLETED
    
    @property
    def is_active(self) -> bool:
        return self.status in (UploadStatus.UPLOADING, UploadStatus.INITIALIZING)


@dataclass
class UploadConfig:
    """Configuration for an upload."""
    chunk_size: int = 256 * 1024  # 256 KB chunks
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_checksum: bool = True
    compress: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UploadResult:
    """Result of an upload operation."""
    success: bool
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    web_view_link: Optional[str] = None
    md5_checksum: Optional[str] = None
    size: int = 0
    mime_type: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


class ResumableUploader:
    """
    Resumable upload handler with progress tracking.
    Implements Google Drive resumable upload protocol.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._service: Optional[Any] = None
        self._active_uploads: Dict[str, UploadProgress] = {}
        self._progress_callbacks: Dict[str, List[Callable[[UploadProgress], None]]] = {}
        self._cancelled_uploads: set = set()
    
    async def initialize(self) -> bool:
        """Initialize uploader with user credentials."""
        try:
            credentials = await asyncio.to_thread(
                get_oauth_manager().get_credentials,
                self.user_id
            )
            
            if not credentials:
                logger.error(f"No credentials for user {self.user_id}")
                return False
            
            self._service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize uploader: {e}")
            return False
    
    async def upload_file(
        self,
        file_path: str,
        parent_folder_id: Optional[str] = None,
        file_name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[UploadConfig] = None
    ) -> UploadResult:
        """
        Upload a file with resumable support and progress tracking.
        
        Args:
            file_path: Path to file to upload
            parent_folder_id: Optional parent folder ID
            file_name: Optional custom file name
            description: Optional file description
            config: Upload configuration
        
        Returns:
            Upload result
        """
        if not self._service:
            await self.initialize()
        
        config = config or UploadConfig()
        upload_id = self._generate_upload_id(file_path)
        
        try:
            path = Path(file_path)
            actual_file_name = file_name or path.name
            file_size = path.stat().st_size
            
            # Calculate checksum if enabled
            md5_checksum = None
            if config.enable_checksum:
                md5_checksum = await self._calculate_md5(file_path)
            
            # Create file metadata
            file_metadata = {
                'name': actual_file_name,
                'description': description or ''
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            # Add custom metadata
            if config.metadata:
                file_metadata['appProperties'] = config.metadata
            
            # Initialize progress
            progress = UploadProgress(
                upload_id=upload_id,
                bytes_uploaded=0,
                total_bytes=file_size,
                status=UploadStatus.INITIALIZING,
                total_chunks=(file_size + config.chunk_size - 1) // config.chunk_size
            )
            self._active_uploads[upload_id] = progress
            
            # Create media upload
            media = MediaFileUpload(
                file_path,
                resumable=True,
                chunksize=config.chunk_size
            )
            
            # Create upload request
            request = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, size, mimeType, md5Checksum'
            )
            
            # Execute chunked upload with progress
            response = await self._execute_chunked_upload(
                request, 
                progress, 
                config
            )
            
            if upload_id in self._cancelled_uploads:
                progress.status = UploadStatus.CANCELLED
                return UploadResult(
                    success=False,
                    error_message="Upload cancelled by user"
                )
            
            # Update progress
            progress.status = UploadStatus.COMPLETED
            progress.bytes_uploaded = file_size
            progress.percent_complete = 100.0
            
            self._notify_progress(upload_id, progress)
            
            logger.info(f"Upload completed: {actual_file_name} ({file_size} bytes)")
            
            return UploadResult(
                success=True,
                file_id=response.get('id'),
                file_name=response.get('name'),
                web_view_link=response.get('webViewLink'),
                md5_checksum=response.get('md5Checksum') or md5_checksum,
                size=int(response.get('size', 0)),
                mime_type=response.get('mimeType')
            )
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            
            if upload_id in self._active_uploads:
                self._active_uploads[upload_id].status = UploadStatus.FAILED
                self._active_uploads[upload_id].error_message = str(e)
            
            return UploadResult(
                success=False,
                error_message=str(e)
            )
        
        finally:
            # Cleanup
            if upload_id in self._cancelled_uploads:
                self._cancelled_uploads.discard(upload_id)
    
    async def upload_stream(
        self,
        stream: BinaryIO,
        file_name: str,
        total_size: int,
        parent_folder_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        config: Optional[UploadConfig] = None
    ) -> UploadResult:
        """
        Upload from a stream with progress tracking.
        
        Args:
            stream: Binary stream to upload from
            file_name: Name for the uploaded file
            total_size: Total size of the stream
            parent_folder_id: Optional parent folder ID
            mime_type: MIME type of the content
            config: Upload configuration
        
        Returns:
            Upload result
        """
        if not self._service:
            await self.initialize()
        
        config = config or UploadConfig()
        upload_id = self._generate_upload_id(file_name)
        
        try:
            # Create file metadata
            file_metadata = {
                'name': file_name,
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            # Initialize progress
            progress = UploadProgress(
                upload_id=upload_id,
                bytes_uploaded=0,
                total_bytes=total_size,
                status=UploadStatus.INITIALIZING,
                total_chunks=(total_size + config.chunk_size - 1) // config.chunk_size
            )
            self._active_uploads[upload_id] = progress
            
            # Create media upload from stream
            media = MediaIoBaseUpload(
                stream,
                mimetype=mime_type or 'application/octet-stream',
                resumable=True,
                chunksize=config.chunk_size
            )
            
            # Create upload request
            request = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, size, mimeType'
            )
            
            # Execute chunked upload
            response = await self._execute_chunked_upload(
                request, 
                progress, 
                config
            )
            
            progress.status = UploadStatus.COMPLETED
            progress.bytes_uploaded = total_size
            progress.percent_complete = 100.0
            
            self._notify_progress(upload_id, progress)
            
            return UploadResult(
                success=True,
                file_id=response.get('id'),
                file_name=response.get('name'),
                web_view_link=response.get('webViewLink'),
                size=int(response.get('size', 0)),
                mime_type=response.get('mimeType')
            )
            
        except Exception as e:
            logger.error(f"Stream upload failed: {e}")
            
            if upload_id in self._active_uploads:
                self._active_uploads[upload_id].status = UploadStatus.FAILED
                self._active_uploads[upload_id].error_message = str(e)
            
            return UploadResult(
                success=False,
                error_message=str(e)
            )
    
    async def _execute_chunked_upload(
        self,
        request,
        progress: UploadProgress,
        config: UploadConfig
    ) -> Dict[str, Any]:
        """Execute chunked upload with progress tracking."""
        response = None
        chunk_number = 0
        last_update_time = asyncio.get_event_loop().time()
        
        while response is None:
            # Check if cancelled
            if progress.upload_id in self._cancelled_uploads:
                raise Exception("Upload cancelled")
            
            status, response = await asyncio.to_thread(request.next_chunk)
            
            if status:
                chunk_number += 1
                progress.chunk_number = chunk_number
                progress.bytes_uploaded = status.resumable_progress
                progress.percent_complete = (
                    progress.bytes_uploaded / progress.total_bytes * 100
                )
                
                # Calculate speed
                current_time = asyncio.get_event_loop().time()
                time_delta = current_time - last_update_time
                if time_delta > 0:
                    bytes_delta = status.resumable_progress - (progress.bytes_uploaded - status.resumable_progress)
                    progress.speed_bps = bytes_delta / time_delta
                    
                    # Calculate ETA
                    remaining_bytes = progress.total_bytes - progress.bytes_uploaded
                    if progress.speed_bps > 0:
                        progress.eta_seconds = remaining_bytes / progress.speed_bps
                
                last_update_time = current_time
                progress.status = UploadStatus.UPLOADING
                
                self._notify_progress(progress.upload_id, progress)
        
        return response
    
    async def resume_upload(
        self,
        upload_id: str,
        file_path: str,
        parent_folder_id: Optional[str] = None
    ) -> UploadResult:
        """
        Resume an interrupted upload.
        
        Args:
            upload_id: ID of the upload to resume
            file_path: Path to the file
            parent_folder_id: Optional parent folder ID
        
        Returns:
            Upload result
        """
        # Check if we have a stored upload session
        # This would typically use a database to store session info
        logger.info(f"Attempting to resume upload {upload_id}")
        
        # For now, restart the upload
        return await self.upload_file(file_path, parent_folder_id)
    
    def cancel_upload(self, upload_id: str) -> bool:
        """Cancel an active upload."""
        if upload_id in self._active_uploads:
            self._cancelled_uploads.add(upload_id)
            self._active_uploads[upload_id].status = UploadStatus.CANCELLED
            logger.info(f"Upload {upload_id} cancelled")
            return True
        return False
    
    def pause_upload(self, upload_id: str) -> bool:
        """Pause an active upload."""
        if upload_id in self._active_uploads:
            self._active_uploads[upload_id].status = UploadStatus.PAUSED
            logger.info(f"Upload {upload_id} paused")
            return True
        return False
    
    def get_progress(self, upload_id: str) -> Optional[UploadProgress]:
        """Get current progress of an upload."""
        return self._active_uploads.get(upload_id)
    
    def register_progress_callback(
        self, 
        upload_id: str, 
        callback: Callable[[UploadProgress], None]
    ) -> None:
        """Register a callback for progress updates."""
        if upload_id not in self._progress_callbacks:
            self._progress_callbacks[upload_id] = []
        self._progress_callbacks[upload_id].append(callback)
    
    def _notify_progress(self, upload_id: str, progress: UploadProgress) -> None:
        """Notify all registered callbacks of progress."""
        callbacks = self._progress_callbacks.get(upload_id, [])
        for callback in callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    async def _calculate_md5(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file."""
        hash_md5 = hashlib.md5()
        
        def _calculate():
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        
        return await asyncio.to_thread(_calculate)
    
    def _generate_upload_id(self, identifier: str) -> str:
        """Generate unique upload ID."""
        data = f"{self.user_id}:{identifier}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def download_file(
        self,
        file_id: str,
        destination_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> UploadResult:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: ID of file to download
            destination_path: Path to save file
            progress_callback: Optional progress callback
        
        Returns:
            Download result
        """
        if not self._service:
            await self.initialize()
        
        try:
            # Get file metadata
            file_metadata = await asyncio.to_thread(
                self._service.files().get(fileId=file_id, fields='name, size, mimeType, md5Checksum').execute
            )
            
            # Create download request
            request = self._service.files().get_media(fileId=file_id)
            
            # Download with progress
            with open(destination_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                
                done = False
                while not done:
                    status, done = await asyncio.to_thread(downloader.next_chunk)
                    
                    if status and progress_callback:
                        progress_callback(
                            status.resumable_progress,
                            status.total_size or file_metadata.get('size', 0)
                        )
            
            logger.info(f"Download completed: {file_metadata.get('name')}")
            
            return UploadResult(
                success=True,
                file_id=file_id,
                file_name=file_metadata.get('name'),
                md5_checksum=file_metadata.get('md5Checksum'),
                size=int(file_metadata.get('size', 0)),
                mime_type=file_metadata.get('mimeType')
            )
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return UploadResult(
                success=False,
                error_message=str(e)
            )


class UploadManager:
    """Manager for handling multiple uploads."""
    
    def __init__(self):
        self._uploaders: Dict[str, ResumableUploader] = {}
    
    def get_uploader(self, user_id: str) -> ResumableUploader:
        """Get or create uploader for user."""
        if user_id not in self._uploaders:
            self._uploaders[user_id] = ResumableUploader(user_id)
        return self._uploaders[user_id]
    
    async def batch_upload(
        self,
        user_id: str,
        file_paths: list,
        parent_folder_id: Optional[str] = None,
        config: Optional[UploadConfig] = None
    ) -> list:
        """Upload multiple files."""
        uploader = self.get_uploader(user_id)
        results = []
        
        for file_path in file_paths:
            result = await uploader.upload_file(
                file_path,
                parent_folder_id=parent_folder_id,
                config=config
            )
            results.append(result)
        
        return results


# Singleton instance
upload_manager = UploadManager()


def get_upload_manager() -> UploadManager:
    """Get upload manager instance."""
    return upload_manager
