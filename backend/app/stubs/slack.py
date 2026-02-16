"""
Slack API Stub

Stub implementation for Slack API.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from .base import BaseStub, StubResponse


class SlackStub(BaseStub):
    """
    Stub for Slack API.
    
    Provides mock data for:
    - Messages
    - Channels
    - Users
    - Webhooks
    """
    
    service_name = "slack"
    version = "1.0.0-stub"
    
    _channels = [
        {"id": "C001", "name": "general", "is_channel": True, "num_members": 10},
        {"id": "C002", "name": "engineering", "is_channel": True, "num_members": 5},
        {"id": "C003", "name": "random", "is_channel": True, "num_members": 10},
    ]
    
    _messages = [
        {"type": "message", "user": "U001", "text": "Hello team!", "ts": "1234567890.000001"},
        {"type": "message", "user": "U002", "text": "Project update: on track", "ts": "1234567890.000002"},
    ]
    
    def get_info(self) -> Dict[str, Any]:
        """Return stub information."""
        return {
            "service": self.service_name,
            "version": self.version,
            "mode": "stub",
            "endpoints": ["chat", "channels", "users", "webhooks"],
        }
    
    def send_message(self, channel: str, text: str, **kwargs) -> StubResponse:
        """Mock send message."""
        self._log_call("send_message", channel=channel, text=text[:50])
        return self._success_response(
            data={
                "ok": True,
                "channel": channel,
                "ts": datetime.utcnow().timestamp(),
                "message": {"text": text, "type": "message"},
                "stub": True,
            },
            message=f"Message sent to #{channel} (stub - not delivered)",
        )
    
    def post_webhook(self, webhook_url: str, text: str, **kwargs) -> StubResponse:
        """Mock webhook post."""
        self._log_call("post_webhook", webhook_url=webhook_url[:30], text=text[:50])
        return self._success_response(
            data={
                "ok": True,
                "webhook": webhook_url[:30] + "...",
                "text_preview": text[:100],
                "posted": True,
                "stub": True,
            },
            message="Webhook posted (stub - not delivered)",
        )
    
    def get_channels(self) -> StubResponse:
        """Get mock channels."""
        self._log_call("get_channels")
        return self._success_response(
            data={"channels": self._channels, "ok": True},
            message=f"Retrieved {len(self._channels)} channels (stub)",
        )
    
    def get_channel_history(self, channel: str) -> StubResponse:
        """Get mock channel history."""
        self._log_call("get_channel_history", channel=channel)
        return self._success_response(
            data={"messages": self._messages, "has_more": False, "ok": True},
            message=f"Retrieved {len(self._messages)} messages (stub)",
        )
    
    def upload_file(self, channels: List[str], content: str, filename: str) -> StubResponse:
        """Mock file upload."""
        self._log_call("upload_file", channels=channels, filename=filename)
        return self._success_response(
            data={
                "ok": True,
                "file": {
                    "id": "F999",
                    "name": filename,
                    "size": len(content),
                    "channels": channels,
                },
                "stub": True,
            },
            message=f"File '{filename}' uploaded (stub)",
        )
