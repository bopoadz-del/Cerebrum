"""
Google Drive Service - Real API Integration
Handles OAuth flow, token refresh, and Drive API operations
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.logging import get_logger
from app.models.google_drive import GoogleDriveToken
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class GoogleDriveService:
    """Service for interacting with Google Drive API"""
    
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
    
    def __init__(self, db: Session):
        self.db = db
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        if not all([self.client_id, self.client_secret]):
            raise HTTPException(
                status_code=500,
                detail="Google OAuth credentials not configured"
            )
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access/refresh tokens"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to exchange OAuth code: {response.text}"
                )
            
            return response.json()
    
    async def refresh_access_token(self, token: GoogleDriveToken) -> str:
        """Refresh expired access token using refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "refresh_token": token.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                token.is_active = False
                self.db.commit()
                raise HTTPException(
                    status_code=401,
                    detail="Failed to refresh token. Please re-authenticate."
                )
            
            data = response.json()
            token.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            token.updated_at = datetime.utcnow()
            self.db.commit()
            
            return token.access_token
    
    async def get_valid_access_token(self, user_id: int) -> str:
        """Get valid (non-expired) access token for user, refresh if needed"""
        token = self.db.query(GoogleDriveToken).filter(
            GoogleDriveToken.user_id == user_id,
            GoogleDriveToken.is_active == True
        ).first()
        
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Google Drive not connected. Please authenticate first."
            )
        
        if token.is_expired():
            return await self.refresh_access_token(token)
        
        # Update last used
        token.last_used_at = datetime.utcnow()
        self.db.commit()
        
        return token.access_token
    
    async def list_files(
        self, 
        user_id: int, 
        folder_id: Optional[str] = None,
        query: Optional[str] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """List files from user's Google Drive"""
        access_token = await self.get_valid_access_token(user_id)
        
        # Build query
        q_parts = ["trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        if query:
            q_parts.append(f"name contains '{query}'")
        
        q_string = " and ".join(q_parts)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.DRIVE_API_BASE}/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": q_string,
                    "pageSize": page_size,
                    "fields": "files(id,name,mimeType,size,modifiedTime,parents,webViewLink,thumbnailLink)",
                    "orderBy": "folder,name"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Drive API error: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch files from Google Drive"
                )
            
            data = response.json()
            files = data.get("files", [])
            
            # Transform to consistent format
            return [
                {
                    "id": f["id"],
                    "name": f["name"],
                    "mime_type": f["mimeType"],
                    "size": int(f.get("size", 0)) if "size" in f else None,
                    "modified_time": f.get("modifiedTime"),
                    "is_folder": f["mimeType"] == "application/vnd.google-apps.folder",
                    "web_view_link": f.get("webViewLink"),
                    "thumbnail_link": f.get("thumbnailLink")
                }
                for f in files
            ]
    
    async def get_folder_tree(self, user_id: int) -> List[Dict[str, Any]]:
        """Get folder hierarchy from Google Drive"""
        access_token = await self.get_valid_access_token(user_id)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.DRIVE_API_BASE}/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": "mimeType='application/vnd.google-apps.folder' and trashed=false",
                    "pageSize": 1000,
                    "fields": "files(id,name,parents)",
                    "orderBy": "name"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch folders")
            
            folders = response.json().get("files", [])
            return [
                {"id": f["id"], "name": f["name"], "parents": f.get("parents", [])}
                for f in folders
            ]
    
    async def revoke_token(self, user_id: int) -> bool:
        """Revoke Google Drive access for user"""
        token = self.db.query(GoogleDriveToken).filter(
            GoogleDriveToken.user_id == user_id,
            GoogleDriveToken.is_active == True
        ).first()
        
        if not token:
            return False
        
        # Try to revoke with Google
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": token.access_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
        except Exception as e:
            logger.warning(f"Failed to revoke token with Google: {e}")
        
        # Deactivate in database regardless
        token.is_active = False
        token.revoked_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def save_tokens(
        self, 
        user_id: int, 
        token_data: Dict[str, Any], 
        google_user_info: Optional[Dict] = None
    ) -> GoogleDriveToken:
        """Save or update OAuth tokens for user"""
        expires_in = token_data.get("expires_in", 3600)
        
        # Check if token exists
        existing = self.db.query(GoogleDriveToken).filter(
            GoogleDriveToken.user_id == user_id
        ).first()
        
        if existing:
            existing.access_token = token_data["access_token"]
            existing.refresh_token = token_data.get("refresh_token", existing.refresh_token)
            existing.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            if google_user_info:
                existing.google_email = google_user_info.get("email")
                existing.google_user_id = google_user_info.get("id")
            token = existing
        else:
            token = GoogleDriveToken(
                user_id=user_id,
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                scopes=token_data.get("scope", ""),
                google_email=google_user_info.get("email") if google_user_info else None,
                google_user_id=google_user_info.get("id") if google_user_info else None
            )
            self.db.add(token)
        
        self.db.commit()
        self.db.refresh(token)
        return token
