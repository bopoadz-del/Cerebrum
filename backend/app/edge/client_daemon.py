"""
Edge client daemon for Jetson devices.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import json
import uuid


class DaemonStatus(Enum):
    """Status of the edge daemon."""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RUNNING = "running"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class DeviceInfo:
    """Information about the edge device."""
    device_id: str
    device_type: str
    hardware_version: str
    software_version: str
    cuda_version: Optional[str] = None
    tensorrt_version: Optional[str] = None
    total_memory_mb: int = 0
    storage_total_gb: int = 0
    gpu_count: int = 0
    capabilities: List[str] = field(default_factory=list)


@dataclass
class SystemMetrics:
    """Current system metrics."""
    cpu_percent: float
    memory_used_mb: int
    memory_total_mb: int
    gpu_utilization: Optional[float] = None
    gpu_memory_used_mb: Optional[int] = None
    gpu_memory_total_mb: Optional[int] = None
    disk_used_gb: int = 0
    disk_total_gb: int = 0
    temperature_celsius: Optional[float] = None
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0


class EdgeClientDaemon:
    """Client daemon running on Jetson edge devices."""
    
    HEARTBEAT_INTERVAL = 30  # seconds
    RECONNECT_DELAY = 5  # seconds
    MAX_RECONNECT_ATTEMPTS = 10
    
    def __init__(
        self,
        server_url: str,
        device_id: str,
        device_info: DeviceInfo
    ):
        self.server_url = server_url
        self.device_id = device_id
        self.device_info = device_info
        
        self.status = DaemonStatus.INITIALIZING
        self.websocket = None
        self._running = False
        self._heartbeat_task = None
        self._command_handlers: Dict[str, Callable] = {}
        self._active_models: Dict[str, Any] = {}
        self._active_jobs: Dict[str, Any] = {}
        self._metrics_history: List[SystemMetrics] = []
    
    async def start(self):
        """Start the edge daemon."""
        self._running = True
        self.status = DaemonStatus.CONNECTING
        
        # Register default command handlers
        self._register_default_handlers()
        
        # Start connection loop
        await self._connection_loop()
    
    async def stop(self):
        """Stop the edge daemon."""
        self._running = False
        self.status = DaemonStatus.SHUTTING_DOWN
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        if self.websocket:
            await self.websocket.close()
    
    def _register_default_handlers(self):
        """Register default command handlers."""
        self._command_handlers["health_check"] = self._handle_health_check
        self._command_handlers["start_deployment"] = self._handle_deployment
        self._command_handlers["rollback_deployment"] = self._handle_rollback
        self._command_handlers["establish_tunnel"] = self._handle_tunnel
        self._command_handlers["close_tunnel"] = self._handle_close_tunnel
        self._command_handlers["run_inference"] = self._handle_inference
        self._command_handlers["load_model"] = self._handle_load_model
        self._command_handlers["unload_model"] = self._handle_unload_model
        self._command_handlers["update_config"] = self._handle_update_config
        self._command_handlers["update_heartbeat_interval"] = self._handle_update_heartbeat
        self._command_handlers["reboot"] = self._handle_reboot
    
    async def _connection_loop(self):
        """Main connection loop with reconnection."""
        
        reconnect_attempts = 0
        
        while self._running:
            try:
                await self._connect()
                reconnect_attempts = 0
                await self._handle_messages()
                
            except Exception as e:
                self.status = DaemonStatus.ERROR
                reconnect_attempts += 1
                
                if reconnect_attempts >= self.MAX_RECONNECT_ATTEMPTS:
                    self._running = False
                    break
                
                await asyncio.sleep(self.RECONNECT_DELAY * reconnect_attempts)
    
    async def _connect(self):
        """Connect to the server."""
        
        import websockets
        
        self.websocket = await websockets.connect(
            f"{self.server_url}/ws/edge/{self.device_id}",
            extra_headers={
                "X-Device-ID": self.device_id,
                "X-Device-Type": self.device_info.device_type
            }
        )
        
        self.status = DaemonStatus.CONNECTED
        
        # Send initial registration
        await self._send_registration()
        
        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        self.status = DaemonStatus.RUNNING
    
    async def _send_registration(self):
        """Send device registration message."""
        
        message = {
            "type": "register",
            "device_id": self.device_id,
            "device_info": {
                "device_type": self.device_info.device_type,
                "hardware_version": self.device_info.hardware_version,
                "software_version": self.device_info.software_version,
                "cuda_version": self.device_info.cuda_version,
                "tensorrt_version": self.device_info.tensorrt_version,
                "total_memory_mb": self.device_info.total_memory_mb,
                "storage_total_gb": self.device_info.storage_total_gb,
                "gpu_count": self.device_info.gpu_count,
                "capabilities": self.device_info.capabilities
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        
        while self._running and self.status == DaemonStatus.RUNNING:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            except Exception:
                break
    
    async def _send_heartbeat(self):
        """Send heartbeat message."""
        
        metrics = await self._collect_metrics()
        
        message = {
            "type": "heartbeat",
            "device_id": self.device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "online",
            "metrics": {
                "cpu_percent": metrics.cpu_percent,
                "memory_used_mb": metrics.memory_used_mb,
                "memory_total_mb": metrics.memory_total_mb,
                "gpu_utilization": metrics.gpu_utilization,
                "gpu_memory_used_mb": metrics.gpu_memory_used_mb,
                "temperature_celsius": metrics.temperature_celsius
            },
            "active_jobs": list(self._active_jobs.keys()),
            "software_version": self.device_info.software_version,
            "uptime_seconds": self._get_uptime_seconds()
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def _collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        
        # Placeholder - in production, use actual system calls
        # For Jetson, use tegrastats or jtop
        
        import psutil
        
        memory = psutil.virtual_memory()
        
        metrics = SystemMetrics(
            cpu_percent=psutil.cpu_percent(),
            memory_used_mb=memory.used // (1024 * 1024),
            memory_total_mb=memory.total // (1024 * 1024),
            disk_used_gb=psutil.disk_usage('/').used // (1024 * 1024 * 1024),
            disk_total_gb=psutil.disk_usage('/').total // (1024 * 1024 * 1024)
        )
        
        # Try to get GPU metrics for Jetson
        try:
            metrics.gpu_utilization = await self._get_gpu_utilization()
            metrics.gpu_memory_used_mb = await self._get_gpu_memory()
            metrics.temperature_celsius = await self._get_temperature()
        except Exception:
            pass
        
        self._metrics_history.append(metrics)
        
        # Keep only last 100 measurements
        if len(self._metrics_history) > 100:
            self._metrics_history = self._metrics_history[-100:]
        
        return metrics
    
    async def _get_gpu_utilization(self) -> Optional[float]:
        """Get GPU utilization for Jetson."""
        # Placeholder - use tegrastats or jtop
        return None
    
    async def _get_gpu_memory(self) -> Optional[int]:
        """Get GPU memory usage for Jetson."""
        # Placeholder - use tegrastats or jtop
        return None
    
    async def _get_temperature(self) -> Optional[float]:
        """Get device temperature."""
        # Placeholder - read from thermal zones
        return None
    
    def _get_uptime_seconds(self) -> int:
        """Get device uptime in seconds."""
        import psutil
        return int(datetime.utcnow().timestamp() - psutil.boot_time())
    
    async def _handle_messages(self):
        """Handle incoming messages from server."""
        
        while self._running:
            try:
                message_str = await self.websocket.recv()
                message = json.loads(message_str)
                
                command = message.get("command")
                payload = message.get("payload", {})
                
                handler = self._command_handlers.get(command)
                if handler:
                    response = await handler(payload)
                    
                    # Send response
                    await self.websocket.send(json.dumps({
                        "type": "response",
                        "command": command,
                        "request_id": payload.get("request_id"),
                        "success": response.get("success", True),
                        "data": response.get("data"),
                        "error": response.get("error")
                    }))
                
            except Exception as e:
                if self._running:
                    self.status = DaemonStatus.ERROR
                break
    
    # Command handlers
    async def _handle_health_check(self, payload: Dict) -> Dict:
        """Handle health check command."""
        metrics = await self._collect_metrics()
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "metrics": {
                    "cpu_percent": metrics.cpu_percent,
                    "memory_percent": (
                        metrics.memory_used_mb / metrics.memory_total_mb * 100
                    ) if metrics.memory_total_mb > 0 else 0
                }
            }
        }
    
    async def _handle_deployment(self, payload: Dict) -> Dict:
        """Handle deployment command."""
        # Placeholder - implement actual deployment
        return {"success": True, "data": {"status": "downloading"}}
    
    async def _handle_rollback(self, payload: Dict) -> Dict:
        """Handle rollback command."""
        # Placeholder - implement actual rollback
        return {"success": True, "data": {"status": "rolled_back"}}
    
    async def _handle_tunnel(self, payload: Dict) -> Dict:
        """Handle tunnel establishment."""
        # Placeholder - implement actual tunnel
        return {"success": True, "data": {"status": "tunnel_established"}}
    
    async def _handle_close_tunnel(self, payload: Dict) -> Dict:
        """Handle tunnel close."""
        return {"success": True}
    
    async def _handle_inference(self, payload: Dict) -> Dict:
        """Handle inference request."""
        model_name = payload.get("model_name")
        input_data = payload.get("input_data")
        
        # Run inference
        # Placeholder - implement actual inference
        result = {"output": "placeholder"}
        
        return {"success": True, "data": result}
    
    async def _handle_load_model(self, payload: Dict) -> Dict:
        """Handle model load command."""
        model_name = payload.get("model_name")
        model_path = payload.get("model_path")
        
        # Load model
        # Placeholder - implement actual model loading
        self._active_models[model_name] = {"path": model_path}
        
        return {"success": True, "data": {"model_loaded": model_name}}
    
    async def _handle_unload_model(self, payload: Dict) -> Dict:
        """Handle model unload command."""
        model_name = payload.get("model_name")
        
        if model_name in self._active_models:
            del self._active_models[model_name]
        
        return {"success": True}
    
    async def _handle_update_config(self, payload: Dict) -> Dict:
        """Handle config update command."""
        config = payload.get("config", {})
        
        # Apply config updates
        if "heartbeat_interval" in config:
            self.HEARTBEAT_INTERVAL = config["heartbeat_interval"]
        
        return {"success": True}
    
    async def _handle_update_heartbeat(self, payload: Dict) -> Dict:
        """Handle heartbeat interval update."""
        interval = payload.get("interval_seconds", 30)
        self.HEARTBEAT_INTERVAL = interval
        return {"success": True}
    
    async def _handle_reboot(self, payload: Dict) -> Dict:
        """Handle reboot command."""
        # Schedule reboot
        asyncio.create_task(self._delayed_reboot())
        return {"success": True, "data": {"reboot_scheduled": True}}
    
    async def _delayed_reboot(self, delay: int = 5):
        """Reboot after delay."""
        await asyncio.sleep(delay)
        # In production, use actual reboot command
        import os
        os.system("reboot")
