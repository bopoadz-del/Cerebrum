"""
Microsoft 365 Integration Module
Handles Teams, Outlook, SharePoint, and OneDrive integration.
"""
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.database import Base


MICROSOFT_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class Microsoft365Connection(Base):
    """Microsoft 365 connection record."""
    __tablename__ = 'microsoft_365_connections'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'))
    
    organization_id = Column(String(255), nullable=False)  # Azure AD tenant ID
    organization_name = Column(String(255))
    
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    
    scopes = Column(JSONB, default=list)
    
    is_active = Column(Boolean, default=True)
    connected_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    connected_at = Column(DateTime, default=datetime.utcnow)
    
    last_sync_at = Column(DateTime)
    
    settings = Column(JSONB, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Models

class TeamsMeetingRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    attendees: List[str] = []  # Email addresses


class TeamsMeetingResponse(BaseModel):
    id: str
    join_url: str
    start_time: datetime
    end_time: datetime


class SharePointFolderRequest(BaseModel):
    folder_name: str
    parent_folder_id: Optional[str] = None


class OutlookEventRequest(BaseModel):
    subject: str
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    body: Optional[str] = None


class Microsoft365Service:
    """Service for Microsoft 365 integration."""
    
    SCOPES = [
        "https://graph.microsoft.com/Calendars.ReadWrite",
        "https://graph.microsoft.com/Chat.ReadWrite",
        "https://graph.microsoft.com/Files.ReadWrite",
        "https://graph.microsoft.com/Group.ReadWrite.All",
        "https://graph.microsoft.com/Mail.ReadWrite",
        "https://graph.microsoft.com/OnlineMeetings.ReadWrite",
        "https://graph.microsoft.com/Sites.ReadWrite.All",
        "https://graph.microsoft.com/TeamMember.ReadWrite.All",
        "https://graph.microsoft.com/TeamsActivity.Send",
        "https://graph.microsoft.com/User.Read"
    ]
    
    def __init__(self, db_session, client_id: str, client_secret: str):
        self.db = db_session
        self.client_id = client_id
        self.client_secret = client_secret
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def _refresh_token(self, connection: Microsoft365Connection) -> str:
        """Refresh access token."""
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": connection.refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        connection.access_token = token_data["access_token"]
        connection.token_expires_at = datetime.utcnow().timestamp() + token_data["expires_in"]
        
        if "refresh_token" in token_data:
            connection.refresh_token = token_data["refresh_token"]
        
        self.db.commit()
        
        return connection.access_token
    
    def _make_request(
        self,
        connection: Microsoft365Connection,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Microsoft Graph API."""
        # Check token expiration
        if datetime.utcnow() >= connection.token_expires_at:
            access_token = self._refresh_token(connection)
        else:
            access_token = connection.access_token
        
        url = f"{MICROSOFT_GRAPH_BASE_URL}{endpoint}"
        headers = self._get_headers(access_token)
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json() if response.content else {}
    
    def create_teams_meeting(
        self,
        connection: Microsoft365Connection,
        request: TeamsMeetingRequest
    ) -> TeamsMeetingResponse:
        """Create a Teams meeting."""
        endpoint = "/me/onlineMeetings"
        
        data = {
            "startDateTime": request.start_time.isoformat(),
            "endDateTime": request.end_time.isoformat(),
            "subject": request.title
        }
        
        if request.description:
            data["description"] = request.description
        
        if request.attendees:
            data["participants"] = {
                "attendees": [{"emailAddress": {"address": email}} for email in request.attendees]
            }
        
        result = self._make_request(connection, "POST", endpoint, data)
        
        return TeamsMeetingResponse(
            id=result.get("id"),
            join_url=result.get("joinUrl"),
            start_time=request.start_time,
            end_time=request.end_time
        )
    
    def send_teams_message(
        self,
        connection: Microsoft365Connection,
        channel_id: str,
        message: str
    ) -> Dict[str, Any]:
        """Send a message to a Teams channel."""
        endpoint = f"/teams/{connection.settings.get('team_id')}/channels/{channel_id}/messages"
        
        data = {
            "body": {
                "contentType": "html",
                "content": message
            }
        }
        
        return self._make_request(connection, "POST", endpoint, data)
    
    def create_sharepoint_folder(
        self,
        connection: Microsoft365Connection,
        request: SharePointFolderRequest
    ) -> Dict[str, Any]:
        """Create a SharePoint folder."""
        site_id = connection.settings.get("site_id")
        drive_id = connection.settings.get("drive_id")
        
        if request.parent_folder_id:
            endpoint = f"/sites/{site_id}/drives/{drive_id}/items/{request.parent_folder_id}/children"
        else:
            endpoint = f"/sites/{site_id}/drives/{drive_id}/root/children"
        
        data = {
            "name": request.folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename"
        }
        
        return self._make_request(connection, "POST", endpoint, data)
    
    def upload_sharepoint_file(
        self,
        connection: Microsoft365Connection,
        folder_id: str,
        file_name: str,
        file_content: bytes
    ) -> Dict[str, Any]:
        """Upload a file to SharePoint."""
        site_id = connection.settings.get("site_id")
        drive_id = connection.settings.get("drive_id")
        
        endpoint = f"/sites/{site_id}/drives/{drive_id}/items/{folder_id}:/{file_name}:/content"
        
        access_token = connection.access_token
        if datetime.utcnow() >= connection.token_expires_at:
            access_token = self._refresh_token(connection)
        
        url = f"{MICROSOFT_GRAPH_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream"
        }
        
        response = requests.put(url, headers=headers, data=file_content)
        response.raise_for_status()
        return response.json()
    
    def create_outlook_event(
        self,
        connection: Microsoft365Connection,
        request: OutlookEventRequest
    ) -> Dict[str, Any]:
        """Create an Outlook calendar event."""
        endpoint = "/me/events"
        
        data = {
            "subject": request.subject,
            "start": {
                "dateTime": request.start_time.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": request.end_time.isoformat(),
                "timeZone": "UTC"
            }
        }
        
        if request.attendees:
            data["attendees"] = [{"emailAddress": {"address": email}} for email in request.attendees]
        
        if request.location:
            data["location"] = {"displayName": request.location}
        
        if request.body:
            data["body"] = {"contentType": "HTML", "content": request.body}
        
        return self._make_request(connection, "POST", endpoint, data)
    
    def get_user_profile(
        self,
        connection: Microsoft365Connection
    ) -> Dict[str, Any]:
        """Get connected user's profile."""
        return self._make_request(connection, "GET", "/me")
    
    def get_teams_channels(
        self,
        connection: Microsoft365Connection
    ) -> List[Dict[str, Any]]:
        """Get Teams channels."""
        team_id = connection.settings.get("team_id")
        endpoint = f"/teams/{team_id}/channels"
        
        result = self._make_request(connection, "GET", endpoint)
        return result.get("value", [])
    
    def sync_project_to_teams(
        self,
        connection: Microsoft365Connection,
        project_id: str,
        project_name: str
    ) -> Dict[str, Any]:
        """Create Teams channel for a project."""
        team_id = connection.settings.get("team_id")
        endpoint = f"/teams/{team_id}/channels"
        
        data = {
            "displayName": project_name[:50],  # Teams limit
            "description": f"Project channel for {project_name}",
            "membershipType": "standard"
        }
        
        return self._make_request(connection, "POST", endpoint, data)
    
    def send_project_notification(
        self,
        connection: Microsoft365Connection,
        channel_id: str,
        notification_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send project notification to Teams."""
        # Format message based on notification type
        if notification_type == "task_assigned":
            message = f"""
            <h3>New Task Assigned</h3>
            <p><b>Task:</b> {data.get('task_title')}</p>
            <p><b>Assigned to:</b> {data.get('assignee_name')}</p>
            <p><b>Due:</b> {data.get('due_date')}</p>
            """
        elif notification_type == "rfi_created":
            message = f"""
            <h3>New RFI Submitted</h3>
            <p><b>Subject:</b> {data.get('rfi_subject')}</p>
            <p><b>From:</b> {data.get('submitter_name')}</p>
            """
        else:
            message = f"<p>{data.get('message', 'New notification')}</p>"
        
        return self.send_teams_message(connection, channel_id, message)
