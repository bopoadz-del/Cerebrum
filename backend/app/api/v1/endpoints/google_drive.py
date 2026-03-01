"""
Google Drive API Endpoints
"""
from typing import Optional, List, Dict, Any
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.api.deps import get_current_user, User, get_db
from app.services.google_drive_service import GoogleDriveService
from app.core.config import settings

router = APIRouter()

class AuthUrlResponse(BaseModel):
    auth_url: str
    state: str

class DriveFileResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    modified_time: Optional[str] = None
    is_folder: bool = False
    web_view_link: Optional[str] = None

@router.get("/auth/url", response_model=AuthUrlResponse)
async def get_auth_url(current_user: User = Depends(get_current_user)):
    """Get Google OAuth URL"""
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # Include user_id in state so we can identify them on callback
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
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback from Google (NO AUTH REQUIRED - called by Google)"""
    try:
        # DEBUG: Log the raw state received from Google
        print(f"DEBUG: Received raw state = {repr(state)}")
        
        # URL decode in case state was encoded
        import urllib.parse
        decoded_state = urllib.parse.unquote(state)
        print(f"DEBUG: URL decoded state = {repr(decoded_state)}")
        
        # Extract user_id from state (format: random:user_id)
        user_id_raw = decoded_state.split(":")[-1] if ":" in decoded_state else decoded_state
        
        print(f"DEBUG: Extracted user_id_raw = {repr(user_id_raw)}")
        
        try:
            user_id = uuid.UUID(user_id_raw)
            print(f"DEBUG: Parsed user_id = {user_id}")
        except ValueError as e:
            print(f"DEBUG: UUID parse failed: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid OAuth state (user id): {user_id_raw}")
        
        # Validate Google OAuth is configured
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not set")
        if not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_SECRET not set")
        
        service = GoogleDriveService(db)
        token_data = await service.exchange_code(code)
        
        # Get user email from Google
        async with httpx.AsyncClient() as client:
            userinfo = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            email = userinfo.json().get("email") if userinfo.status_code == 200 else None
        
        # Verify user exists before saving tokens
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=400, detail="OAuth user not found")
        
        service.save_tokens(user_id, token_data, account_email=email)
        
        # Return HTML that sends postMessage to parent window (COOP-compatible)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Google Drive Connected</title>
            <script>
                // Send auth success message to parent window
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'GOOGLE_DRIVE_AUTH_SUCCESS',
                        code: '{code}',
                        state: '{state}'
                    }}, 'https://cerebrum-frontend.onrender.com');
                }}
                // Close popup after short delay
                setTimeout(() => window.close(), 500);
            </script>
        </head>
        <body>
            <h2>Google Drive Connected!</h2>
            <p>You can close this window.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        # Return error HTML for popup
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Failed</title>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'GOOGLE_DRIVE_AUTH_ERROR',
                        error: '{str(e)}'
                    }}, 'https://cerebrum-frontend.onrender.com');
                }}
                setTimeout(() => window.close(), 3000);
            </script>
        </head>
        <body>
            <h2>Authentication Failed</h2>
            <p>{str(e)}</p>
            <p>This window will close automatically.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)

@router.get("/files", response_model=List[DriveFileResponse])
async def list_files(
    folder_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List files from Google Drive (requires auth)"""
    service = GoogleDriveService(db)
    files = await service.list_files(current_user.id, folder_id)
    return [DriveFileResponse(**f) for f in files]


@router.post("/scan")
async def scan_drive(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Scan Google Drive for all files (requires auth)"""
    service = GoogleDriveService(db)
    try:
        files = await service.list_files(current_user.id, page_size=100)
        return {
            "success": True,
            "files_scanned": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects")
async def get_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Google Drive folders as projects (requires auth)"""
    service = GoogleDriveService(db)
    try:
        files = await service.list_files(current_user.id, page_size=100)
        # Filter to only folders and format as projects
        folders = [f for f in files if f.get("is_folder")]
        projects = [
            {
                "id": f["id"],
                "name": f["name"],
                "file_count": 0,  # Would need separate query
                "status": "active",
                "updated_at": f.get("modified_time")
            }
            for f in folders
        ]
        return {
            "success": True,
            "projects": projects if projects else []
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search")
async def search_files(
    query: str,
    folder_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search files in Google Drive (requires auth)"""
    service = GoogleDriveService(db)
    try:
        # Get all files and filter by name
        all_files = await service.list_files(current_user.id, folder_id, page_size=100)
        query_lower = query.lower()
        results = [f for f in all_files if query_lower in f.get("name", "").lower()]
        
        return {
            "success": True,
            "results": [
                {
                    "id": f["id"],
                    "score": 1.0,
                    "metadata": {
                        "name": f["name"],
                        "project": folder_id or "root",
                        "mime_type": f.get("mime_type"),
                        "modified_time": f.get("modified_time")
                    }
                }
                for f in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def get_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check Google Drive connection status"""
    try:
        from app.models.integration import IntegrationToken, IntegrationProvider
        import uuid
        
        # Ensure user_id is UUID type
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        
        # Use async query
        stmt = select(IntegrationToken).where(
            IntegrationToken.user_id == user_id,
            IntegrationToken.service == IntegrationProvider.GOOGLE_DRIVE,
            IntegrationToken.is_active == True
        )
        result = await db.execute(stmt)
        token = result.scalar_one_or_none()
        
        return {
            "connected": token is not None,
            "email": token.account_email if token else None,
            "last_used": token.expiry.isoformat() if token and token.expiry else None
        }
    except Exception as e:
        # Log error but don't fail - return not connected
        import logging
        import traceback
        logging.getLogger(__name__).error(f"Error checking Google Drive status: {e}")
        logging.getLogger(__name__).error(traceback.format_exc())
        # Return 200 with error info instead of raising
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=200,
            content={
                "connected": False,
                "email": None,
                "last_used": None,
                "error": str(e)
            }
        )
