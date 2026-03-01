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
import httpx
import anyio

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
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
          async with httpx.AsyncClient(timeout=30) as client:
              resp = await client.post(
                  "https://oauth2.googleapis.com/token",
                  data={
                      "code": code,
                      "client_id": self.client_id,
                      "client_secret": self.client_secret,
                      "redirect_uri": self.redirect_uri,
                      "grant_type": "authorization_code",
                  },
                  headers={"Content-Type": "application/x-www-form-urlencoded"},
              )
              resp.raise_for_status()
              return resp.json()
    def save_tokens(self, user_id: uuid.UUID, token_data: Dict[str, Any], account_email: str = None):
        """Persist OAuth tokens using IntegrationToken model fields."""
        token_id = token_data.get('token_id') or uuid.uuid4().hex
        existing = self.db.query(IntegrationToken).filter(
            IntegrationToken.user_id == user_id,
            IntegrationToken.service == IntegrationProvider.GOOGLE_DRIVE
        ).first()

        expires_in = int(token_data.get('expires_in', 3600) or 3600)
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        scopes = token_data.get('scope', '') or ''

        if existing:
            existing.access_token = token_data['access_token']
            # refresh_token only comes first time sometimes; don't erase existing
            existing.refresh_token = token_data.get('refresh_token') or existing.refresh_token
            existing.scopes = scopes
            existing.expiry = expiry
            existing.client_id = self.client_id
            existing.client_secret = self.client_secret
            existing.is_active = True
            existing.revoked_at = None
            existing.rotation_count = (existing.rotation_count or 0) + 1
            if account_email:
                existing.account_email = account_email
        else:
            token = IntegrationToken(
                token_id=token_id,
                user_id=user_id,
                service=IntegrationProvider.GOOGLE_DRIVE,
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=scopes,
                expiry=expiry,
                is_active=True,
                account_email=account_email,
            )
            self.db.add(token)

        self.db.commit()

    def get_credentials(self, user_id: uuid.UUID) -> Optional[Credentials]:
        # Use raw query to avoid column mismatch during migrations
        from sqlalchemy import text
        result = self.db.execute(
            text("""
                SELECT access_token, refresh_token, expiry, scopes, token_uri, client_id, client_secret
                FROM integration_tokens 
                WHERE user_id = :user_id 
                AND service = 'google_drive' 
                AND is_active = true
                LIMIT 1
            """),
            {"user_id": str(user_id)}
        )
        row = result.fetchone()

        if not row:
            return None

        access_token, refresh_token, expiry, scopes, token_uri, client_id, client_secret = row

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=token_uri or 'https://oauth2.googleapis.com/token',
            client_id=client_id or self.client_id,
            client_secret=client_secret or self.client_secret,
            scopes=self.SCOPES
        )

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Update token in DB using raw SQL
                self.db.execute(
                    text("""
                        UPDATE integration_tokens 
                        SET access_token = :access_token
                        WHERE user_id = :user_id 
                        AND service = 'google_drive'
                    """),
                    {"access_token": creds.token, "user_id": str(user_id)}
                )
                self.db.commit()
            except Exception:
                return None
        return creds
    
    async def list_files(self, user_id: uuid.UUID, folder_id: Optional[str] = None, page_size: int = 50):
          def _run():
              creds = self.get_credentials(user_id)
              if not creds:
                  raise ValueError("Not authenticated")

              svc = build('drive', 'v3', credentials=creds, cache_discovery=False)

              q = "trashed=false"
              if folder_id:
                  q += f" and '{folder_id}' in parents"

              results = svc.files().list(
                  pageSize=page_size,
                  fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
                  q=q,
                  orderBy="modifiedTime desc"
              ).execute()

              out = []
              for f in results.get("files", []):
                  mt = f.get("mimeType")
                  out.append({
                      "id": f.get("id"),
                      "name": f.get("name"),
                      "mime_type": mt,
                      "size": int(f["size"]) if f.get("size") is not None else None,
                      "modified_time": f.get("modifiedTime"),
                      "is_folder": mt == "application/vnd.google-apps.folder",
                      "web_view_link": f.get("webViewLink"),
                  })
              return out

          return await anyio.to_thread.run_sync(_run)
    
