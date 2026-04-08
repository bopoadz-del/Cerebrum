"""
Voice Chat API Endpoints

Provides WebSocket endpoint for real-time voice chat using OpenAI Realtime API.

Endpoint: /api/v1/voice/realtime

Features:
- WebSocket connection for bidirectional audio streaming
- Session management
- Support for multiple voice configurations
- Health check endpoint
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.voice.realtime_proxy import get_voice_proxy, ConnectionState
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def get_openai_api_key() -> str:
    """Get OpenAI API key from settings or environment."""
    api_key = getattr(settings, 'OPENAI_API_KEY', None) or getattr(settings, 'openai_api_key', None)
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured"
        )
    return api_key


@router.get("/realtime/health")
async def voice_health_check():
    """
    Health check for voice chat service.
    
    Returns:
        Status of the voice chat service
    """
    proxy = get_voice_proxy()
    
    # Check if OpenAI API key is configured
    try:
        api_key = get_openai_api_key()
        configured = bool(api_key)
    except HTTPException:
        configured = False
    
    return {
        "status": "healthy" if configured else "unconfigured",
        "service": "voice_realtime",
        "openai_configured": configured,
        "active_sessions": proxy.get_active_sessions_count(),
        "supported_voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        "features": [
            "realtime_audio_streaming",
            "voice_activity_detection",
            "interrupt_handling",
            "session_management"
        ]
    }


@router.websocket("/realtime")
async def voice_realtime_websocket(
    websocket: WebSocket,
    session_id: Optional[str] = None,
    voice: str = "alloy",
    instructions: Optional[str] = None
):
    """
    WebSocket endpoint for real-time voice chat with OpenAI.
    
    Connect to: ws://host:port/api/v1/voice/realtime
    
    Query Parameters:
        - session_id: Optional client-provided session ID
        - voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        - instructions: Custom system instructions
    
    Protocol:
        1. Client connects via WebSocket
        2. Server establishes connection to OpenAI Realtime API
        3. Bidirectional audio streaming begins
        4. Server forwards events between client and OpenAI
    
    Client → Server Messages:
        - input_audio_buffer.append: Append audio (base64 PCM16)
        - input_audio_buffer.commit: Commit audio buffer
        - conversation.item.create: Add text to conversation
        - conversation.item.truncate: Truncate/interrupt
        - response.create: Request AI response
        - response.cancel: Cancel current response
        - session.update: Update session config
        - ping: Heartbeat
    
    Server → Client Messages:
        - session.connected: Connection established
        - session.created: OpenAI session created
        - session.updated: Session config updated
        - state.change: Connection state changed
        - input_audio_buffer.speech_started: User started speaking
        - input_audio_buffer.speech_stopped: User stopped speaking
        - input_audio_buffer.committed: Audio buffer committed
        - conversation.item.created: Conversation item added
        - conversation.item.input_audio_transcription.completed: User speech transcribed
        - response.created: AI response started
        - response.audio.delta: Audio chunk from AI
        - response.audio.done: Audio response complete
        - response.text.delta: Text transcription delta
        - response.done: Response complete
        - response.cancelled: Response was cancelled
        - error: Error message
        - pong: Heartbeat response
    
    States:
        - idle: Initial state
        - connecting: Connecting to OpenAI
        - connected: Connected and ready
        - listening: User is speaking
        - speaking: AI is speaking
        - processing: Processing audio/transcription
        - disconnected: Connection closed
        - error: Error occurred
    """
    import uuid
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    logger.info(f"Voice WebSocket connection request: {session_id}")
    
    # Get OpenAI API key
    try:
        openai_api_key = get_openai_api_key()
    except HTTPException as e:
        logger.error(f"OpenAI API key not configured: {e}")
        await websocket.accept()
        await websocket.send_json({
            "type": "session.error",
            "error": "OpenAI API key not configured",
            "session_id": session_id
        })
        await websocket.close(code=1011, reason="Service unavailable")
        return
    
    # Accept WebSocket connection
    await websocket.accept()
    logger.info(f"Voice WebSocket accepted: {session_id}")
    
    # Get proxy and create session
    proxy = get_voice_proxy()
    
    try:
        # Create voice session
        session = await proxy.create_session(
            session_id=session_id,
            browser_ws=websocket,
            openai_api_key=openai_api_key,
            instructions=instructions,
            voice=voice
        )
        
        # Start the session (this begins the proxy loops)
        await session.start()
        
    except WebSocketDisconnect:
        logger.info(f"Client disconnected during session setup: {session_id}")
    except Exception as e:
        logger.error(f"Voice session error: {e}")
        try:
            await websocket.send_json({
                "type": "session.error",
                "error": str(e),
                "session_id": session_id
            })
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
    finally:
        # Clean up session
        await proxy.remove_session(session_id)
        logger.info(f"Voice session cleanup complete: {session_id}")


@router.get("/realtime/sessions")
async def list_voice_sessions():
    """
    List active voice sessions (admin/debug endpoint).
    
    Returns:
        Count and list of active session IDs
    """
    proxy = get_voice_proxy()
    count = proxy.get_active_sessions_count()
    
    return {
        "active_sessions": count,
        "sessions": list(proxy.sessions.keys()) if hasattr(proxy, 'sessions') else []
    }


@router.post("/realtime/sessions/{session_id}/interrupt")
async def interrupt_voice_session(session_id: str):
    """
    Interrupt a specific voice session (admin/debug endpoint).
    
    Args:
        session_id: The session ID to interrupt
    
    Returns:
        Success status
    """
    proxy = get_voice_proxy()
    session = await proxy.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await session.interrupt()
    
    return {
        "success": True,
        "message": f"Session {session_id} interrupted",
        "state": session.state.value
    }
