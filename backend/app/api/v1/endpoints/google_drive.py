"""
Google Drive Endpoints
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, User, get_db
from app.services.google_drive_service import GoogleDriveService
from app.core.config import settings

router = APIRouter()

class AuthUrlResponse(BaseModel):
    auth_url: str
    state: str

class TokenExchangeRequest(BaseModel):
    code: str

class DriveFileResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    modified_time: Optional[str] = None
    is_folder: bool = False

@router.get("/auth/url", response_model=AuthUrlResponse)
async def get_auth_url(current_user: User = Depends(get_current_user)):
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    state = secrets.token_urlsafe(32)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=https://www.googleapis.com/auth/drive.readonly"
        "+https://www.googleapis.com/auth/drive.file"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=consent"
    )
    return AuthUrlResponse(auth_url=auth_url, state=state)

@router.post("/auth/callback")
async def oauth_callback(
    request: TokenExchangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = GoogleDriveService(db)
    token_data = await service.exchange_code(request.code)
    
    # Get email from Google
    async with __import__('httpx').AsyncClient() as client:
        userinfo = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        email = userinfo.json().get("email") if userinfo.status_code == 200 else None
    
    service.save_tokens(str(current_user.id), token_data, email)
    return {"success": True, "email": email}

@router.get("/files", response_model=List[DriveFileResponse])
async def list_files(
    folder_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = GoogleDriveService(db)
    files = await service.list_files(str(current_user.id), folder_id)
    return [DriveFileResponse(**f) for f in files]
