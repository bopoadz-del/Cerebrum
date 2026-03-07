"""
PERMANENT Google Drive connection - never expires
Uses refresh token automatically before every operation
"""
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.services.google_drive_service import (
    GoogleDriveService,
    GoogleDriveAuthError,
    GoogleDriveError,
    GoogleDriveNotFoundError
)


class PermanentGoogleDrive:
    """Google Drive that never loses connection - auto-refreshes tokens."""
    
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.service = GoogleDriveService(db)
        self.user_id = user_id
    
    async def ensure_fresh_token(self) -> bool:
        """
        Always refresh before using if possible.
        Returns True if we have valid credentials (fresh or refreshed).
        """
        try:
            # First check if current token is still good
            creds = self.service.get_credentials(self.user_id)
            if creds:
                self.service._logger.debug(f"Token still valid for user {self.user_id}")
                return True
            
            # Token expired or not found - try to refresh
            self.service._logger.info(f"Token expired or missing for user {self.user_id}, attempting refresh...")
            token_data = await self.service.refresh_access_token(self.user_id)
            if token_data:
                self.service._logger.info(f"Token refreshed successfully for user {self.user_id}")
                return True
            
            # Refresh failed - no refresh token or refresh failed
            self.service._logger.error(f"Token refresh failed for user {self.user_id} - no refresh token or invalid grant")
            return False
        except Exception as e:
            self.service._logger.error(f"Error in ensure_fresh_token for user {self.user_id}: {e}", exc_info=True)
            return False
    
    async def list_files(
        self, 
        folder_id: Optional[str] = None, 
        page_size: int = 50,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List files with guaranteed fresh token."""
        if not await self.ensure_fresh_token():
            raise GoogleDriveAuthError("No Google Drive credentials found for user")
        return await self.service.list_files(
            self.user_id, 
            folder_id=folder_id, 
            page_size=page_size,
            query=query
        )
    
    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file with fresh token."""
        if not await self.ensure_fresh_token():
            raise GoogleDriveAuthError("Not authenticated")
        return await self.service.get_file(self.user_id, file_id)
    
    async def download_file(self, file_id: str, export_format: Optional[str] = None):
        """Download file with fresh token."""
        if not await self.ensure_fresh_token():
            raise GoogleDriveAuthError("Not authenticated")
        return await self.service.download_file(self.user_id, file_id, export_format)
    
    async def search_files(
        self, 
        query: str,
        file_type: Optional[str] = None,
        page_size: int = 50
    ) -> List[Dict[str, Any]]:
        """Search files with fresh token."""
        if not await self.ensure_fresh_token():
            raise GoogleDriveAuthError("Not authenticated")
        return await self.service.search_files(
            self.user_id,
            query=query,
            file_type=file_type,
            page_size=page_size
        )
    
    async def create_folder(self, name: str, parent_id: Optional[str] = None) -> Dict[str, str]:
        """Create folder with fresh token."""
        if not await self.ensure_fresh_token():
            raise GoogleDriveAuthError("Not authenticated")
        return await self.service.create_folder(self.user_id, name, parent_id)
    
    async def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """Delete file with fresh token."""
        if not await self.ensure_fresh_token():
            raise GoogleDriveAuthError("Not authenticated")
        return await self.service.delete_file(self.user_id, file_id, permanent)
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status."""
        return self.service.get_status(self.user_id)
    
    def get_credentials(self):
        """Get credentials (will auto-refresh on next use)."""
        return self.service.get_credentials(self.user_id)


def get_permanent_drive(db: Session, user_id: uuid.UUID) -> PermanentGoogleDrive:
    """Create a permanent drive connection for a user."""
    return PermanentGoogleDrive(db, user_id)
