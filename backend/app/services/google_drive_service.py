"""
Google Drive Service
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.integration import IntegrationToken

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
    
    async def get_valid_token(self, user_id: uuid.UUID) -> str:
        token = self.db.query(IntegrationToken).filter(
            IntegrationToken.user_id == user_id,
            IntegrationToken.service == "google_drive",
            IntegrationToken.is_active == True
        ).first()
        
        if not token:
            raise HTTPException(status_code=401, detail="Google Drive not connected. Please authenticate first.")
        
        # Check if token is expired and needs refresh
        if token.expiry and token.expiry < datetime.utcnow():
            if token.refresh_token:
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
                    token.expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
                    self.db.commit()
            else:
                raise HTTPException(status_code=401, detail="Token expired and no refresh token available.")
        
        return token.access_token
    
    async def list_files(self, user_id: uuid.UUID, folder_id: Optional[str] = None) -> List[Dict]:
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
    
    def save_tokens(self, user_id: uuid.UUID, token_data: Dict, email: Optional[str] = None):
        """Save tokens to integration_tokens table"""
        try:
            expires_in = token_data.get("expires_in", 3600)
            
            # Check for existing token
            existing = self.db.query(IntegrationToken).filter(
                IntegrationToken.user_id == user_id,
                IntegrationToken.service == "google_drive"
            ).first()
            
            if existing:
                existing.access_token = token_data["access_token"]
                existing.refresh_token = token_data.get("refresh_token", existing.refresh_token)
                existing.expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                existing.is_active = True
            else:
                # Create new token
                token = IntegrationToken(
                    token_id=str(uuid.uuid4()),
                    user_id=user_id,
                    service="google_drive",
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_uri="https://oauth2.googleapis.com/token",
                    scopes=token_data.get("scope", ""),
                    expiry=datetime.utcnow() + timedelta(seconds=expires_in),
                    is_active=True
                )
                self.db.add(token)
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error saving tokens: {str(e)}")
