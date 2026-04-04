"""
WebSocket heartbeat for edge device status.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import json


class DeviceStatus(Enum):
    """Edge device connection status."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


@dataclass
class HeartbeatMessage:
    """Heartbeat message from edge device."""
    device_id: str
    timestamp: datetime
    status: DeviceStatus
    metrics: Dict[str, Any]
    active_jobs: List[str]
    software_version: str
    uptime_seconds: int


@dataclass
class DeviceConnection:
    """Connection state for an edge device."""
    device_id: str
    websocket: Any  # WebSocket object
    status: DeviceStatus
    last_heartbeat: datetime
    heartbeat_interval_seconds: int
    missed_heartbeats: int
    connection_started: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class HeartbeatManager:
    """Manage WebSocket heartbeats for edge devices."""
    
    # Configuration
    DEFAULT_HEARTBEAT_INTERVAL = 30  # seconds
    MAX_MISSED_HEARTBEATS = 3
    CHECK_INTERVAL = 10  # seconds
    
    def __init__(self):
        self.connections: Dict[str, DeviceConnection] = {}
        self._status_callbacks: List[Callable[[str, DeviceStatus, DeviceStatus], None]] = []
        self._heartbeat_callbacks: List[Callable[[HeartbeatMessage], None]] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the heartbeat manager."""
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_heartbeats())
    
    async def stop(self):
        """Stop the heartbeat manager."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def register_connection(
        self,
        device_id: str,
        websocket: Any,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeviceConnection:
        """Register a new device connection."""
        
        connection = DeviceConnection(
            device_id=device_id,
            websocket=websocket,
            status=DeviceStatus.ONLINE,
            last_heartbeat=datetime.utcnow(),
            heartbeat_interval_seconds=heartbeat_interval,
            missed_heartbeats=0,
            connection_started=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.connections[device_id] = connection
        
        # Notify status change
        await self._notify_status_change(device_id, DeviceStatus.UNKNOWN, DeviceStatus.ONLINE)
        
        return connection
    
    async def unregister_connection(self, device_id: str):
        """Unregister a device connection."""
        
        if device_id in self.connections:
            old_status = self.connections[device_id].status
            del self.connections[device_id]
            await self._notify_status_change(device_id, old_status, DeviceStatus.OFFLINE)
    
    async def handle_heartbeat(self, message_data: Dict[str, Any]) -> bool:
        """Process a heartbeat message from a device."""
        
        device_id = message_data.get("device_id")
        if not device_id or device_id not in self.connections:
            return False
        
        connection = self.connections[device_id]
        
        # Parse heartbeat message
        try:
            heartbeat = HeartbeatMessage(
                device_id=device_id,
                timestamp=datetime.utcnow(),
                status=DeviceStatus(message_data.get("status", "online")),
                metrics=message_data.get("metrics", {}),
                active_jobs=message_data.get("active_jobs", []),
                software_version=message_data.get("software_version", "unknown"),
                uptime_seconds=message_data.get("uptime_seconds", 0)
            )
        except (ValueError, KeyError) as e:
            return False
        
        # Update connection state
        old_status = connection.status
        connection.last_heartbeat = datetime.utcnow()
        connection.missed_heartbeats = 0
        connection.status = heartbeat.status
        
        # Notify status change if different
        if old_status != heartbeat.status:
            await self._notify_status_change(device_id, old_status, heartbeat.status)
        
        # Notify heartbeat received
        for callback in self._heartbeat_callbacks:
            try:
                await callback(heartbeat)
            except Exception:
                pass
        
        return True
    
    async def _monitor_heartbeats(self):
        """Monitor heartbeats and detect offline devices."""
        
        while self._running:
            await asyncio.sleep(self.CHECK_INTERVAL)
            
            now = datetime.utcnow()
            
            for device_id, connection in list(self.connections.items()):
                # Calculate expected heartbeat time
                expected_interval = timedelta(
                    seconds=connection.heartbeat_interval_seconds * 
                    (connection.missed_heartbeats + 1)
                )
                time_since_last = now - connection.last_heartbeat
                
                if time_since_last > expected_interval:
                    connection.missed_heartbeats += 1
                    
                    if connection.missed_heartbeats >= self.MAX_MISSED_HEARTBEATS:
                        # Mark as offline
                        old_status = connection.status
                        connection.status = DeviceStatus.OFFLINE
                        await self._notify_status_change(
                            device_id, old_status, DeviceStatus.OFFLINE
                        )
                    elif connection.missed_heartbeats >= self.MAX_MISSED_HEARTBEATS // 2:
                        # Mark as degraded
                        old_status = connection.status
                        connection.status = DeviceStatus.DEGRADED
                        await self._notify_status_change(
                            device_id, old_status, DeviceStatus.DEGRADED
                        )
    
    async def _notify_status_change(
        self,
        device_id: str,
        old_status: DeviceStatus,
        new_status: DeviceStatus
    ):
        """Notify status change callbacks."""
        
        for callback in self._status_callbacks:
            try:
                await callback(device_id, old_status, new_status)
            except Exception:
                pass
    
    def on_status_change(
        self,
        callback: Callable[[str, DeviceStatus, DeviceStatus], None]
    ):
        """Register a status change callback."""
        self._status_callbacks.append(callback)
    
    def on_heartbeat(
        self,
        callback: Callable[[HeartbeatMessage], None]
    ):
        """Register a heartbeat received callback."""
        self._heartbeat_callbacks.append(callback)
    
    async def send_command(
        self,
        device_id: str,
        command: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a command to a device."""
        
        connection = self.connections.get(device_id)
        if not connection or connection.status == DeviceStatus.OFFLINE:
            return False
        
        message = {
            "type": "command",
            "command": command,
            "payload": payload or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await connection.websocket.send(json.dumps(message))
            return True
        except Exception:
            return False
    
    async def broadcast_command(
        self,
        command: str,
        payload: Optional[Dict[str, Any]] = None,
        status_filter: Optional[List[DeviceStatus]] = None
    ) -> Dict[str, bool]:
        """Broadcast a command to multiple devices."""
        
        results = {}
        
        for device_id, connection in self.connections.items():
            if status_filter and connection.status not in status_filter:
                continue
            
            results[device_id] = await self.send_command(
                device_id, command, payload
            )
        
        return results
    
    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a device."""
        
        connection = self.connections.get(device_id)
        if not connection:
            return None
        
        now = datetime.utcnow()
        time_since_heartbeat = (now - connection.last_heartbeat).total_seconds()
        
        return {
            "device_id": device_id,
            "status": connection.status.value,
            "last_heartbeat": connection.last_heartbeat.isoformat(),
            "time_since_heartbeat_seconds": time_since_heartbeat,
            "connection_duration_seconds": (
                now - connection.connection_started
            ).total_seconds(),
            "missed_heartbeats": connection.missed_heartbeats,
            "metadata": connection.metadata
        }
    
    async def get_all_status(self) -> List[Dict[str, Any]]:
        """Get status of all connected devices."""
        
        statuses = []
        for device_id in self.connections:
            status = await self.get_device_status(device_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    async def request_health_check(self, device_id: str) -> bool:
        """Request a health check from a device."""
        
        return await self.send_command(
            device_id,
            "health_check",
            {"request_id": str(datetime.utcnow().timestamp())}
        )
    
    async def update_heartbeat_interval(
        self,
        device_id: str,
        new_interval: int
    ) -> bool:
        """Update the heartbeat interval for a device."""
        
        connection = self.connections.get(device_id)
        if not connection:
            return False
        
        connection.heartbeat_interval_seconds = new_interval
        
        # Notify device of new interval
        return await self.send_command(
            device_id,
            "update_heartbeat_interval",
            {"interval_seconds": new_interval}
        )
