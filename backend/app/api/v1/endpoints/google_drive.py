"""
Google Drive API Endpoints
"""
from typing import Optional, List, Dict, Any
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
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
    db: Session = Depends(get_db)
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
        
        service.save_tokens(user_id, token_data)
        
        return {
            "success": True,
            "message": "Google Drive connected successfully",
            "email": email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

@router.get("/files", response_model=List[DriveFileResponse])
async def list_files(
    folder_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List files from Google Drive (requires auth)"""
    service = GoogleDriveService(db)
    files = await service.list_files(current_user.id, folder_id)
    return [DriveFileResponse(**f) for f in files]

@router.get("/status")
async def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check Google Drive connection status"""
    from sqlalchemy import text
    result = db.execute(text("SELECT created_at FROM google_drive_tokens WHERE user_id=:uid LIMIT 1"), {"uid": str(current_user.id)})
    token = result.fetchone()
    
    return {
        "connected": token is not None,
        "email": None,  # IntegrationToken doesn't store email, could be fetched from Google API
        "last_used": token[0].isoformat() if token else None
    }
