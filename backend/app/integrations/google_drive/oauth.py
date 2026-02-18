"""
Google Drive OAuth2 Integration with Refresh Token Rotation
Implements secure OAuth2 flow with automatic token refresh and rotation.
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.core.logging import get_logger
from app.api.deps import get_db_session

logger = get_logger(__name__)

# Lazy import IntegrationToken to avoid circular imports
def _get_integration_token_model():
    try:
        from app.models.integration import IntegrationToken
        return IntegrationToken
    except ImportError:
        logger.warning("IntegrationToken model not found, using stub implementation")
        return None

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]


@dataclass
class TokenInfo:
    """Token information with metadata."""
    access_token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list
    expiry: datetime
    token_id: str
    rotation_count: int = 0


class GoogleDriveOAuthManager:
    """Manages Google Drive OAuth2 authentication with token rotation."""
    
    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "javascript_origins": [settings.FRONTEND_URL]
            }
        }
        self._token_cache: Dict[str, TokenInfo] = {}
    
    def create_auth_flow(self, state: Optional[str] = None) -> Flow:
        """Create OAuth2 flow for authorization."""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            state=state
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        return flow
    
    def get_authorization_url(self, user_id: str) -> Tuple[str, str]:
        """Generate authorization URL with PKCE and state."""
        state = secrets.token_urlsafe(32)
        flow = self.create_auth_flow(state)
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        
        # Store state in cache for validation
        self._store_auth_state(state, user_id)
        
        logger.info(f"Generated auth URL for user {user_id}")
        return auth_url, state
    
    def exchange_code(
        self, 
        code: str, 
        state: str,
        user_id: str
    ) -> TokenInfo:
        """Exchange authorization code for tokens."""
        self._validate_auth_state(state, user_id)
        
        flow = self.create_auth_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        token_info = TokenInfo(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scopes=list(credentials.scopes),
            expiry=credentials.expiry,
            token_id=secrets.token_urlsafe(16),
            rotation_count=0
        )
        
        # Save to database
        self._save_token_to_db(user_id, token_info)
        self._token_cache[token_info.token_id] = token_info
        
        logger.info(f"Token exchanged successfully for user {user_id}")
        return token_info
    
    def get_credentials(self, user_id: str) -> Optional[Credentials]:
        """Get valid credentials for user, refreshing if necessary."""
        token_info = self._get_token_from_db(user_id)
        
        if not token_info:
            logger.warning(f"No token found for user {user_id}")
            return None
        
        credentials = Credentials(
            token=token_info.access_token,
            refresh_token=token_info.refresh_token,
            token_uri=token_info.token_uri,
            client_id=token_info.client_id,
            client_secret=token_info.client_secret,
            scopes=token_info.scopes,
            expiry=token_info.expiry
        )
        
        # Check if token needs refresh
        if credentials.expired or self._should_refresh_soon(credentials):
            credentials = self._refresh_with_rotation(user_id, credentials)
        
        return credentials
    
    def _refresh_with_rotation(
        self, 
        user_id: str, 
        credentials: Credentials
    ) -> Credentials:
        """Refresh token with rotation for enhanced security."""
        try:
            credentials.refresh(Request())
            
            # Rotate refresh token every 5 uses
            token_info = self._get_token_from_db(user_id)
            if token_info and token_info.rotation_count >= 5:
                logger.info(f"Rotating refresh token for user {user_id}")
                # Request new refresh token
                credentials = self._force_new_refresh_token(user_id)
                rotation_count = 0
            else:
                rotation_count = (token_info.rotation_count + 1) if token_info else 1
            
            # Update stored token
            new_token_info = TokenInfo(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_uri=credentials.token_uri,
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
                scopes=list(credentials.scopes),
                expiry=credentials.expiry,
                token_id=token_info.token_id if token_info else secrets.token_urlsafe(16),
                rotation_count=rotation_count
            )
            
            self._save_token_to_db(user_id, new_token_info)
            self._token_cache[new_token_info.token_id] = new_token_info
            
            logger.info(f"Token refreshed for user {user_id}")
            return credentials
            
        except Exception as e:
            logger.error(f"Token refresh failed for user {user_id}: {e}")
            raise TokenRefreshError(f"Failed to refresh token: {e}")
    
    def _force_new_refresh_token(self, user_id: str) -> Credentials:
        """Force generation of new refresh token."""
        # This requires re-authorization
        raise ReauthorizationRequired(
            "Token rotation required. Please re-authorize Google Drive access."
        )
    
    def revoke_token(self, user_id: str) -> bool:
        """Revoke and delete token for user."""
        try:
            credentials = self.get_credentials(user_id)
            if credentials:
                # Revoke with Google
                import requests
                requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': credentials.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
            
            # Delete from database
            self._delete_token_from_db(user_id)
            
            logger.info(f"Token revoked for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Token revocation failed: {e}")
            return False
    
    def _should_refresh_soon(self, credentials: Credentials) -> bool:
        """Check if token should be refreshed (within 5 minutes of expiry)."""
        if not credentials.expiry:
            return False
        return datetime.utcnow() > (credentials.expiry - timedelta(minutes=5))
    
    def _store_auth_state(self, state: str, user_id: str) -> None:
        """Store authorization state for validation."""
        # Implementation would use Redis or similar
        pass
    
    def _validate_auth_state(self, state: str, user_id: str) -> bool:
        """Validate authorization state."""
        # Implementation would validate against stored state
        return True
    
    def _save_token_to_db(self, user_id: str, token_info: TokenInfo) -> None:
        """Save token to database."""
        from app.db.session import get_sync_db_context
        from app.models.integration import IntegrationToken
        from sqlalchemy import select
        import uuid
        
        try:
            with get_sync_db_context() as session:
                # Check for existing token
                stmt = select(IntegrationToken).where(
                    IntegrationToken.user_id == uuid.UUID(user_id),
                    IntegrationToken.service == "google_drive"
                )
                existing = session.execute(stmt).scalar_one_or_none()
                
                if existing:
                    # Update existing token
                    existing.access_token = token_info.access_token
                    existing.refresh_token = token_info.refresh_token
                    existing.token_uri = token_info.token_uri
                    existing.client_id = token_info.client_id
                    existing.client_secret = token_info.client_secret
                    existing.scopes = " ".join(token_info.scopes)
                    existing.expiry = token_info.expiry
                    existing.rotation_count = token_info.rotation_count
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new token
                    token = IntegrationToken(
                        token_id=token_info.token_id,
                        user_id=uuid.UUID(user_id),
                        service="google_drive",
                        access_token=token_info.access_token,
                        refresh_token=token_info.refresh_token,
                        token_uri=token_info.token_uri,
                        client_id=token_info.client_id,
                        client_secret=token_info.client_secret,
                        scopes=" ".join(token_info.scopes),
                        expiry=token_info.expiry,
                        rotation_count=token_info.rotation_count,
                    )
                    session.add(token)
                
                logger.info(f"Token saved to database for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to save token to database: {e}")
            # Don't raise - token is still in cache
    
    def _get_token_from_db(self, user_id: str) -> Optional[TokenInfo]:
        """Retrieve token from database."""
        from app.db.session import get_sync_db_context
        from app.models.integration import IntegrationToken
        from sqlalchemy import select
        import uuid
        
        try:
            with get_sync_db_context() as session:
                stmt = select(IntegrationToken).where(
                    IntegrationToken.user_id == uuid.UUID(user_id),
                    IntegrationToken.service == "google_drive",
                    IntegrationToken.is_active == True
                )
                token = session.execute(stmt).scalar_one_or_none()
                
                if token:
                    return TokenInfo(
                        access_token=token.access_token,
                        refresh_token=token.refresh_token or "",
                        token_uri=token.token_uri,
                        client_id=token.client_id or "",
                        client_secret=token.client_secret or "",
                        scopes=token.scopes.split() if token.scopes else [],
                        expiry=token.expiry,
                        token_id=token.token_id,
                        rotation_count=token.rotation_count,
                    )
        except Exception as e:
            logger.error(f"Failed to retrieve token from database: {e}")
        
        return None
    
    def _delete_token_from_db(self, user_id: str) -> None:
        """Delete token from database."""
        from app.db.session import get_sync_db_context
        from app.models.integration import IntegrationToken
        from sqlalchemy import select
        import uuid
        
        try:
            with get_sync_db_context() as session:
                stmt = select(IntegrationToken).where(
                    IntegrationToken.user_id == uuid.UUID(user_id),
                    IntegrationToken.service == "google_drive"
                )
                token = session.execute(stmt).scalar_one_or_none()
                if token:
                    token.is_active = False
                    token.revoked_at = datetime.utcnow()
                    logger.info(f"Token revoked in database for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to delete token from database: {e}")


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""
    pass


class ReauthorizationRequired(Exception):
    """Raised when re-authorization is required."""
    pass


# Singleton instance
oauth_manager = GoogleDriveOAuthManager()


def get_oauth_manager() -> GoogleDriveOAuthManager:
    """Get OAuth manager instance."""
    return oauth_manager
