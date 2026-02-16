"""
Google Drive API Endpoints
RESTful API for Google Drive integration operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, User
from app.core.logging import get_logger
from app.integrations.google_drive.oauth import (
    get_oauth_manager, TokenRefreshError, ReauthorizationRequired
)
from app.integrations.google_drive.sync import (
    get_sync_manager, SyncResult
)
from app.integrations.google_drive.upload import (
    get_upload_manager, UploadConfig, UploadResult
)
from app.integrations.google_drive.conflict import (
    get_conflict_resolver, get_conflict_queue, Conflict, ConflictStrategy
)
from app.integrations.google_drive.tasks import (
    sync_user_drive, get_sync_scheduler, get_sync_monitor, SyncStatus
)

logger = get_logger(__name__)
router = APIRouter(prefix="/drive", tags=["Google Drive"])


# Pydantic Models
class AuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class TokenExchangeRequest(BaseModel):
    code: str
    state: str


class SyncRequest(BaseModel):
    folder_id: Optional[str] = None
    full_resync: bool = False
    auto_resolve_conflicts: bool = True


class SyncResponse(BaseModel):
    task_id: str
    status: str
    message: str


class UploadRequest(BaseModel):
    file_name: Optional[str] = None
    parent_folder_id: Optional[str] = None
    description: Optional[str] = None
    chunk_size: int = Field(default=256 * 1024, ge=64 * 1024, le=10 * 1024 * 1024)


class ConflictResolutionRequest(BaseModel):
    conflict_id: str
    strategy: str  # ConflictStrategy name
    keep_both: bool = False


class FolderTreeResponse(BaseModel):
    id: str
    name: str
    children: List[Dict[str, Any]]
    path: List[str]


class DriveFileResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    modified_time: Optional[datetime] = None
    is_folder: bool = False
    parents: List[str] = []
    web_view_link: Optional[str] = None


class ProgressResponse(BaseModel):
    upload_id: str
    bytes_uploaded: int
    total_bytes: int
    percent_complete: float
    status: str
    speed_bps: float
    eta_seconds: Optional[float] = None


# Authentication Endpoints
@router.get("/auth/url", response_model=AuthUrlResponse)
async def get_auth_url(
    current_user: User = Depends(get_current_user)
) -> AuthUrlResponse:
    """Get Google OAuth2 authorization URL."""
    try:
        oauth_manager = get_oauth_manager()
        auth_url, state = oauth_manager.get_authorization_url(str(current_user.id))
        
        return AuthUrlResponse(auth_url=auth_url, state=state)
        
    except Exception as e:
        logger.error(f"Failed to generate auth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/callback")
async def oauth_callback(
    request: TokenExchangeRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Handle OAuth2 callback and exchange code for tokens."""
    try:
        oauth_manager = get_oauth_manager()
        token_info = oauth_manager.exchange_code(
            code=request.code,
            state=request.state,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "message": "Authentication successful",
            "token_id": token_info.token_id,
            "scopes": token_info.scopes,
            "expiry": token_info.expiry.isoformat() if token_info.expiry else None
        }
        
    except ReauthorizationRequired as e:
        raise HTTPException(status_code=401, detail=str(e))
    except TokenRefreshError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/revoke")
async def revoke_auth(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Revoke Google Drive authorization."""
    try:
        oauth_manager = get_oauth_manager()
        success = oauth_manager.revoke_token(str(current_user.id))
        
        if success:
            return {"success": True, "message": "Authorization revoked"}
        else:
            raise HTTPException(status_code=500, detail="Failed to revoke authorization")
            
    except Exception as e:
        logger.error(f"Token revocation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sync Endpoints
@router.post("/sync", response_model=SyncResponse)
async def start_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> SyncResponse:
    """Start a background sync operation."""
    try:
        # Queue sync task
        task = sync_user_drive.delay(
            user_id=str(current_user.id),
            folder_id=request.folder_id,
            full_resync=request.full_resync,
            resolve_conflicts=request.auto_resolve_conflicts
        )
        
        return SyncResponse(
            task_id=task.id,
            status="queued",
            message="Sync operation queued"
        )
        
    except Exception as e:
        logger.error(f"Failed to start sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status/{task_id}")
async def get_sync_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get status of a sync task."""
    try:
        monitor = get_sync_monitor()
        task_info = monitor.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "task_id": task_id,
            "status": task_info.status.value,
            "user_id": task_info.user_id,
            "started_at": task_info.started_at.isoformat() if task_info.started_at else None,
            "completed_at": task_info.completed_at.isoformat() if task_info.completed_at else None,
            "retry_count": task_info.retry_count,
            "error_message": task_info.error_message,
            "result": task_info.result.to_dict() if task_info.result else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/schedule")
async def schedule_sync(
    interval_minutes: int = Query(default=30, ge=5, le=1440),
    folder_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Schedule periodic sync for user."""
    try:
        scheduler = get_sync_scheduler()
        schedule_id = scheduler.schedule_user_sync(
            user_id=str(current_user.id),
            interval_minutes=interval_minutes,
            folder_id=folder_id
        )
        
        return {
            "schedule_id": schedule_id,
            "interval_minutes": interval_minutes,
            "message": "Sync scheduled successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sync/schedule/{schedule_id}")
async def cancel_scheduled_sync(
    schedule_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cancel a scheduled sync."""
    try:
        scheduler = get_sync_scheduler()
        success = scheduler.cancel_scheduled_sync(schedule_id)
        
        if success:
            return {"success": True, "message": "Sync schedule cancelled"}
        else:
            raise HTTPException(status_code=404, detail="Schedule not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel sync schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# File/Folder Endpoints
@router.get("/files", response_model=List[DriveFileResponse])
async def list_files(
    folder_id: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
    page_size: int = Query(default=100, le=1000),
    current_user: User = Depends(get_current_user)
) -> List[DriveFileResponse]:
    """List files in Google Drive."""
    try:
        from app.integrations.google_drive.sync import DeltaSyncEngine
        
        engine = DeltaSyncEngine(str(current_user.id))
        await engine.initialize()
        
        # Get folder tree or search
        if query:
            # Search files
            files = await engine._search_files(query, page_size)
        else:
            # List folder contents
            children = await engine._list_folder_children(folder_id or 'root')
            files = children
        
        return [
            DriveFileResponse(
                id=f['id'],
                name=f['name'],
                mime_type=f['mimeType'],
                size=int(f.get('size', 0)) if f.get('size') else None,
                modified_time=datetime.fromisoformat(
                    f['modifiedTime'].replace('Z', '+00:00')
                ) if f.get('modifiedTime') else None,
                is_folder=f['mimeType'] == 'application/vnd.google-apps.folder',
                parents=f.get('parents', []),
                web_view_link=f.get('webViewLink')
            )
            for f in files[:page_size]
        ]
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folders/tree", response_model=FolderTreeResponse)
async def get_folder_tree(
    folder_id: str = Query(default="root"),
    current_user: User = Depends(get_current_user)
) -> FolderTreeResponse:
    """Get folder tree structure."""
    try:
        from app.integrations.google_drive.sync import DeltaSyncEngine
        
        engine = DeltaSyncEngine(str(current_user.id))
        await engine.initialize()
        
        tree = await engine.get_folder_tree(folder_id)
        
        return FolderTreeResponse(**tree)
        
    except Exception as e:
        logger.error(f"Failed to get folder tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Upload Endpoints
@router.post("/upload")
async def upload_file(
    request: Request,
    upload_request: UploadRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Upload a file to Google Drive."""
    try:
        # This would handle multipart file upload
        # For now, return upload URL
        upload_manager = get_upload_manager()
        uploader = upload_manager.get_uploader(str(current_user.id))
        
        return {
            "upload_url": f"/api/v1/drive/upload/{current_user.id}",
            "chunk_size": upload_request.chunk_size,
            "message": "Use PUT to upload file chunks"
        }
        
    except Exception as e:
        logger.error(f"Failed to initiate upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/progress/{upload_id}", response_model=ProgressResponse)
async def get_upload_progress(
    upload_id: str,
    current_user: User = Depends(get_current_user)
) -> ProgressResponse:
    """Get upload progress."""
    try:
        upload_manager = get_upload_manager()
        uploader = upload_manager.get_uploader(str(current_user.id))
        
        progress = uploader.get_progress(upload_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        return ProgressResponse(
            upload_id=progress.upload_id,
            bytes_uploaded=progress.bytes_uploaded,
            total_bytes=progress.total_bytes,
            percent_complete=progress.percent_complete,
            status=progress.status.value,
            speed_bps=progress.speed_bps,
            eta_seconds=progress.eta_seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get upload progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/{upload_id}/cancel")
async def cancel_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cancel an active upload."""
    try:
        upload_manager = get_upload_manager()
        uploader = upload_manager.get_uploader(str(current_user.id))
        
        success = uploader.cancel_upload(upload_id)
        
        if success:
            return {"success": True, "message": "Upload cancelled"}
        else:
            raise HTTPException(status_code=404, detail="Upload not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Download Endpoints
@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download a file from Google Drive."""
    try:
        upload_manager = get_upload_manager()
        uploader = upload_manager.get_uploader(str(current_user.id))
        
        # Create temporary file
        import tempfile
        import os
        
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, f"download_{file_id}")
        
        result = await uploader.download_file(file_id, temp_path)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        
        # Stream file response
        def iterfile():
            with open(temp_path, 'rb') as f:
                yield from f
            # Cleanup
            os.remove(temp_path)
            os.rmdir(temp_dir)
        
        return StreamingResponse(
            iterfile(),
            media_type=result.mime_type or 'application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={result.file_name}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Conflict Resolution Endpoints
@router.get("/conflicts")
async def get_conflicts(
    resolved_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get conflict list."""
    try:
        resolver = get_conflict_resolver()
        conflicts = resolver.get_conflict_history(resolved_only=resolved_only)
        
        return {
            "conflicts": [c.to_dict() for c in conflicts],
            "stats": resolver.get_conflict_stats()
        }
        
    except Exception as e:
        logger.error(f"Failed to get conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conflicts/resolve")
async def resolve_conflict(
    request: ConflictResolutionRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Resolve a conflict."""
    try:
        resolver = get_conflict_resolver()
        
        # Find conflict
        conflicts = resolver.get_pending_conflicts()
        conflict = next((c for c in conflicts if c.conflict_id == request.conflict_id), None)
        
        if not conflict:
            raise HTTPException(status_code=404, detail="Conflict not found")
        
        # Parse strategy
        try:
            strategy = ConflictStrategy[request.strategy.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid strategy")
        
        # Resolve
        import asyncio
        success, resolution = await resolver.resolve(conflict, strategy=strategy)
        
        return {
            "success": success,
            "conflict_id": request.conflict_id,
            "resolution": resolution,
            "strategy": strategy.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve conflict: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health & Monitoring Endpoints
@router.get("/health")
async def drive_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get Google Drive integration health status."""
    try:
        monitor = get_sync_monitor()
        metrics = monitor.get_metrics()
        
        # Check authentication
        oauth_manager = get_oauth_manager()
        credentials = oauth_manager.get_credentials(str(current_user.id))
        
        return {
            "authenticated": credentials is not None,
            "token_valid": credentials.valid if credentials else False,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's Google Drive sync statistics."""
    try:
        monitor = get_sync_monitor()
        user_tasks = monitor.get_user_tasks(str(current_user.id))
        
        completed = [t for t in user_tasks if t.status == SyncStatus.COMPLETED]
        failed = [t for t in user_tasks if t.status == SyncStatus.FAILED]
        
        total_files = sum(t.result.files_synced for t in completed if t.result)
        total_folders = sum(t.result.folders_synced for t in completed if t.result)
        
        return {
            "total_syncs": len(user_tasks),
            "successful_syncs": len(completed),
            "failed_syncs": len(failed),
            "total_files_synced": total_files,
            "total_folders_synced": total_folders,
            "recent_tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "started_at": t.started_at.isoformat() if t.started_at else None
                }
                for t in user_tasks[-10:]  # Last 10 tasks
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
