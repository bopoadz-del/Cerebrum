"""
OpenAI Realtime API WebSocket Proxy

Handles audio streaming between browser and OpenAI Realtime API:
- WebRTC audio capture from frontend
- WebSocket connection to OpenAI Realtime API
- Base64 audio chunk encoding/decoding
- Session management and event routing
- Support for interrupting the agent

Architecture:
Browser (WebRTC) ←→ Cerebrum Backend ←→ OpenAI Realtime API
"""

import asyncio
import json
import base64
import logging
from typing import Dict, Optional, Any, Set
from datetime import datetime
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
import websockets

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Voice connection states."""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class VoiceSession:
    """
    Manages a single voice chat session.
    
    Handles the bidirectional audio stream between browser and OpenAI:
    - Receives audio from browser (WebRTC)
    - Proxies to OpenAI Realtime API (WebSocket)
    - Returns audio responses to browser
    """
    
    def __init__(
        self,
        session_id: str,
        browser_ws: WebSocket,
        openai_api_key: str,
        instructions: Optional[str] = None,
        voice: str = "alloy"
    ):
        self.session_id = session_id
        self.browser_ws = browser_ws
        self.openai_api_key = openai_api_key
        self.instructions = instructions or self._default_instructions()
        self.voice = voice
        
        self.state = ConnectionState.IDLE
        self.openai_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._closed = False
        self._tasks: Set[asyncio.Task] = set()
        
        # Audio buffer for playback
        self.audio_buffer: list[str] = []
        self.is_playing = False
        
        # Interrupt handling
        self.current_response_id: Optional[str] = None
        
    def _default_instructions(self) -> str:
        """Default system instructions for the voice assistant."""
        return (
            "You are Cerebrum AI, a construction intelligence assistant. "
            "You help users with construction management, BIM, cost estimation, "
            "and project planning. Be concise, professional, and helpful. "
            "Keep responses brief and natural for voice conversation."
        )
    
    async def start(self):
        """Start the voice session by connecting to OpenAI."""
        self.state = ConnectionState.CONNECTING
        
        try:
            # Connect to OpenAI Realtime API
            openai_url = "wss://api.openai.com/v1/realtime"
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "OpenAI-Beta": "realtime=v1",
            }
            
            self.openai_ws = await websockets.connect(
                openai_url,
                additional_headers=headers
            )
            
            # Initialize session
            await self._send_openai_message({
                "type": "session.update",
                "session": {
                    "instructions": self.instructions,
                    "voice": self.voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                }
            })
            
            self.state = ConnectionState.CONNECTED
            
            # Start proxy tasks
            browser_to_openai = asyncio.create_task(
                self._browser_to_openai_proxy()
            )
            openai_to_browser = asyncio.create_task(
                self._openai_to_browser_proxy()
            )
            
            self._tasks.add(browser_to_openai)
            self._tasks.add(openai_to_browser)
            
            # Clean up tasks when done
            browser_to_openai.add_done_callback(self._tasks.discard)
            openai_to_browser.add_done_callback(self._tasks.discard)
            
            logger.info(f"Voice session started: {self.session_id}")
            
            # Notify browser of connection
            await self._send_browser_message({
                "type": "session.connected",
                "session_id": self.session_id,
                "state": self.state.value
            })
            
        except Exception as e:
            logger.error(f"Failed to start voice session {self.session_id}: {e}")
            self.state = ConnectionState.ERROR
            await self._send_browser_message({
                "type": "session.error",
                "error": str(e),
                "session_id": self.session_id
            })
            raise
    
    async def _browser_to_openai_proxy(self):
        """Proxy audio data from browser to OpenAI."""
        try:
            while not self._closed:
                # Receive message from browser
                data = await self.browser_ws.receive_text()
                message = json.loads(data)
                
                msg_type = message.get("type")
                
                if msg_type == "input_audio_buffer.append":
                    # Forward audio to OpenAI
                    await self._send_openai_message(message)
                    
                elif msg_type == "input_audio_buffer.commit":
                    # Commit audio buffer
                    await self._send_openai_message(message)
                    
                elif msg_type == "conversation.item.create":
                    # Create conversation item
                    await self._send_openai_message(message)
                    
                elif msg_type == "conversation.item.truncate":
                    # Truncate conversation (interrupt)
                    await self._send_openai_message(message)
                    self.state = ConnectionState.LISTENING
                    await self._notify_state_change()
                    
                elif msg_type == "response.create":
                    # Request a response
                    await self._send_openai_message(message)
                    self.state = ConnectionState.PROCESSING
                    await self._notify_state_change()
                    
                elif msg_type == "response.cancel":
                    # Cancel current response
                    await self._send_openai_message(message)
                    self.state = ConnectionState.LISTENING
                    await self._notify_state_change()
                    
                elif msg_type == "session.update":
                    # Update session config
                    await self._send_openai_message(message)
                    
                elif msg_type == "ping":
                    await self._send_browser_message({"type": "pong"})
                    
                else:
                    logger.warning(f"Unknown message type from browser: {msg_type}")
                    
        except WebSocketDisconnect:
            logger.info(f"Browser disconnected: {self.session_id}")
        except Exception as e:
            logger.error(f"Browser proxy error: {e}")
        finally:
            await self.close()
    
    async def _openai_to_browser_proxy(self):
        """Proxy events from OpenAI to browser."""
        try:
            while not self._closed and self.openai_ws:
                # Receive message from OpenAI
                data = await self.openai_ws.recv()
                message = json.loads(data)
                
                msg_type = message.get("type")
                
                # Handle different event types
                if msg_type == "session.created":
                    logger.info(f"OpenAI session created: {message.get('session', {}).get('id')}")
                    await self._send_browser_message(message)
                    
                elif msg_type == "session.updated":
                    await self._send_browser_message(message)
                    
                elif msg_type == "input_audio_buffer.speech_started":
                    self.state = ConnectionState.LISTENING
                    await self._notify_state_change()
                    await self._send_browser_message(message)
                    
                elif msg_type == "input_audio_buffer.speech_stopped":
                    self.state = ConnectionState.PROCESSING
                    await self._notify_state_change()
                    await self._send_browser_message(message)
                    
                elif msg_type == "input_audio_buffer.committed":
                    await self._send_browser_message(message)
                    
                elif msg_type == "conversation.item.created":
                    await self._send_browser_message(message)
                    
                elif msg_type == "conversation.item.input_audio_transcription.completed":
                    # User speech transcribed
                    await self._send_browser_message(message)
                    
                elif msg_type == "response.created":
                    self.current_response_id = message.get("response", {}).get("id")
                    self.state = ConnectionState.SPEAKING
                    await self._notify_state_change()
                    await self._send_browser_message(message)
                    
                elif msg_type == "response.audio.delta":
                    # Audio chunk from OpenAI
                    await self._send_browser_message(message)
                    
                elif msg_type == "response.audio.done":
                    await self._send_browser_message(message)
                    
                elif msg_type == "response.text.delta":
                    # Text transcription of assistant speech
                    await self._send_browser_message(message)
                    
                elif msg_type == "response.done":
                    self.state = ConnectionState.LISTENING
                    self.current_response_id = None
                    await self._notify_state_change()
                    await self._send_browser_message(message)
                    
                elif msg_type == "response.cancelled":
                    self.state = ConnectionState.LISTENING
                    await self._notify_state_change()
                    await self._send_browser_message(message)
                    
                elif msg_type == "error":
                    logger.error(f"OpenAI error: {message.get('error', {})}")
                    await self._send_browser_message(message)
                    
                else:
                    # Forward unknown messages as well
                    await self._send_browser_message(message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"OpenAI connection closed: {self.session_id}")
        except Exception as e:
            logger.error(f"OpenAI proxy error: {e}")
        finally:
            await self.close()
    
    async def _send_openai_message(self, message: Dict[str, Any]):
        """Send a message to OpenAI."""
        if self.openai_ws and not self._closed:
            await self.openai_ws.send(json.dumps(message))
    
    async def _send_browser_message(self, message: Dict[str, Any]):
        """Send a message to the browser."""
        if not self._closed:
            await self.browser_ws.send_json(message)
    
    async def _notify_state_change(self):
        """Notify browser of state change."""
        await self._send_browser_message({
            "type": "state.change",
            "state": self.state.value,
            "session_id": self.session_id
        })
    
    async def interrupt(self):
        """Interrupt the current assistant response."""
        if self.current_response_id:
            await self._send_openai_message({
                "type": "response.cancel"
            })
            await self._send_openai_message({
                "type": "conversation.item.truncate",
                "item_id": self.current_response_id
            })
            self.state = ConnectionState.LISTENING
            await self._notify_state_change()
    
    async def close(self):
        """Close the voice session."""
        if self._closed:
            return
            
        self._closed = True
        self.state = ConnectionState.DISCONNECTED
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Close OpenAI connection
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except Exception as e:
                logger.error(f"Error closing OpenAI websocket: {e}")
        
        logger.info(f"Voice session closed: {self.session_id}")


class VoiceRealtimeProxy:
    """
    Manages multiple voice chat sessions.
    
    Acts as a factory and registry for VoiceSession instances.
    """
    
    def __init__(self):
        self.sessions: Dict[str, VoiceSession] = {}
        self._lock = asyncio.Lock()
    
    async def create_session(
        self,
        session_id: str,
        browser_ws: WebSocket,
        openai_api_key: str,
        instructions: Optional[str] = None,
        voice: str = "alloy"
    ) -> VoiceSession:
        """Create a new voice session."""
        async with self._lock:
            session = VoiceSession(
                session_id=session_id,
                browser_ws=browser_ws,
                openai_api_key=openai_api_key,
                instructions=instructions,
                voice=voice
            )
            self.sessions[session_id] = session
            return session
    
    async def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Get an existing session."""
        return self.sessions.get(session_id)
    
    async def remove_session(self, session_id: str):
        """Remove a session from the registry."""
        async with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                await session.close()
    
    async def cleanup(self):
        """Close all sessions."""
        async with self._lock:
            for session in self.sessions.values():
                await session.close()
            self.sessions.clear()
    
    def get_active_sessions_count(self) -> int:
        """Get number of active sessions."""
        return len(self.sessions)


# Global proxy instance
_voice_proxy: Optional[VoiceRealtimeProxy] = None


def get_voice_proxy() -> VoiceRealtimeProxy:
    """Get or create the global voice proxy."""
    global _voice_proxy
    if _voice_proxy is None:
        _voice_proxy = VoiceRealtimeProxy()
    return _voice_proxy
