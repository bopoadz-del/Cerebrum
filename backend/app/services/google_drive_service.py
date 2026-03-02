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
        import logging
        logger = logging.getLogger(__name__)
        
        try:
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
                logger.info(f"No active Google Drive token found for user {user_id}")
                return None

            access_token, refresh_token, expiry, scopes, token_uri, client_id, client_secret = row
            
            if not access_token:
                logger.error(f"Access token is empty for user {user_id}")
                return None

            creds = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri=token_uri or 'https://oauth2.googleapis.com/token',
                client_id=client_id or self.client_id,
                client_secret=client_secret or self.client_secret,
                scopes=self.SCOPES
            )

            # Check if token needs refresh
            try:
                is_expired = creds.expired if expiry else False
            except Exception as exp_err:
                logger.warning(f"Could not check expiry: {exp_err}")
                is_expired = False

            if is_expired and creds.refresh_token:
                logger.info(f"Token expired for user {user_id}, attempting refresh")
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
                    logger.info(f"Token refreshed successfully for user {user_id}")
                except Exception as refresh_err:
                    logger.error(f"Failed to refresh token for user {user_id}: {refresh_err}")
                    return None
            
            return creds
        except Exception as e:
            logger.error(f"Error getting credentials for user {user_id}: {e}", exc_info=True)
            return None
    
    async def list_files(self, user_id: uuid.UUID, folder_id: Optional[str] = None, page_size: int = 50):
          import logging
          from googleapiclient.errors import HttpError
          logger = logging.getLogger(__name__)
          
          def _run():
              try:
                  creds = self.get_credentials(user_id)
                  if not creds:
                      logger.error(f"No credentials found for user {user_id}")
                      raise ValueError("Not authenticated")
              except Exception as cred_err:
                  logger.error(f"Error getting credentials: {cred_err}")
                  raise ValueError(f"Authentication error: {cred_err}")

              try:
                  svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
              except Exception as build_err:
                  logger.error(f"Error building Drive service: {build_err}")
                  raise ValueError(f"Failed to initialize Google Drive service: {build_err}")

              q = "trashed=false"
              if folder_id:
                  q += f" and '{folder_id}' in parents"
              
              logger.info(f"Querying Google Drive: folder_id={folder_id}, query={q}")

              try:
                  results = svc.files().list(
                      pageSize=page_size,
                      fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
                      q=q,
                      orderBy="modifiedTime desc"
                  ).execute()
                  
                  files = results.get("files", [])
                  logger.info(f"Google Drive returned {len(files)} files for folder {folder_id}")
                  
              except HttpError as e:
                  error_code = e.resp.status if hasattr(e, 'resp') else 'unknown'
                  error_details = e._get_reason() if hasattr(e, '_get_reason') else str(e)
                  logger.error(f"Google Drive HTTP error {error_code}: {error_details}")
                  
                  if error_code == 401 or 'unauthorized' in error_details.lower():
                      raise ValueError("Google Drive authentication expired. Please reconnect.")
                  elif error_code == 404 or 'not found' in error_details.lower():
                      raise ValueError(f"Folder not found in Google Drive: {folder_id}")
                  elif error_code == 403:
                      raise ValueError("Access denied to Google Drive folder. Check permissions.")
                  else:
                      raise ValueError(f"Google Drive API error ({error_code}): {error_details}")
              except Exception as e:
                  logger.error(f"Google Drive API error: {e}", exc_info=True)
                  error_str = str(e).lower()
                  if 'unauthorized' in error_str or 'invalid' in error_str or 'expired' in error_str:
                      raise ValueError("Google Drive authentication expired. Please reconnect.")
                  if 'not found' in error_str:
                      raise ValueError(f"Folder not found in Google Drive: {folder_id}")
                  raise ValueError(f"Google Drive error: {str(e)}")

              out = []
              for f in files:
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
    
