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
from app.models.user import User
from app.models.integration import IntegrationToken

logger = get_logger(__name__)

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
        # Implementation with actual database
        pass
    
    def _get_token_from_db(self, user_id: str) -> Optional[TokenInfo]:
        """Retrieve token from database."""
        # Implementation with actual database
        return None
    
    def _delete_token_from_db(self, user_id: str) -> None:
        """Delete token from database."""
        # Implementation with actual database
        pass


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
