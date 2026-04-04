# Voice Chat Feature

Real-time voice chat capability using OpenAI Realtime API.

## Architecture

```
Frontend (WebRTC) ←→ Cerebrum Backend ←→ OpenAI Realtime API
```

## Files Created

### Backend
- `backend/app/voice/__init__.py` - Voice module initialization
- `backend/app/voice/realtime_proxy.py` - WebSocket proxy to OpenAI Realtime API
- `backend/app/api/v1/endpoints/voice.py` - Voice API endpoints

### Frontend
- `frontend/src/hooks/useVoiceChat.ts` - React hook for voice chat
- `frontend/src/components/VoiceChatInterface.tsx` - Voice chat UI component

## API Endpoints

### WebSocket
- `ws://host:port/api/v1/voice/realtime` - Real-time voice connection
  - Query params: `session_id`, `voice`, `instructions`

### REST
- `GET /api/v1/voice/realtime/health` - Health check
- `GET /api/v1/voice/realtime/sessions` - List active sessions
- `POST /api/v1/voice/realtime/sessions/{id}/interrupt` - Interrupt session

## Usage

### Frontend Integration

```tsx
import { VoiceChatInterface } from '@/components/VoiceChatInterface';

function App() {
  return (
    <div className="h-screen">
      <VoiceChatInterface />
    </div>
  );
}
```

### Using the Hook Directly

```tsx
import { useVoiceChat } from '@/hooks/useVoiceChat';

function MyComponent() {
  const {
    state,
    isConnected,
    isListening,
    isSpeaking,
    error,
    transcript,
    aiTranscript,
    connect,
    disconnect,
    interrupt,
  } = useVoiceChat();

  return (
    <button onClick={() => connect('alloy')}>
      Start Voice Chat
    </button>
  );
}
```

## Environment Variables

Add to backend `.env`:
```
OPENAI_API_KEY=your_openai_api_key
```

## Features

- **Real-time audio streaming** - Low latency bidirectional audio
- **Voice activity detection** - Automatic speech detection
- **Multiple voices** - alloy, echo, fable, onyx, nova, shimmer
- **Push-to-talk mode** - Optional manual control
- **Interrupt handling** - Tap to stop AI response
- **Transcript display** - Real-time transcription

## Connection States

- `idle` - Initial state
- `connecting` - Connecting to server
- `connected` - Connected and ready
- `listening` - User is speaking
- `speaking` - AI is speaking
- `processing` - Processing audio
- `disconnected` - Connection closed
- `error` - Error occurred

## Testing

1. Start the backend server
2. Open frontend in browser
3. Click "Start Call" button
4. Allow microphone access
5. Start speaking

## Troubleshooting

- **No microphone access**: Check browser permissions
- **Connection failed**: Verify OpenAI API key is set
- **Audio not playing**: Check audio output device
