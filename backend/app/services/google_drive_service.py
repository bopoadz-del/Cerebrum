"""
Google Drive Service
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.google_drive import GoogleDriveToken

class GoogleDriveService:
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
    
    def __init__(self, db: Session):
        self.db = db
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        if not self.client_id or not self.client_secret:
            raise HTTPException(status_code=500, detail="Google OAuth credentials not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Token exchange failed: {response.text}")
            return response.json()
    
    async def get_valid_token(self, user_id: str) -> str:
        token = self.db.query(GoogleDriveToken).filter(
            GoogleDriveToken.user_id == user_id,
            GoogleDriveToken.is_active == True
        ).first()
        
        if not token:
            raise HTTPException(status_code=401, detail="Google Drive not connected. Please authenticate first.")
        
        if token.is_expired():
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
                    token.is_active = False
                    self.db.commit()
                    raise HTTPException(status_code=401, detail="Failed to refresh token. Please re-authenticate.")
                
                data = response.json()
                token.access_token = data["access_token"]
                token.expires_at = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
                self.db.commit()
        
        token.last_used_at = datetime.utcnow()
        self.db.commit()
        return token.access_token
    
    async def list_files(self, user_id: str, folder_id: Optional[str] = None) -> List[Dict]:
        access_token = await self.get_valid_token(user_id)
        
        q_parts = ["trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.DRIVE_API_BASE}/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": " and ".join(q_parts),
                    "pageSize": 100,
                    "fields": "files(id,name,mimeType,size,modifiedTime,webViewLink,thumbnailLink)",
                    "orderBy": "folder,name"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch files from Google Drive")
            
            files = response.json().get("files", [])
            return [{
                "id": f["id"],
                "name": f["name"],
                "mime_type": f["mimeType"],
                "size": int(f["size"]) if "size" in f else None,
                "modified_time": f.get("modifiedTime"),
                "is_folder": f["mimeType"] == "application/vnd.google-apps.folder",
                "web_view_link": f.get("webViewLink"),
                "thumbnail_link": f.get("thumbnailLink")
            } for f in files]
    
    def save_tokens(self, user_id: str, token_data: Dict, email: Optional[str] = None):
        try:
            from uuid import UUID
            
            # Convert user_id string to UUID
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid user_id format: {user_id}")
            
            expires_in = token_data.get("expires_in", 3600)
            
            existing = self.db.query(GoogleDriveToken).filter(
                GoogleDriveToken.user_id == user_uuid
            ).first()
            
            if existing:
                existing.access_token = token_data["access_token"]
                existing.refresh_token = token_data.get("refresh_token", existing.refresh_token)
                existing.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                existing.google_email = email or existing.google_email
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
            else:
                token = GoogleDriveToken(
                    user_id=user_uuid,
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                    google_email=email
                )
                self.db.add(token)
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error saving tokens: {str(e)}")
