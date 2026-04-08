"""
Cerebrum Agent WebSocket - Real-time Agent Interaction

Provides WebSocket endpoint for:
- Real-time task execution with progress updates
- Streaming agent responses
- Bidirectional communication
- Multi-step plan progress tracking
"""

import json
import asyncio
from typing import Dict, Optional, Set
from datetime import datetime
import logging

from fastapi import WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

# Import plan status enums (imported inside functions to avoid circular imports)


class AgentConnection:
    """Manages a single WebSocket connection to the agent."""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.now().isoformat()
        self.active_tasks: Set[str] = set()
        self._closed = False
    
    async def accept(self):
        """Accept the WebSocket connection."""
        await self.websocket.accept()
        logger.info(f"WebSocket connection accepted: {self.client_id}")
    
    async def send(self, message: Dict):
        """Send a message to the client."""
        if not self._closed and self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {self.client_id}: {e}")
                self._closed = True
    
    async def send_text(self, text: str):
        """Send text message to the client."""
        if not self._closed and self.websocket.client_state == WebSocketState.CONNECTED:
            try:
                await self.websocket.send_text(text)
            except Exception as e:
                logger.error(f"Error sending text to {self.client_id}: {e}")
                self._closed = True
    
    async def receive(self) -> Dict:
        """Receive a message from the client."""
        data = await self.websocket.receive_text()
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Close the connection."""
        self._closed = True
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                await self.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.debug(f"Error closing websocket for {self.client_id}: {e}")
        logger.info(f"WebSocket connection closed: {self.client_id}")


class AgentWebSocketManager:
    """
    Manages WebSocket connections for real-time agent interaction.
    
    Features:
    - Multiple concurrent connections
    - Real-time task progress updates
    - Streaming responses
    - Connection heartbeat
    """
    
    def __init__(self, agent):
        self.agent = agent
        self.connections: Dict[str, AgentConnection] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def connect(self, websocket: WebSocket, client_id: str) -> AgentConnection:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket object
            client_id: Unique client identifier
        
        Returns:
            AgentConnection instance
        """
        connection = AgentConnection(websocket, client_id)
        await connection.accept()
        
        self.connections[client_id] = connection
        
        # Send welcome message
        await connection.send({
            "type": "welcome",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to Cerebrum Agent. Send a task to begin."
        })
        
        # Start heartbeat if not running
        if not self._running:
            await self._start_heartbeat()
        
        logger.info(f"Client connected: {client_id}. Total connections: {len(self.connections)}")
        
        return connection
    
    async def disconnect(self, client_id: str, code: int = 1000, reason: str = ""):
        """Disconnect a client."""
        connection = self.connections.pop(client_id, None)
        if connection:
            await connection.close(code=code, reason=reason)
            logger.info(f"Client disconnected: {client_id}. Total connections: {len(self.connections)}")
        
        # Stop heartbeat if no connections
        if not self.connections and self._running:
            await self._stop_heartbeat()
    
    async def handle_message(self, client_id: str, data: Dict):
        """
        Handle an incoming message from a client.
        
        Message types:
        - task: Execute a single agent task
        - plan: Create and execute a multi-step plan
        - stream: Execute with streaming progress updates
        - cancel: Cancel current task
        - ping: Heartbeat response
        """
        connection = self.connections.get(client_id)
        if not connection:
            return
        
        msg_type = data.get("type", "task")
        
        try:
            if msg_type == "task":
                await self._handle_task(connection, data)
            
            elif msg_type == "plan":
                await self._handle_plan(connection, data)
            
            elif msg_type == "stream":
                await self._handle_stream(connection, data)
            
            elif msg_type == "cancel":
                await self._handle_cancel(connection, data)
            
            elif msg_type == "ping":
                await connection.send({"type": "pong", "timestamp": datetime.now().isoformat()})
            
            else:
                await connection.send({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
        
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await connection.send({
                "type": "error",
                "message": str(e)
            })
    
    async def _handle_task(self, connection: AgentConnection, data: Dict):
        """Handle a single task execution."""
        task = data.get("task", "")
        context = data.get("context", {})
        
        if not task:
            await connection.send({
                "type": "error",
                "message": "Task is required"
            })
            return
        
        await connection.send({
            "type": "task_started",
            "task": task,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            result = await self.agent.run(task, context)
            
            await connection.send({
                "type": "task_completed",
                "success": result.success,
                "action": result.action.value if hasattr(result.action, 'value') else str(result.action),
                "layer": result.layer.value if hasattr(result.layer, 'value') else str(result.layer),
                "data": result.data,
                "message": result.message,
                "timestamp": result.timestamp
            })
        
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            await connection.send({
                "type": "task_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _handle_plan(self, connection: AgentConnection, data: Dict):
        """Handle multi-step plan execution."""
        from app.agent.planner import MultiStepPlanner, StepStatus, PlanStatus
        
        goal = data.get("goal", "")
        context = data.get("context", {})
        
        if not goal:
            await connection.send({
                "type": "error",
                "message": "Goal is required for plan execution"
            })
            return
        
        # Create planner
        planner = MultiStepPlanner(self.agent.tools)
        plan = planner.create_plan(goal, context)
        
        await connection.send({
            "type": "plan_created",
            "plan_id": plan.id,
            "goal": goal,
            "steps": [s.to_dict() for s in plan.steps],
            "timestamp": datetime.now().isoformat()
        })
        
        connection.active_tasks.add(plan.id)
        
        try:
            # Execute plan with progress updates
            for step in plan.steps:
                # Send step started
                await connection.send({
                    "type": "step_started",
                    "plan_id": plan.id,
                    "step_id": step.id,
                    "description": step.description,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Execute the step
                step.status = StepStatus.RUNNING
                try:
                    if step.tool_name in self.agent.tools:
                        result = self.agent.tools[step.tool_name](**step.parameters)
                        step.result = result
                        step.status = StepStatus.COMPLETED
                    else:
                        step.error = f"Tool {step.tool_name} not found"
                        step.status = StepStatus.FAILED
                except Exception as e:
                    step.error = str(e)
                    step.status = StepStatus.FAILED
                
                # Send step completed
                await connection.send({
                    "type": "step_completed",
                    "plan_id": plan.id,
                    "step_id": step.id,
                    "status": step.status.value if hasattr(step.status, 'value') else str(step.status),
                    "result": step.result,
                    "error": step.error,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Update plan status
            plan.status = PlanStatus.COMPLETED if all(
                s.status == StepStatus.COMPLETED for s in plan.steps
            ) else PlanStatus.FAILED
            
            # Send plan completed
            await connection.send({
                "type": "plan_completed",
                "plan_id": plan.id,
                "status": plan.status.value if hasattr(plan.status, 'value') else str(plan.status),
                "progress": plan.get_progress(),
                "timestamp": datetime.now().isoformat()
            })
        
        finally:
            connection.active_tasks.discard(plan.id)
    
    async def _handle_stream(self, connection: AgentConnection, data: Dict):
        """Handle streaming task execution with real-time updates."""
        task = data.get("task", "")
        context = data.get("context", {})
        stream_id = f"stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not task:
            await connection.send({
                "type": "error",
                "message": "Task is required for streaming"
            })
            return
        
        await connection.send({
            "type": "stream_started",
            "stream_id": stream_id,
            "task": task,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # Stream layer movement
            original_layer = self.agent.get_current_layer()
            
            await connection.send({
                "type": "stream_update",
                "stream_id": stream_id,
                "update_type": "layer_change",
                "from_layer": original_layer.value if hasattr(original_layer, 'value') else str(original_layer),
                "to_layer": "analyzing",
                "timestamp": datetime.now().isoformat()
            })
            
            # Execute task
            result = await self.agent.run(task, context)
            
            # Stream completion
            await connection.send({
                "type": "stream_update",
                "stream_id": stream_id,
                "update_type": "completion",
                "success": result.success,
                "layer": result.layer.value if hasattr(result.layer, 'value') else str(result.layer),
                "action": result.action.value if hasattr(result.action, 'value') else str(result.action),
                "timestamp": datetime.now().isoformat()
            })
            
            await connection.send({
                "type": "stream_completed",
                "stream_id": stream_id,
                "result": {
                    "success": result.success,
                    "data": result.data,
                    "message": result.message
                },
                "timestamp": datetime.now().isoformat()
            })
        
        except Exception as e:
            logger.error(f"Stream execution error: {e}")
            await connection.send({
                "type": "stream_error",
                "stream_id": stream_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _handle_cancel(self, connection: AgentConnection, data: Dict):
        """Handle task cancellation request."""
        task_id = data.get("task_id", "")
        
        if task_id in connection.active_tasks:
            connection.active_tasks.discard(task_id)
            await connection.send({
                "type": "cancelled",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            await connection.send({
                "type": "error",
                "message": f"Task {task_id} not found or not active"
            })
    
    async def broadcast(self, message: Dict):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for client_id, connection in self.connections.items():
            try:
                await connection.send(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id, code=1001, reason="Broadcast failed")
    
    async def _start_heartbeat(self):
        """Start the heartbeat task."""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _stop_heartbeat(self):
        """Stop the heartbeat task."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to all clients."""
        while self._running:
            try:
                await self.broadcast({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat(),
                    "active_connections": len(self.connections)
                })
                await asyncio.sleep(30)  # Every 30 seconds
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(30)
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.connections)


# Global manager instance
_ws_manager: Optional[AgentWebSocketManager] = None


def get_websocket_manager(agent) -> AgentWebSocketManager:
    """Get or create the WebSocket manager."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = AgentWebSocketManager(agent)
    return _ws_manager


# =============================================================================
# FastAPI Router for WebSocket Endpoint
# =============================================================================

from fastapi import APIRouter

websocket_router = APIRouter()


def _validate_origin(websocket: WebSocket) -> bool:
    """
    Validate the Origin header for WebSocket connections.
    WebSockets don't use CORS headers - origin validation is the security mechanism.
    
    Returns True if:
    - DEBUG mode is enabled
    - Origin header is empty (non-browser clients)
    - Origin matches allowed list
    """
    from app.core.config import settings
    
    origin = websocket.headers.get("origin", "")
    
    # In debug mode, allow all origins
    if settings.DEBUG:
        return True
    
    # Allow non-browser clients that don't send Origin header
    if not origin:
        return True
    
    # Build allowed origins list including CORS settings and local development
    allowed_origins = list(settings.cors_origins_list) if hasattr(settings, 'cors_origins_list') else []
    allowed_origins.extend([
        # HTTP/HTTPS origins
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "https://localhost",
        "https://localhost:3000",
        "https://localhost:8000",
        "https://localhost:8080",
        "https://127.0.0.1",
        "https://127.0.0.1:3000",
        "https://127.0.0.1:8000",
        "https://127.0.0.1:8080",
        # WebSocket origins (ws:// and wss://)
        "ws://localhost",
        "ws://localhost:3000",
        "ws://localhost:8000",
        "ws://localhost:8080",
        "ws://127.0.0.1",
        "ws://127.0.0.1:3000",
        "ws://127.0.0.1:8000",
        "ws://127.0.0.1:8080",
        "wss://localhost",
        "wss://localhost:3000",
        "wss://localhost:8000",
        "wss://localhost:8080",
        "wss://127.0.0.1",
        "wss://127.0.0.1:3000",
        "wss://127.0.0.1:8000",
        "wss://127.0.0.1:8080",
    ])
    
    # Also allow file:// origins for local file-based clients
    if origin.startswith("file://"):
        return True
    
    # Check if origin is in allowed list
    for allowed in allowed_origins:
        if allowed == "*" or origin.startswith(allowed):
            return True
    
    return False


@websocket_router.websocket("/ws")
async def agent_websocket(websocket: WebSocket, client_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time agent communication.
    
    Connect to: ws://host:port/api/v1/agent/v2/ws?client_id=<optional_id>
    """
    from app.agent.core import CerebrumAgent
    
    # Validate origin before accepting connection
    if not _validate_origin(websocket):
        logger.warning(f"WebSocket connection rejected: invalid origin {websocket.headers.get('origin', 'unknown')}")
        # Cannot close before accept - just return to reject the connection
        # The HTTP upgrade will fail with 403
        return
    
    # Generate client ID if not provided
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())
    
    # Get agent instance and manager
    agent = CerebrumAgent()
    manager = get_websocket_manager(agent)
    
    # Accept connection
    connection = await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive and handle messages
            try:
                data = await connection.receive()
                await manager.handle_message(client_id, data)
            except ValueError as e:
                # JSON parsing error
                await connection.send({
                    "type": "error",
                    "message": f"Invalid message format: {str(e)}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
        await manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await manager.disconnect(client_id, code=1011, reason="Internal error")
