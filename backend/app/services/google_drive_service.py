"""
Google Drive Service - Unified Integration

Provides OAuth2 authentication and file operations for Google Drive.
Uses IntegrationToken model for token storage.
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, BinaryIO, Tuple
from pathlib import Path

import httpx
import anyio
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.models.integration import IntegrationToken, IntegrationProvider


class GoogleDriveError(Exception):
    """Base exception for Google Drive operations."""
    pass


class GoogleDriveAuthError(GoogleDriveError):
    """Authentication-related errors."""
    pass


class GoogleDriveNotFoundError(GoogleDriveError):
    """File/folder not found errors."""
    pass


class GoogleDriveQuotaError(GoogleDriveError):
    """Quota exceeded errors."""
    pass


class GoogleDriveService:
    """
    Google Drive service for OAuth and file operations.
    
    Uses synchronous SQLAlchemy sessions for database operations
    and async methods for I/O-bound Google API calls.
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    # Mime type mappings
    MIME_TYPES = {
        'folder': 'application/vnd.google-apps.folder',
        'document': 'application/vnd.google-apps.document',
        'spreadsheet': 'application/vnd.google-apps.spreadsheet',
        'presentation': 'application/vnd.google-apps.presentation',
        'pdf': 'application/pdf',
        'text': 'text/plain',
        'markdown': 'text/markdown',
    }
    
    def __init__(self, db: Session):
        """
        Initialize service with a synchronous database session.
        
        Args:
            db: SQLAlchemy synchronous session
        """
        self.db = db
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self._logger = self._get_logger()
    
    def _get_logger(self):
        import logging
        return logging.getLogger(__name__)
    
    # =========================================================================
    # OAuth Authentication
    # =========================================================================
    
    def get_auth_url(self, state: str) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: CSRF state token (should include user_id)
            
        Returns:
            Authorization URL for redirect
        """
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
        
        flow = Flow.from_client_config(
            client_config, 
            scopes=self.SCOPES, 
            redirect_uri=self.redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        return auth_url
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Google callback
            
        Returns:
            Token data including access_token, refresh_token, expires_in
        """
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
    
    async def refresh_access_token(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Refresh expired access token using refresh token.
        
        Args:
            user_id: User UUID
            
        Returns:
            New token data or None if refresh fails
        """
        try:
            # Get refresh token from database
            result = self.db.execute(
                text("""
                    SELECT refresh_token, client_id, client_secret, is_active
                    FROM integration_tokens 
                    WHERE user_id = :user_id 
                    AND service = 'google_drive'
                    LIMIT 1
                """),
                {"user_id": str(user_id)}
            )
            row = result.fetchone()
            
            # Debug logging
            if not row:
                self._logger.error(f"No token row found for user {user_id}")
                return None
            
            refresh_token, client_id, client_secret, is_active = row
            self._logger.info(f"Token query for {user_id}: refresh_token={'PRESENT' if refresh_token else 'MISSING'}, is_active={is_active}")
            
            if not refresh_token:  # No refresh token
                self._logger.error(f"Refresh token is empty/None for user {user_id}")
                return None
            
            # Warn if token is inactive but still try to refresh
            if not is_active:
                self._logger.warning(f"Token is not active for user {user_id}, but attempting refresh anyway")
            
            self._logger.info(f"Refreshing token for user {user_id} using client_id={client_id or self.client_id}...")
            
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "refresh_token": refresh_token,
                        "client_id": client_id or self.client_id,
                        "client_secret": client_secret or self.client_secret,
                        "grant_type": "refresh_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                
                if resp.status_code != 200:
                    error_text = resp.text
                    self._logger.error(f"Token refresh failed: HTTP {resp.status_code} - {error_text}")
                    # Log the request details (without sensitive data)
                    self._logger.error(f"Refresh request: client_id={client_id or self.client_id}, client_secret={'*' * 10 if (client_secret or self.client_secret) else 'MISSING'}")
                    return None
                
                token_data = resp.json()
                
                # Update token in database - also reactivate if it was inactive
                expires_in = int(token_data.get('expires_in', 3600) or 3600)
                new_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                
                self.db.execute(
                    text("""
                        UPDATE integration_tokens 
                        SET access_token = :access_token,
                            expiry = :expiry,
                            is_active = true,
                            updated_at = NOW()
                        WHERE user_id = :user_id 
                        AND service = 'google_drive'
                    """),
                    {
                        "access_token": token_data['access_token'],
                        "expiry": new_expiry,
                        "user_id": str(user_id)
                    }
                )
                self.db.commit()
                
                self._logger.info(f"Token refreshed and reactivated for user {user_id}")
                return token_data
                
        except Exception as e:
            self._logger.error(f"Exception during token refresh for user {user_id}: {e}", exc_info=True)
            return None
    
    def save_tokens(
        self, 
        user_id: uuid.UUID, 
        token_data: Dict[str, Any], 
        account_email: Optional[str] = None
    ) -> IntegrationToken:
        """
        Save or update OAuth tokens in database.
        
        Args:
            user_id: User UUID
            token_data: OAuth token response from Google
            account_email: Optional Google account email
            
        Returns:
            IntegrationToken instance
        """
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
            # refresh_token only comes on first auth; NEVER erase existing refresh_token
            new_refresh = token_data.get('refresh_token')
            if new_refresh:
                existing.refresh_token = new_refresh
                self._logger.info(f"Updated refresh_token for user {user_id}")
            elif not existing.refresh_token:
                self._logger.warning(f"No refresh_token available for user {user_id} - re-auth with prompt='consent' needed")
            # else: keep existing refresh_token (don't change it)
            existing.scopes = scopes
            existing.expiry = expiry
            existing.client_id = self.client_id
            existing.client_secret = self.client_secret
            existing.is_active = True
            existing.revoked_at = None
            existing.rotation_count = (existing.rotation_count or 0) + 1
            if account_email:
                existing.account_email = account_email
            self.db.commit()
            return existing
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
            self.db.refresh(token)
            return token
    
    def get_credentials(self, user_id: uuid.UUID) -> Optional[Credentials]:
        """
        Get Google Credentials for user.
        NOTE: This does NOT auto-refresh. Callers must handle refresh separately
        or use PermanentGoogleDrive which auto-refreshes.
        """
        try:
            from app.models.integration import IntegrationToken
            from sqlalchemy import text
            
            # Use raw query to check what's in the database
            result = self.db.execute(
                text("""
                    SELECT access_token, refresh_token, expiry, is_active
                    FROM integration_tokens
                    WHERE user_id = :user_id
                    AND service = 'google_drive'
                    LIMIT 1
                """),
                {"user_id": str(user_id)}
            )
            row = result.fetchone()
            
            if not row:
                self._logger.warning(f"No token row found for user {user_id}")
                return None
            
            access_token, refresh_token, expiry, is_active = row
            self._logger.info(f"Token status for {user_id}: access={'YES' if access_token else 'NO'}, refresh={'YES' if refresh_token else 'NO'}, active={is_active}")
            
            if not access_token:
                self._logger.warning(f"No access token for user {user_id}")
                return None
            
            # For ORM compatibility - use the row data directly instead of re-querying
            from app.models.integration import IntegrationToken, IntegrationProvider
            
            # Create a mock token object from the row data
            class MockToken:
                pass
            
            tok = MockToken()
            tok.access_token = access_token
            tok.refresh_token = refresh_token
            tok.expiry = expiry
            tok.is_active = is_active
            tok.token_uri = 'https://oauth2.googleapis.com/token'
            tok.client_id = None
            tok.client_secret = None
            
            # If not active, still try to use it but log a warning
            if not is_active:
                self._logger.warning(f"Token for user {user_id} is inactive but attempting to use anyway")
            
            from google.oauth2.credentials import Credentials
            
            # Check expiry - log warning if expired but still return credentials
            # (caller should refresh before using)
            if tok.expiry:
                from datetime import datetime, timezone, timedelta
                now = datetime.now(timezone.utc)
                expires = tok.expiry if tok.expiry.tzinfo else tok.expiry.replace(tzinfo=timezone.utc)
                if now >= (expires - timedelta(minutes=5)):
                    self._logger.warning(f"Token EXPIRED for user {user_id} - refresh needed before use")
                    # Still return credentials - caller should refresh
            
            # Build credentials from token data
            creds = Credentials(
                token=tok.access_token,
                refresh_token=tok.refresh_token,
                token_uri=tok.token_uri or "https://oauth2.googleapis.com/token",
                client_id=tok.client_id or self.client_id,
                client_secret=tok.client_secret or self.client_secret,
                scopes=['https://www.googleapis.com/auth/drive.readonly', 
                       'https://www.googleapis.com/auth/drive.file',
                       'https://www.googleapis.com/auth/drive.metadata.readonly']
            )
            
            return creds
            
        except Exception as e:
            self._logger.error(f"Error getting credentials: {e}", exc_info=True)
            return None

    def get_status(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get Google Drive connection status for user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Status dict with connected, email, last_sync, etc.
        """
        try:
            result = self.db.execute(
                text("""
                    SELECT account_email, is_active, expiry, updated_at, 
                           refresh_token, access_token
                    FROM integration_tokens 
                    WHERE user_id = :user_id 
                    AND service = 'google_drive'
                    LIMIT 1
                """),
                {"user_id": str(user_id)}
            )
            row = result.fetchone()
            
            if not row:
                return {
                    "connected": False,
                    "email": None,
                    "last_sync": None,
                    "can_refresh": False,
                    "expires_soon": False
                }
            
            account_email, is_active, expiry, updated_at, refresh_token, access_token = row
            
            # Check if token expires soon (within 10 minutes)
            expires_soon = False
            if expiry:
                from datetime import timezone
                # Handle both offset-naive and offset-aware datetimes
                now = datetime.utcnow().replace(tzinfo=timezone.utc) if expiry.tzinfo else datetime.utcnow()
                expires = expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo else expiry
                expires_soon = now >= (expires - timedelta(minutes=10))
            
            return {
                "connected": is_active and bool(access_token),
                "email": account_email,
                "last_sync": updated_at.isoformat() if updated_at else None,
                "can_refresh": bool(refresh_token),
                "expires_soon": expires_soon,
                "expiry": expiry.isoformat() if expiry else None
            }
        except Exception as e:
            self._logger.error(f"Error getting status: {e}", exc_info=True)
            return {
                "connected": False,
                "email": None,
                "last_sync": None,
                "error": str(e)
            }
    
    def disconnect(self, user_id: uuid.UUID) -> bool:
        """
        Revoke Google Drive connection for user.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if disconnected successfully
        """
        try:
            self.db.execute(
                text("""
                    UPDATE integration_tokens 
                    SET is_active = false,
                        revoked_at = NOW(),
                        access_token = NULL
                    WHERE user_id = :user_id 
                    AND service = 'google_drive'
                """),
                {"user_id": str(user_id)}
            )
            self.db.commit()
            return True
        except Exception as e:
            self._logger.error(f"Error disconnecting: {e}", exc_info=True)
            self.db.rollback()
            return False
    
    # =========================================================================
    # File Operations
    # =========================================================================
    
    async def list_files(
        self, 
        user_id: uuid.UUID, 
        folder_id: Optional[str] = None, 
        page_size: int = 50,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List files from Google Drive.
        
        Args:
            user_id: User UUID
            folder_id: Optional parent folder ID
            page_size: Max results (max 1000)
            query: Additional query filter
            
        Returns:
            List of file metadata dicts
        """
        def _run():
            try:
                creds = self.get_credentials(user_id)
            except GoogleDriveAuthError:
                raise
            except Exception as e:
                self._logger.error(f"Unexpected error getting credentials: {e}")
                raise GoogleDriveAuthError(f"Authentication error: {str(e)}")
            
            if creds is None:
                raise GoogleDriveAuthError("No Google Drive credentials found for user")
            
            try:
                svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
            except Exception as e:
                raise GoogleDriveError(f"Failed to initialize Drive service: {e}")
            
            # Build query
            q_parts = ["trashed=false"]
            if folder_id:
                q_parts.append(f"'{folder_id}' in parents")
            if query:
                q_parts.append(query)
            
            q = " and ".join(q_parts)
            
            try:
                files = []
                page_token = None
                remaining = page_size
                
                while remaining > 0:
                    results = svc.files().list(
                        pageSize=min(1000, remaining),
                        fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, webViewLink, createdTime, description)",
                        q=q,
                        orderBy="modifiedTime desc",
                        pageToken=page_token
                    ).execute()
                    batch = results.get("files", [])
                    files.extend(batch)
                    remaining -= len(batch)
                    page_token = results.get("nextPageToken")
                    if not page_token:
                        break
                
            except HttpError as e:
                error_code = e.resp.status if hasattr(e, 'resp') else 0
                error_details = e._get_reason() if hasattr(e, '_get_reason') else str(e)
                
                if error_code == 401:
                    raise GoogleDriveAuthError("Authentication expired. Please reconnect.")
                elif error_code == 404:
                    raise GoogleDriveNotFoundError(f"Folder not found: {folder_id}")
                elif error_code == 403:
                    raise GoogleDriveError("Access denied. Check permissions.")
                else:
                    raise GoogleDriveError(f"Drive API error ({error_code}): {error_details}")
            
            # Format output
            out = []
            for f in files:
                mt = f.get("mimeType", "")
                out.append({
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "mime_type": mt,
                    "size": int(f["size"]) if f.get("size") else None,
                    "modified_time": f.get("modifiedTime"),
                    "created_time": f.get("createdTime"),
                    "is_folder": mt == self.MIME_TYPES['folder'],
                    "is_google_doc": mt.startswith("application/vnd.google-apps."),
                    "web_view_link": f.get("webViewLink"),
                    "description": f.get("description"),
                })
            return out
        
        return await anyio.to_thread.run_sync(_run)
    
    async def get_file(self, user_id: uuid.UUID, file_id: str) -> Dict[str, Any]:
        """
        Get detailed file metadata.
        
        Args:
            user_id: User UUID
            file_id: Google Drive file ID
            
        Returns:
            File metadata dict
        """
        def _run():
            creds = self.get_credentials(user_id)
            if not creds:
                raise GoogleDriveAuthError("Not authenticated")
            
            svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
            
            try:
                file = svc.files().get(
                    fileId=file_id,
                    fields="id, name, mimeType, size, modifiedTime, createdTime, webViewLink, description, parents, shared"
                ).execute()
                
                mt = file.get("mimeType", "")
                return {
                    "id": file.get("id"),
                    "name": file.get("name"),
                    "mime_type": mt,
                    "size": int(file["size"]) if file.get("size") else None,
                    "modified_time": file.get("modifiedTime"),
                    "created_time": file.get("createdTime"),
                    "web_view_link": file.get("webViewLink"),
                    "description": file.get("description"),
                    "parents": file.get("parents", []),
                    "shared": file.get("shared", False),
                    "is_folder": mt == self.MIME_TYPES['folder'],
                    "is_google_doc": mt.startswith("application/vnd.google-apps."),
                }
            except HttpError as e:
                if e.resp.status == 404:
                    raise GoogleDriveNotFoundError(f"File not found: {file_id}")
                raise GoogleDriveError(f"Failed to get file: {e}")
        
        return await anyio.to_thread.run_sync(_run)
    
    async def download_file(
        self, 
        user_id: uuid.UUID, 
        file_id: str,
        export_format: Optional[str] = None
    ) -> Tuple[bytes, str, str]:
        """
        Download file content from Google Drive.
        
        For Google Workspace files (Docs, Sheets, etc.), exports to specified format.
        For binary files, downloads raw content.
        
        Args:
            user_id: User UUID
            file_id: Google Drive file ID
            export_format: Export format for Google Docs (pdf, txt, etc.)
            
        Returns:
            Tuple of (file_bytes, filename, mime_type)
        """
        def _run():
            creds = self.get_credentials(user_id)
            if not creds:
                raise GoogleDriveAuthError("Not authenticated")
            
            svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
            
            # Get file metadata first
            try:
                file_meta = svc.files().get(fileId=file_id).execute()
            except HttpError as e:
                if e.resp.status == 404:
                    raise GoogleDriveNotFoundError(f"File not found: {file_id}")
                raise
            
            filename = file_meta.get("name", "unnamed")
            mime_type = file_meta.get("mimeType", "application/octet-stream")
            
            # Handle Google Workspace files (export)
            if mime_type.startswith("application/vnd.google-apps."):
                export_mimes = {
                    'application/vnd.google-apps.document': 
                        export_format or 'application/pdf',
                    'application/vnd.google-apps.spreadsheet': 
                        export_format or 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/vnd.google-apps.presentation': 
                        export_format or 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                }
                
                export_mime = export_mimes.get(mime_type, 'application/pdf')
                
                try:
                    request = svc.files().export_media(fileId=file_id, mimeType=export_mime)
                except Exception as e:
                    raise GoogleDriveError(f"Cannot export this file type: {e}")
            else:
                # Binary download
                request = svc.files().get_media(fileId=file_id)
            
            # Download content
            from io import BytesIO
            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                try:
                    status, done = downloader.next_chunk()
                except HttpError as e:
                    if e.resp.status == 403:
                        raise GoogleDriveQuotaError("Download quota exceeded")
                    raise
            
            fh.seek(0)
            return fh.read(), filename, mime_type
        
        return await anyio.to_thread.run_sync(_run)
    
    async def download_file_to_path(
        self, 
        user_id: uuid.UUID, 
        file_id: str,
        output_path: Path,
        export_format: Optional[str] = None
    ) -> Path:
        """
        Download file to local filesystem.
        
        Args:
            user_id: User UUID
            file_id: Google Drive file ID
            output_path: Where to save the file
            export_format: Export format for Google Docs
            
        Returns:
            Path to saved file
        """
        content, filename, _ = await self.download_file(user_id, file_id, export_format)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(content)
        
        return output_path
    
    async def create_folder(
        self, 
        user_id: uuid.UUID, 
        name: str, 
        parent_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a new folder in Google Drive.
        
        Args:
            user_id: User UUID
            name: Folder name
            parent_id: Optional parent folder ID
            
        Returns:
            Dict with id and name of created folder
        """
        def _run():
            creds = self.get_credentials(user_id)
            if not creds:
                raise GoogleDriveAuthError("Not authenticated")
            
            svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
            
            metadata = {
                'name': name,
                'mimeType': self.MIME_TYPES['folder'],
            }
            if parent_id:
                metadata['parents'] = [parent_id]
            
            try:
                folder = svc.files().create(body=metadata, fields='id, name').execute()
                return {
                    "id": folder.get("id"),
                    "name": folder.get("name")
                }
            except HttpError as e:
                raise GoogleDriveError(f"Failed to create folder: {e}")
        
        return await anyio.to_thread.run_sync(_run)
    
    async def upload_file(
        self,
        user_id: uuid.UUID,
        name: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
        parent_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Upload a file to Google Drive.
        
        Args:
            user_id: User UUID
            name: File name
            content: File bytes
            mime_type: Content type
            parent_id: Optional parent folder ID
            
        Returns:
            Dict with id and name of uploaded file
        """
        def _run():
            creds = self.get_credentials(user_id)
            if not creds:
                raise GoogleDriveAuthError("Not authenticated")
            
            svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
            
            from io import BytesIO
            file_metadata = {'name': name}
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            media = MediaIoBaseUpload(
                BytesIO(content),
                mimetype=mime_type,
                resumable=True
            )
            
            try:
                file = svc.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, mimeType, size, webViewLink'
                ).execute()
                
                return {
                    "id": file.get("id"),
                    "name": file.get("name"),
                    "mime_type": file.get("mimeType"),
                    "size": file.get("size"),
                    "web_view_link": file.get("webViewLink")
                }
            except HttpError as e:
                raise GoogleDriveError(f"Failed to upload file: {e}")
        
        return await anyio.to_thread.run_sync(_run)
    
    async def delete_file(self, user_id: uuid.UUID, file_id: str, permanent: bool = False) -> bool:
        """
        Delete or trash a file.
        
        Args:
            user_id: User UUID
            file_id: File ID to delete
            permanent: If True, permanently delete; otherwise move to trash
            
        Returns:
            True if successful
        """
        def _run():
            creds = self.get_credentials(user_id)
            if not creds:
                raise GoogleDriveAuthError("Not authenticated")
            
            svc = build('drive', 'v3', credentials=creds, cache_discovery=False)
            
            try:
                if permanent:
                    svc.files().delete(fileId=file_id).execute()
                else:
                    svc.files().update(
                        fileId=file_id, 
                        body={'trashed': True}
                    ).execute()
                return True
            except HttpError as e:
                if e.resp.status == 404:
                    raise GoogleDriveNotFoundError(f"File not found: {file_id}")
                raise GoogleDriveError(f"Failed to delete file: {e}")
        
        return await anyio.to_thread.run_sync(_run)
    
    async def search_files(
        self, 
        user_id: uuid.UUID, 
        query: str,
        file_type: Optional[str] = None,
        page_size: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search files in Google Drive.
        
        Args:
            user_id: User UUID
            query: Search query (name contains)
            file_type: Optional mime type filter
            page_size: Max results
            
        Returns:
            List of matching file metadata
        """
        # Build search query
        escaped_query = query.replace("'", "\\'")
        q_parts = [f"name contains '{escaped_query}'", "trashed=false"]
        
        if file_type:
            if file_type == 'folder':
                q_parts.append(f"mimeType='{self.MIME_TYPES['folder']}'")
            elif file_type == 'document':
                q_parts.append(f"mimeType='{self.MIME_TYPES['document']}'")
            elif file_type == 'spreadsheet':
                q_parts.append(f"mimeType='{self.MIME_TYPES['spreadsheet']}'")
            elif file_type == 'pdf':
                q_parts.append(f"mimeType='{self.MIME_TYPES['pdf']}'")
        
        search_q = " and ".join(q_parts)
        return await self.list_files(user_id, query=search_q, page_size=page_size)
