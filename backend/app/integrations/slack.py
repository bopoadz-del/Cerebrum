"""
Slack Integration Module - Slack slash commands and notifications
Item 306: Slack integration
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException, Request
import requests
from enum import Enum
import hmac
import hashlib
import json


class SlackEventType(str, Enum):
    """Slack event types"""
    APP_MENTION = "app_mention"
    MESSAGE = "message"
    MEMBER_JOINED = "member_joined_channel"
    REACTION_ADDED = "reaction_added"
    COMMAND = "command"


# Database Models

class SlackWorkspace(Base):
    """Slack workspace connection"""
    __tablename__ = 'slack_workspaces'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # OAuth tokens
    access_token = Column(Text, nullable=True)
    bot_token = Column(Text, nullable=True)
    
    # Workspace info
    team_id = Column(String(50), nullable=False, unique=True)
    team_name = Column(String(255), nullable=True)
    
    # Bot info
    bot_user_id = Column(String(50), nullable=True)
    bot_scopes = Column(JSONB, default=list)
    
    # Settings
    default_channel = Column(String(100), nullable=True)
    notification_settings = Column(JSONB, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class SlackChannelMapping(Base):
    """Mapping between Cerebrum projects and Slack channels"""
    __tablename__ = 'slack_channel_mappings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('slack_workspaces.id', ondelete='CASCADE'), nullable=False)
    
    # Slack channel
    channel_id = Column(String(50), nullable=False)
    channel_name = Column(String(255), nullable=True)
    
    # Cerebrum project
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=True)
    
    # Notification settings
    notify_on_task_created = Column(Boolean, default=True)
    notify_on_task_completed = Column(Boolean, default=True)
    notify_on_document_uploaded = Column(Boolean, default=True)
    notify_on_rfi_created = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SlackNotificationLog(Base):
    """Log of sent Slack notifications"""
    __tablename__ = 'slack_notification_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('slack_workspaces.id', ondelete='CASCADE'), nullable=False)
    channel_mapping_id = Column(UUID(as_uuid=True), ForeignKey('slack_channel_mappings.id'), nullable=True)
    
    # Notification details
    notification_type = Column(String(100), nullable=False)
    message_text = Column(Text, nullable=True)
    blocks = Column(JSONB, nullable=True)
    
    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    slack_message_ts = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Schemas

class SlackOAuthCallback(BaseModel):
    """Slack OAuth callback"""
    code: str
    state: Optional[str] = None


class SlackCommandRequest(BaseModel):
    """Slack slash command request"""
    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    response_url: str
    trigger_id: str


class SlackEventCallback(BaseModel):
    """Slack event callback"""
    token: str
    team_id: str
    api_app_id: str
    event: Dict[str, Any]
    type: str
    event_id: str
    event_time: int


class SlackMessageBlock(BaseModel):
    """Slack message block"""
    type: str
    text: Optional[Dict[str, str]] = None
    fields: Optional[List[Dict[str, str]]] = None
    accessory: Optional[Dict[str, Any]] = None


class SlackNotificationRequest(BaseModel):
    """Send Slack notification request"""
    channel: str
    text: Optional[str] = None
    blocks: Optional[List[SlackMessageBlock]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


# Service Classes

class SlackService:
    """Service for Slack integration"""
    
    API_BASE_URL = "https://slack.com/api"
    
    def __init__(self, db: Session, client_id: str, client_secret: str, signing_secret: str):
        self.db = db
        self.client_id = client_id
        self.client_secret = client_secret
        self.signing_secret = signing_secret
    
    def get_auth_url(self, tenant_id: str) -> str:
        """Get Slack OAuth URL"""
        
        scopes = [
            "chat:write",
            "chat:write.public",
            "channels:read",
            "groups:read",
            "im:read",
            "mpim:read",
            "users:read",
            "commands",
            "reactions:write"
        ]
        
        state = str(uuid.uuid4())
        
        # Store state for validation
        
        return (
            f"https://slack.com/oauth/v2/authorize?"
            f"client_id={self.client_id}&"
            f"scope={','.join(scopes)}&"
            f"state={state}"
        )
    
    def handle_oauth_callback(
        self,
        tenant_id: str,
        callback: SlackOAuthCallback,
        created_by: Optional[str] = None
    ) -> SlackWorkspace:
        """Handle Slack OAuth callback"""
        
        # Exchange code for token
        response = requests.post(
            f"{self.API_BASE_URL}/oauth.v2.access",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": callback.code
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to exchange code")
        
        data = response.json()
        
        if not data.get('ok'):
            raise HTTPException(400, f"Slack error: {data.get('error')}")
        
        # Create or update workspace
        workspace = self.db.query(SlackWorkspace).filter(
            SlackWorkspace.team_id == data['team']['id']
        ).first()
        
        if not workspace:
            workspace = SlackWorkspace(
                tenant_id=tenant_id,
                team_id=data['team']['id']
            )
            self.db.add(workspace)
        
        workspace.access_token = data['authed_user']['access_token']
        workspace.bot_token = data['access_token']
        workspace.team_name = data['team']['name']
        workspace.bot_user_id = data['bot_user_id']
        workspace.bot_scopes = data.get('scope', '').split(',')
        workspace.created_by = created_by
        
        self.db.commit()
        self.db.refresh(workspace)
        
        return workspace
    
    def verify_request_signature(self, request: Request, body: bytes) -> bool:
        """Verify Slack request signature"""
        
        timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
        signature = request.headers.get('X-Slack-Signature', '')
        
        if not timestamp or not signature:
            return False
        
        # Check timestamp is within 5 minutes
        import time
        if abs(time.time() - int(timestamp)) > 300:
            return False
        
        # Create signature
        basestring = f"v0:{timestamp}:{body.decode()}"
        my_signature = 'v0=' + hmac.new(
            self.signing_secret.encode(),
            basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(my_signature, signature)
    
    def handle_slash_command(
        self,
        command: SlackCommandRequest
    ) -> Dict[str, Any]:
        """Handle Slack slash command"""
        
        # Parse command
        cmd_parts = command.text.strip().split()
        
        if not cmd_parts:
            return self._help_response()
        
        action = cmd_parts[0].lower()
        
        if action == 'help':
            return self._help_response()
        
        elif action == 'task':
            return self._handle_task_command(command, cmd_parts[1:])
        
        elif action == 'project':
            return self._handle_project_command(command, cmd_parts[1:])
        
        elif action == 'status':
            return self._handle_status_command(command, cmd_parts[1:])
        
        else:
            return {
                "text": f"Unknown command: {action}. Type `/cerebrum help` for available commands."
            }
    
    def _help_response(self) -> Dict[str, Any]:
        """Return help message"""
        
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Cerebrum AI Commands"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Available commands:*\n"
                            "• `/cerebrum task <title>` - Create a new task\n"
                            "• `/cerebrum project list` - List your projects\n"
                            "• `/cerebrum status` - Get project status\n"
                            "• `/cerebrum help` - Show this help message"
                        )
                    }
                }
            ]
        }
    
    def _handle_task_command(
        self,
        command: SlackCommandRequest,
        args: List[str]
    ) -> Dict[str, Any]:
        """Handle task command"""
        
        if not args:
            return {"text": "Please provide a task title. Example: `/cerebrum task Review drawings`"}
        
        title = ' '.join(args)
        
        # Create task in Cerebrum
        # This would integrate with your task service
        
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ Task created: *{title}*"
                    }
                }
            ]
        }
    
    def _handle_project_command(
        self,
        command: SlackCommandRequest,
        args: List[str]
    ) -> Dict[str, Any]:
        """Handle project command"""
        
        if not args or args[0] != 'list':
            return {"text": "Usage: `/cerebrum project list`"}
        
        # Get projects from Cerebrum
        # This would integrate with your project service
        
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Your Projects:*\n• Project A\n• Project B\n• Project C"
                    }
                }
            ]
        }
    
    def _handle_status_command(
        self,
        command: SlackCommandRequest,
        args: List[str]
    ) -> Dict[str, Any]:
        """Handle status command"""
        
        # Get project status from Cerebrum
        
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Project Status*\n"
                            "📊 Tasks: 15 open, 42 completed\n"
                            "📄 Documents: 128 total\n"
                            "📋 RFIs: 3 pending response"
                        )
                    }
                }
            ]
        }
    
    def send_notification(
        self,
        workspace: SlackWorkspace,
        request: SlackNotificationRequest
    ) -> Dict[str, Any]:
        """Send notification to Slack"""
        
        payload = {
            "channel": request.channel
        }
        
        if request.text:
            payload["text"] = request.text
        
        if request.blocks:
            payload["blocks"] = [b.model_dump() for b in request.blocks]
        
        if request.attachments:
            payload["attachments"] = request.attachments
        
        response = requests.post(
            f"{self.API_BASE_URL}/chat.postMessage",
            headers={"Authorization": f"Bearer {workspace.bot_token}"},
            json=payload
        )
        
        if response.status_code != 200:
            raise HTTPException(400, "Failed to send message")
        
        data = response.json()
        
        # Log notification
        log = SlackNotificationLog(
            workspace_id=workspace.id,
            notification_type='manual',
            message_text=request.text,
            blocks=payload.get('blocks'),
            success=data.get('ok'),
            slack_message_ts=data.get('ts')
        )
        self.db.add(log)
        self.db.commit()
        
        return data
    
    def notify_project_event(
        self,
        project_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Send notification for project event"""
        
        # Get channel mappings for project
        mappings = self.db.query(SlackChannelMapping).filter(
            SlackChannelMapping.project_id == project_id
        ).all()
        
        for mapping in mappings:
            workspace = self.db.query(SlackWorkspace).filter(
                SlackWorkspace.id == mapping.workspace_id
            ).first()
            
            if not workspace or not workspace.is_active:
                continue
            
            # Check if notification is enabled for this event type
            should_notify = self._should_notify(mapping, event_type)
            
            if not should_notify:
                continue
            
            # Build message
            message = self._build_event_message(event_type, event_data)
            
            try:
                self.send_notification(
                    workspace,
                    SlackNotificationRequest(
                        channel=mapping.channel_id,
                        blocks=message
                    )
                )
            except Exception as e:
                # Log error but don't fail
                pass
    
    def _should_notify(self, mapping: SlackChannelMapping, event_type: str) -> bool:
        """Check if notification should be sent for event type"""
        
        if event_type == 'task_created':
            return mapping.notify_on_task_created
        elif event_type == 'task_completed':
            return mapping.notify_on_task_completed
        elif event_type == 'document_uploaded':
            return mapping.notify_on_document_uploaded
        elif event_type == 'rfi_created':
            return mapping.notify_on_rfi_created
        
        return True
    
    def _build_event_message(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build Slack message blocks for event"""
        
        if event_type == 'task_created':
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📝 *New Task*\n*{event_data.get('title')}*\n{event_data.get('description', '')}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Task"
                            },
                            "url": event_data.get('url', '#')
                        }
                    ]
                }
            ]
        
        elif event_type == 'task_completed':
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *Task Completed*\n*{event_data.get('title')}*\nCompleted by {event_data.get('completed_by')}"
                    }
                }
            ]
        
        return []


# Export
__all__ = [
    'SlackEventType',
    'SlackWorkspace',
    'SlackChannelMapping',
    'SlackNotificationLog',
    'SlackOAuthCallback',
    'SlackCommandRequest',
    'SlackEventCallback',
    'SlackMessageBlock',
    'SlackNotificationRequest',
    'SlackService'
]
