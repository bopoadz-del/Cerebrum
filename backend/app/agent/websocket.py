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

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


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
        if not self._closed:
            await self.websocket.send_json(message)
    
    async def send_text(self, text: str):
        """Send text message to the client."""
        if not self._closed:
            await self.websocket.send_text(text)
    
    async def receive(self) -> Dict:
        """Receive a message from the client."""
        data = await self.websocket.receive_text()
        return json.loads(data)
    
    async def close(self):
        """Close the connection."""
        self._closed = True
        await self.websocket.close()
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
    
    async def disconnect(self, client_id: str):
        """Disconnect a client."""
        connection = self.connections.pop(client_id, None)
        if connection:
            await connection.close()
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
                "action": result.action.value,
                "layer": result.layer.value,
                "data": result.data,
                "message": result.message,
                "timestamp": result.timestamp
            })
        
        except Exception as e:
            await connection.send({
                "type": "task_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _handle_plan(self, connection: AgentConnection, data: Dict):
        """Handle multi-step plan execution."""
        from app.agent.planner import MultiStepPlanner
        
        goal = data.get("goal", "")
        context = data.get("context", {})
        
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
                
                # Wait for step to complete
                while step.status.value in ["pending", "running"]:
                    await asyncio.sleep(0.1)
                
                # Send step completed
                await connection.send({
                    "type": "step_completed",
                    "plan_id": plan.id,
                    "step_id": step.id,
                    "status": step.status.value,
                    "result": step.result,
                    "error": step.error,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Send plan completed
            await connection.send({
                "type": "plan_completed",
                "plan_id": plan.id,
                "status": plan.status.value,
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
                "from_layer": original_layer.value,
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
                "layer": result.layer.value,
                "action": result.action.value,
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
        for connection in self.connections.values():
            await connection.send(message)
    
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
