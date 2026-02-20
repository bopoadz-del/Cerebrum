"""Google Drive service using unified IntegrationToken model."""
import json
import base64
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.core.config import settings
from app.models.integration import IntegrationToken, IntegrationProvider

class GoogleDriveService:
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    def get_auth_url(self, state: str) -> str:
        from google_auth_oauthlib.flow import Flow
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
        flow = Flow.from_client_config(client_config, scopes=self.SCOPES, redirect_uri=self.redirect_uri)
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        return auth_url
    
    def exchange_code(self, code: str) -> Dict[str, Any]:
        import requests
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            }
        )
        response.raise_for_status()
        return response.json()
    
    def save_tokens(self, user_id: uuid.UUID, token_data: Dict[str, Any], org_id: Optional[uuid.UUID] = None):
        existing = self.db.query(IntegrationToken).filter(
            IntegrationToken.user_id == user_id,
            IntegrationToken.provider == IntegrationProvider.GOOGLE_DRIVE
        ).first()
        
        expires_at = datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
        
        if existing:
            existing.access_token = token_data['access_token']
            existing.refresh_token = token_data.get('refresh_token')
            existing.token_type = token_data.get('token_type', 'Bearer')
            existing.expires_at = expires_at
            existing.scope = token_data.get('scope', '')
            existing.is_active = True
        else:
            token = IntegrationToken(
                user_id=user_id,
                org_id=org_id,
                provider=IntegrationProvider.GOOGLE_DRIVE,
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_type=token_data.get('token_type', 'Bearer'),
                expires_at=expires_at,
                scope=token_data.get('scope', ''),
                is_active=True
            )
            self.db.add(token)
        
        self.db.commit()
    
    def get_credentials(self, user_id: uuid.UUID) -> Optional[Credentials]:
        token = self.db.query(IntegrationToken).filter(
            IntegrationToken.user_id == user_id,
            IntegrationToken.provider == IntegrationProvider.GOOGLE_DRIVE,
            IntegrationToken.is_active == True
        ).first()
        
        if not token:
            return None
        
        creds = Credentials(
            token=token.access_token,
            refresh_token=token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES
        )
        
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                token.access_token = creds.token
                self.db.commit()
            except Exception:
                return None
        return creds
    
    def list_files(self, user_id: uuid.UUID, page_size: int = 10):
        creds = self.get_credentials(user_id)
        if not creds:
            raise ValueError("Not authenticated")
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        results = service.files().list(
            pageSize=page_size,
            fields="files(id, name, mimeType, modifiedTime, size)",
            q="trashed=false",
            orderBy="modifiedTime desc"
        ).execute()
        return results.get('files', [])

