"""
Google Drive API Endpoints

Provides OAuth flow and file operations for Google Drive integration.
Uses synchronous database sessions compatible with GoogleDriveService.
"""
from typing import Optional, List, Dict, Any
import secrets
import uuid as uuid_module
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx

from app.api.deps import get_current_user, User, get_db
from app.core.logging import get_logger
from app.services.google_drive_service import (
    GoogleDriveService, 
    GoogleDriveAuthError,
    GoogleDriveNotFoundError,
    GoogleDriveError
)
from app.services.gdrive_persistent import get_permanent_drive, PermanentGoogleDrive
from app.core.config import settings

router = APIRouter(prefix="/google-drive", tags=["Google Drive"])

# Module-level logger
logger = get_logger(__name__)


# =============================================================================
# Request/Response Schemas
# =============================================================================

class AuthUrlResponse(BaseModel):
    """OAuth authorization URL response."""
    auth_url: str
    state: str


class DriveFileResponse(BaseModel):
    """File metadata response."""
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    modified_time: Optional[str] = None
    created_time: Optional[str] = None
    is_folder: bool = False
    is_google_doc: bool = False
    web_view_link: Optional[str] = None
    description: Optional[str] = None


class DriveStatusResponse(BaseModel):
    """Connection status response."""
    connected: bool
    email: Optional[str] = None
    last_sync: Optional[str] = None
    can_refresh: bool = False
    expires_soon: bool = False
    expiry: Optional[str] = None


class DownloadRequest(BaseModel):
    """File download request."""
    export_format: Optional[str] = None


class SearchResponse(BaseModel):
    """Search results response."""
    query: str
    results: List[DriveFileResponse]
    count: int


class CreateFolderRequest(BaseModel):
    """Create folder request."""
    name: str
    parent_id: Optional[str] = None


class FolderResponse(BaseModel):
    """Created folder response."""
    id: str
    name: str


class UploadResponse(BaseModel):
    """File upload response."""
    id: str
    name: str
    mime_type: str
    size: Optional[str] = None
    web_view_link: Optional[str] = None


# =============================================================================
# OAuth Authentication Endpoints
# =============================================================================

@router.get("/auth/url", response_model=AuthUrlResponse)
async def get_auth_url(
    current_user: User = Depends(get_current_user)
):
    """Get Google OAuth authorization URL."""
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # Include user_id in state for verification
    nonce = secrets.token_urlsafe(16)
    state = f"{nonce}:{current_user.id}"
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=https://www.googleapis.com/auth/drive.readonly"
        "+https://www.googleapis.com/auth/drive.file"
        "+https://www.googleapis.com/auth/drive.metadata.readonly"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=consent"
    )
    return AuthUrlResponse(auth_url=auth_url, state=state)


@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Google.
    
    Note: This endpoint is called by Google (no auth required).
    Returns HTML that communicates with parent window via postMessage.
    """
    import urllib.parse
    import logging
    logger = logging.getLogger(__name__)
    
    def make_response(success: bool, message: str, code_val: str = "", state_val: str = ""):
        code_js = json.dumps(code_val)
        state_js = json.dumps(state_val)
        error_js = json.dumps(message)
        frontend_url = settings.FRONTEND_URL or "https://cerebrum-frontend.onrender.com"
        
        if success:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Google Drive Connected</title>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'GOOGLE_DRIVE_AUTH_SUCCESS',
                        code: {code_js},
                        state: {state_js}
                    }}, '{frontend_url}');
                }}
                setTimeout(() => window.close(), 500);
            </script></head>
            <body><h2>✓ Google Drive Connected!</h2><p>You can close this window.</p></body>
            </html>
            """)
        else:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Authentication Failed</title>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'GOOGLE_DRIVE_AUTH_ERROR',
                        error: {error_js}
                    }}, '{frontend_url}');
                }}
                setTimeout(() => window.close(), 3000);
            </script></head>
            <body>
                <h2>✗ Authentication Failed</h2>
                <p>{message}</p>
                <p>This window will close automatically.</p>
            </body>
            </html>
            """, status_code=400)
    
    try:
        # Decode state
        decoded_state = urllib.parse.unquote(state)
        user_id_raw = decoded_state.split(":")[-1] if ":" in decoded_state else decoded_state
        
        try:
            user_id = uuid_module.UUID(user_id_raw)
        except ValueError:
            return make_response(False, f"Invalid user ID in state: {user_id_raw}")
        
        # Validate configuration
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return make_response(False, "Google OAuth not properly configured")
        
        # Exchange code for tokens
        service = GoogleDriveService(db)
        token_data = await service.exchange_code(code)
        
        # Get user email from Google
        email = None
        try:
            async with httpx.AsyncClient() as client:
                userinfo = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                if userinfo.status_code == 200:
                    email = userinfo.json().get("email")
        except Exception as e:
            logger.warning(f"Could not get user email: {e}")
        
        # Verify user exists
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return make_response(False, "User not found")
        
        # Save tokens
        service.save_tokens(user_id, token_data, account_email=email)
        logger.info(f"Google Drive connected for user {user_id}")
        
        return make_response(True, "Success", code, state)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        return make_response(False, str(e))


# =============================================================================
# Connection Status Endpoints
# =============================================================================

@router.get("/status", response_model=DriveStatusResponse)
async def get_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Google Drive connection status for current user."""
    service = GoogleDriveService(db)
    status = service.get_status(current_user.id)
    return DriveStatusResponse(**status)


@router.post("/disconnect")
async def disconnect_drive(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Google Drive (revoke tokens)."""
    service = GoogleDriveService(db)
    success = service.disconnect(current_user.id)
    
    if success:
        return {"success": True, "message": "Google Drive disconnected"}
    else:
        raise HTTPException(status_code=500, detail="Failed to disconnect")


# =============================================================================
# File Operations Endpoints
# =============================================================================

@router.get("/files", response_model=List[DriveFileResponse])
async def list_files(
    folder_id: Optional[str] = None,
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List files from Google Drive with auto-refresh."""
    service = get_permanent_drive(db, current_user.id)
    
    try:
        files = await service.list_files(
            folder_id=folder_id, 
            page_size=page_size
        )
        return [DriveFileResponse(**f) for f in files]
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GoogleDriveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/{file_id}", response_model=DriveFileResponse)
async def get_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed file metadata with auto-refresh."""
    service = get_permanent_drive(db, current_user.id)
    
    try:
        file = await service.get_file(file_id)
        return DriveFileResponse(**file)
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GoogleDriveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    export_format: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download file from Google Drive with auto-refresh.
    
    For Google Workspace files (Docs, Sheets, etc.), use export_format:
    - Google Docs: application/pdf, text/plain
    - Google Sheets: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    - Google Slides: application/vnd.openxmlformats-officedocument.presentationml.presentation
    """
    import json
    service = get_permanent_drive(db, current_user.id)
    
    try:
        content, filename, mime_type = await service.download_file(
            file_id, 
            export_format=export_format
        )
        
        # Determine content type for response
        response_mime = export_format or mime_type or "application/octet-stream"
        
        return StreamingResponse(
            iter([content]),
            media_type=response_mime,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GoogleDriveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search", response_model=SearchResponse)
async def search_files(
    query: str = Query(..., min_length=1),
    file_type: Optional[str] = Query(None, regex="^(folder|document|spreadsheet|pdf)$"),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search files in Google Drive by name with auto-refresh."""
    service = get_permanent_drive(db, current_user.id)
    
    try:
        files = await service.search_files(
            query=query,
            file_type=file_type,
            page_size=page_size
        )
        return SearchResponse(
            query=query,
            results=[DriveFileResponse(**f) for f in files],
            count=len(files)
        )
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/folders", response_model=FolderResponse)
async def create_folder(
    request: CreateFolderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new folder in Google Drive with auto-refresh."""
    service = get_permanent_drive(db, current_user.id)
    
    try:
        folder = await service.create_folder(
            name=request.name,
            parent_id=request.parent_id
        )
        return FolderResponse(**folder)
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    permanent: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete or trash a file with auto-refresh.
    
    - permanent=false (default): Move to trash
    - permanent=true: Permanently delete
    """
    service = get_permanent_drive(db, current_user.id)
    
    try:
        success = await service.delete_file(file_id, permanent=permanent)
        return {
            "success": success,
            "file_id": file_id,
            "permanent": permanent
        }
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GoogleDriveNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GoogleDriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Legacy/Compatibility Endpoints
# =============================================================================

@router.post("/scan")
async def scan_drive(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Scan Google Drive for all files (legacy endpoint) with auto-refresh."""
    service = get_permanent_drive(db, current_user.id)
    try:
        files = await service.list_files(page_size=500000)
        return {
            "success": True,
            "files_scanned": len(files),
            "files": files
        }
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects")
async def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Google Drive folders as projects (legacy endpoint) with auto-refresh."""
    service = get_permanent_drive(db, current_user.id)
    try:
        files = await service.list_files(page_size=500000)
        folders = [f for f in files if f.get("is_folder")]
        projects = [
            {
                "id": f["id"],
                "name": f["name"],
                "file_count": 0,
                "status": "active",
                "updated_at": f.get("modified_time")
            }
            for f in folders
        ]
        return {
            "success": True,
            "projects": projects if projects else []
        }
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/files")
async def get_project_files(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get files within a specific folder/project (legacy endpoint) with auto-refresh."""
    service = get_permanent_drive(db, current_user.id)
    try:
        files = await service.list_files(
            folder_id=project_id, 
            page_size=500000
        )
        files_only = [f for f in files if not f.get("is_folder")]
        return {
            "success": True,
            "files": files_only
        }
    except GoogleDriveAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Debug Endpoints (Temporary - for troubleshooting)
# =============================================================================

@router.get("/debug/credentials")
async def debug_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check Google Drive credential status.
    """
    from app.models.google_drive import GoogleDriveToken
    service = GoogleDriveService(db)
    
    # Check token in DB
    token = db.query(GoogleDriveToken).filter(
        GoogleDriveToken.user_id == current_user.id
    ).first()
    
    if not token:
        return {
            "error": "No token found",
            "user_id": str(current_user.id),
            "solution": "Reconnect Google Drive - no stored credentials"
        }
    
    # Try to get credentials
    try:
        creds = service.get_credentials(current_user.id)
        
        result = {
            "token_exists": True,
            "user_id": str(current_user.id),
            "email": token.google_email,
            "expired": token.is_expired(),
            "credentials_valid": creds is not None,
            "creds_type": str(type(creds)) if creds else None,
        }
        
        # Additional credential details if available
        if creds:
            result["creds_valid"] = creds.valid if hasattr(creds, 'valid') else 'N/A'
            result["creds_expired"] = creds.expired if hasattr(creds, 'expired') else 'N/A'
            if hasattr(creds, 'expiry') and creds.expiry:
                result["creds_expiry"] = creds.expiry.isoformat()
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "token_exists": True,
            "user_id": str(current_user.id),
            "email": token.google_email,
            "expired": token.is_expired(),
            "solution": "Check error details - may need to reconnect"
        }


@router.get("/debug/token-details")
async def debug_token_details(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed token information (safely - no sensitive data exposed).
    """
    from app.models.google_drive import GoogleDriveToken
    
    token = db.query(GoogleDriveToken).filter(
        GoogleDriveToken.user_id == current_user.id
    ).first()
    
    if not token:
        return {"error": "No token found", "user_id": str(current_user.id)}
    
    # Return safe token details (no actual credentials)
    return {
        "user_id": str(token.user_id),
        "google_email": token.google_email,
        "token_exists": bool(token.token_data),
        "refresh_token_exists": bool(token.refresh_token),
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "is_expired": token.is_expired(),
        "created_at": token.created_at.isoformat() if token.created_at else None,
        "updated_at": token.updated_at.isoformat() if token.updated_at else None,
    }


@router.get("/indexing-status")
async def get_indexing_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Google Drive indexing status with auto-refresh."""
    from app.models.google_drive import GoogleDriveToken
    
    # Check if user has a token
    token = db.query(GoogleDriveToken).filter(
        GoogleDriveToken.user_id == current_user.id
    ).first()
    
    if not token:
        return {
            "status": "disconnected",
            "total_files": 0,
            "indexed_files": 0,
            "progress": 0
        }
    
    # Get file count from Google Drive with auto-refresh
    service = get_permanent_drive(db, current_user.id)
    try:
        files = await service.list_files(page_size=1)
        return {
            "status": "connected",
            "total_files": len(files),
            "indexed_files": 0,
            "progress": 0
        }
    except GoogleDriveAuthError:
        return {
            "status": "expired",
            "total_files": 0,
            "indexed_files": 0,
            "progress": 0
        }
    except Exception as e:
        logger.error(f"Error getting indexing status: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "total_files": 0,
            "indexed_files": 0,
            "progress": 0
        }
