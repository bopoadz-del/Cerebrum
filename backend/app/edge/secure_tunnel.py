"""
Secure tunnel for remote device access.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid
import ssl


class TunnelStatus(Enum):
    """Status of a secure tunnel."""
    PENDING = "pending"
    CONNECTING = "connecting"
    ACTIVE = "active"
    CLOSED = "closed"
    ERROR = "error"


class TunnelProtocol(Enum):
    """Supported tunnel protocols."""
    SSH = "ssh"
    WEBSOCKET = "websocket"
    GRPC = "grpc"


@dataclass
class TunnelSession:
    """Secure tunnel session."""
    session_id: str
    device_id: str
    protocol: TunnelProtocol
    local_port: int
    remote_port: int
    status: TunnelStatus
    created_by: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    bytes_transferred: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecureTunnelManager:
    """Manage secure tunnels for remote device access."""
    
    DEFAULT_SESSION_TIMEOUT = 3600  # 1 hour
    MAX_SESSIONS_PER_DEVICE = 3
    
    def __init__(self, heartbeat_manager: Optional[Any] = None):
        self.heartbeat_manager = heartbeat_manager
        self.sessions: Dict[str, TunnelSession] = {}
        self.device_sessions: Dict[str, List[str]] = {}
        self._active_connections: Dict[str, Any] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the tunnel manager."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
    
    async def stop(self):
        """Stop the tunnel manager."""
        self._running = False
        
        # Close all sessions
        for session_id in list(self.sessions.keys()):
            await self.close_session(session_id)
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def create_session(
        self,
        device_id: str,
        protocol: TunnelProtocol,
        local_port: int,
        remote_port: int,
        created_by: str,
        timeout_seconds: int = DEFAULT_SESSION_TIMEOUT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TunnelSession:
        """Create a new tunnel session."""
        
        # Check device session limit
        device_session_ids = self.device_sessions.get(device_id, [])
        if len(device_session_ids) >= self.MAX_SESSIONS_PER_DEVICE:
            raise ValueError(
                f"Maximum sessions ({self.MAX_SESSIONS_PER_DEVICE}) reached for device {device_id}"
            )
        
        # Check if device is online
        if self.heartbeat_manager:
            status = await self.heartbeat_manager.get_device_status(device_id)
            if not status or status["status"] != "online":
                raise ValueError(f"Device {device_id} is not online")
        
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        session = TunnelSession(
            session_id=session_id,
            device_id=device_id,
            protocol=protocol,
            local_port=local_port,
            remote_port=remote_port,
            status=TunnelStatus.PENDING,
            created_by=created_by,
            created_at=now,
            expires_at=now + timedelta(seconds=timeout_seconds),
            last_activity=now,
            metadata=metadata or {}
        )
        
        self.sessions[session_id] = session
        
        if device_id not in self.device_sessions:
            self.device_sessions[device_id] = []
        self.device_sessions[device_id].append(session_id)
        
        # Establish tunnel
        asyncio.create_task(self._establish_tunnel(session_id))
        
        return session
    
    async def _establish_tunnel(self, session_id: str):
        """Establish the tunnel connection."""
        
        session = self.sessions.get(session_id)
        if not session:
            return
        
        session.status = TunnelStatus.CONNECTING
        
        try:
            # Send tunnel request to device
            if self.heartbeat_manager:
                success = await self.heartbeat_manager.send_command(
                    session.device_id,
                    "establish_tunnel",
                    {
                        "session_id": session_id,
                        "protocol": session.protocol.value,
                        "remote_port": session.remote_port
                    }
                )
                
                if not success:
                    session.status = TunnelStatus.ERROR
                    session.error_message = "Failed to send tunnel request to device"
                    return
            
            # Wait for device to establish tunnel
            # In production, this would use a proper handshake
            await asyncio.sleep(2)
            
            # Create local listener
            await self._create_local_listener(session)
            
            session.status = TunnelStatus.ACTIVE
            
        except Exception as e:
            session.status = TunnelStatus.ERROR
            session.error_message = str(e)
    
    async def _create_local_listener(self, session: TunnelSession):
        """Create local port listener for the tunnel."""
        # Placeholder - in production, create actual TCP listener
        pass
    
    async def close_session(self, session_id: str) -> bool:
        """Close a tunnel session."""
        
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Send close command to device
        if self.heartbeat_manager:
            await self.heartbeat_manager.send_command(
                session.device_id,
                "close_tunnel",
                {"session_id": session_id}
            )
        
        # Close local connection
        if session_id in self._active_connections:
            # Close connection
            del self._active_connections[session_id]
        
        session.status = TunnelStatus.CLOSED
        
        # Remove from device sessions
        if session.device_id in self.device_sessions:
            self.device_sessions[session.device_id] = [
                sid for sid in self.device_sessions[session.device_id]
                if sid != session_id
            ]
        
        return True
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "device_id": session.device_id,
            "protocol": session.protocol.value,
            "local_port": session.local_port,
            "remote_port": session.remote_port,
            "status": session.status.value,
            "created_by": session.created_by,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "expires_in_seconds": (
                session.expires_at - datetime.utcnow()
            ).total_seconds(),
            "bytes_transferred": session.bytes_transferred,
            "error_message": session.error_message
        }
    
    async def list_sessions(
        self,
        device_id: Optional[str] = None,
        status: Optional[TunnelStatus] = None
    ) -> List[Dict[str, Any]]:
        """List tunnel sessions."""
        
        sessions = list(self.sessions.values())
        
        if device_id:
            sessions = [s for s in sessions if s.device_id == device_id]
        
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        return [
            await self.get_session(s.session_id)
            for s in sorted(sessions, key=lambda x: x.created_at, reverse=True)
        ]
    
    async def extend_session(
        self,
        session_id: str,
        additional_seconds: int
    ) -> bool:
        """Extend session expiration."""
        
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.expires_at = session.expires_at + timedelta(seconds=additional_seconds)
        
        return True
    
    async def _cleanup_expired_sessions(self):
        """Periodically cleanup expired sessions."""
        
        while self._running:
            await asyncio.sleep(60)  # Check every minute
            
            now = datetime.utcnow()
            expired_sessions = [
                sid for sid, session in self.sessions.items()
                if session.expires_at < now and session.status != TunnelStatus.CLOSED
            ]
            
            for session_id in expired_sessions:
                await self.close_session(session_id)
    
    async def handle_device_response(
        self,
        device_id: str,
        session_id: str,
        response: Dict[str, Any]
    ):
        """Handle tunnel response from device."""
        
        session = self.sessions.get(session_id)
        if not session or session.device_id != device_id:
            return
        
        if response.get("success"):
            session.status = TunnelStatus.ACTIVE
        else:
            session.status = TunnelStatus.ERROR
            session.error_message = response.get("error", "Unknown error")
    
    async def get_tunnel_logs(self, session_id: str) -> List[Dict[str, Any]]:
        """Get tunnel activity logs."""
        
        # Placeholder - in production, store and retrieve actual logs
        return [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "tunnel_created",
                "session_id": session_id
            }
        ]
    
    async def create_ssh_tunnel(
        self,
        device_id: str,
        local_port: int,
        remote_port: int = 22,
        created_by: str = "",
        timeout_seconds: int = DEFAULT_SESSION_TIMEOUT
    ) -> TunnelSession:
        """Create an SSH tunnel."""
        
        return await self.create_session(
            device_id=device_id,
            protocol=TunnelProtocol.SSH,
            local_port=local_port,
            remote_port=remote_port,
            created_by=created_by,
            timeout_seconds=timeout_seconds,
            metadata={"service": "ssh"}
        )
    
    async def create_port_forward(
        self,
        device_id: str,
        service_port: int,
        local_port: int,
        created_by: str = "",
        timeout_seconds: int = DEFAULT_SESSION_TIMEOUT
    ) -> TunnelSession:
        """Create a port forwarding tunnel."""
        
        return await self.create_session(
            device_id=device_id,
            protocol=TunnelProtocol.WEBSOCKET,
            local_port=local_port,
            remote_port=service_port,
            created_by=created_by,
            timeout_seconds=timeout_seconds,
            metadata={"service": "port_forward", "target_port": service_port}
        )
