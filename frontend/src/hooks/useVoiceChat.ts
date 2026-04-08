import { useState, useCallback, useRef, useEffect } from 'react';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

// Connection states
type VoiceConnectionState = 
  | 'idle' 
  | 'connecting' 
  | 'connected' 
  | 'listening' 
  | 'speaking' 
  | 'processing' 
  | 'disconnected' 
  | 'error';

// Voice options
export type VoiceOption = 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer';

// Audio configuration
const AUDIO_CONFIG = {
  sampleRate: 24000,  // OpenAI Realtime API uses 24kHz
  channelCount: 1,    // Mono
  bufferSize: 4096,
};

export interface VoiceChatState {
  state: VoiceConnectionState;
  isConnected: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  error: string | null;
  transcript: string;
  aiTranscript: string;
}

export interface VoiceChatActions {
  connect: (voice?: VoiceOption, instructions?: string) => Promise<void>;
  disconnect: () => void;
  startListening: () => void;
  stopListening: () => void;
  interrupt: () => void;
}

export interface VoiceChatHook extends VoiceChatState, VoiceChatActions {}

/**
 * React hook for real-time voice chat with OpenAI Realtime API
 * 
 * Features:
 * - WebRTC audio capture
 * - WebSocket connection to backend
 * - Audio playback
 * - Voice activity detection
 * - Interrupt handling
 */
export function useVoiceChat(): VoiceChatHook {
  // State
  const [state, setState] = useState<VoiceConnectionState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');
  const [aiTranscript, setAiTranscript] = useState('');

  // Refs for internal state that doesn't trigger re-renders
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const playbackQueueRef = useRef<Int16Array[]>([]);
  const isPlayingRef = useRef(false);
  const sessionIdRef = useRef<string>('');
  const currentResponseIdRef = useRef<string | null>(null);

  // Derived state
  const isConnected = state === 'connected' || state === 'listening' || state === 'speaking' || state === 'processing';
  const isListening = state === 'listening';
  const isSpeaking = state === 'speaking';

  /**
   * Convert Float32 audio to Int16 (PCM16)
   */
  const floatToInt16 = useCallback((float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
  }, []);

  /**
   * Convert Int16 audio to Float32
   */
  const int16ToFloat = useCallback((int16Array: Int16Array): Float32Array => {
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
    }
    return float32Array;
  }, []);

  /**
   * Base64 encode Int16Array
   */
  const base64EncodeAudio = useCallback((int16Array: Int16Array): string => {
    const uint8Array = new Uint8Array(int16Array.buffer);
    let binary = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binary += String.fromCharCode(uint8Array[i]);
    }
    return btoa(binary);
  }, []);

  /**
   * Base64 decode to Int16Array
   */
  const base64DecodeAudio = useCallback((base64: string): Int16Array => {
    const binary = atob(base64);
    const uint8Array = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      uint8Array[i] = binary.charCodeAt(i);
    }
    return new Int16Array(uint8Array.buffer);
  }, []);

  /**
   * Play audio from the queue
   */
  const playNextAudioChunk = useCallback(async () => {
    if (isPlayingRef.current || playbackQueueRef.current.length === 0) {
      return;
    }

    isPlayingRef.current = true;
    const audioContext = audioContextRef.current;
    if (!audioContext) return;

    const int16Data = playbackQueueRef.current.shift()!;
    const float32Data = int16ToFloat(int16Data);

    // Create audio buffer
    const audioBuffer = audioContext.createBuffer(1, float32Data.length, AUDIO_CONFIG.sampleRate);
    audioBuffer.getChannelData(0).set(float32Data);

    // Create source and play
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    
    source.onended = () => {
      isPlayingRef.current = false;
      playNextAudioChunk();
    };

    source.start();
  }, [int16ToFloat]);

  /**
   * Queue audio for playback
   */
  const queueAudio = useCallback((base64Audio: string) => {
    const int16Data = base64DecodeAudio(base64Audio);
    playbackQueueRef.current.push(int16Data);
    playNextAudioChunk();
  }, [base64DecodeAudio, playNextAudioChunk]);

  /**
   * Send audio data to server
   */
  const sendAudioData = useCallback((int16Data: Int16Array) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const base64Audio = base64EncodeAudio(int16Data);
      wsRef.current.send(JSON.stringify({
        type: 'input_audio_buffer.append',
        audio: base64Audio,
      }));
    }
  }, [base64EncodeAudio]);

  /**
   * Initialize audio worklet for processing
   */
  const initializeAudioWorklet = useCallback(async (audioContext: AudioContext) => {
    // Create inline audio worklet processor
    const workletCode = `
      class PCMProcessor extends AudioWorkletProcessor {
        constructor() {
          super();
          this.buffer = new Float32Array(0);
        }

        process(inputs, outputs, parameters) {
          const input = inputs[0];
          if (input.length === 0) return true;

          const channelData = input[0];
          
          // Accumulate samples
          const newBuffer = new Float32Array(this.buffer.length + channelData.length);
          newBuffer.set(this.buffer);
          newBuffer.set(channelData, this.buffer.length);
          this.buffer = newBuffer;

          // Send in chunks of 4800 samples (0.2s at 24kHz)
          const chunkSize = 4800;
          while (this.buffer.length >= chunkSize) {
            const chunk = this.buffer.slice(0, chunkSize);
            this.port.postMessage({ samples: chunk });
            this.buffer = this.buffer.slice(chunkSize);
          }

          return true;
        }
      }

      registerProcessor('pcm-processor', PCMProcessor);
    `;

    const blob = new Blob([workletCode], { type: 'application/javascript' });
    const url = URL.createObjectURL(blob);
    
    try {
      await audioContext.audioWorklet.addModule(url);
      
      const workletNode = new AudioWorkletNode(audioContext, 'pcm-processor');
      
      workletNode.port.onmessage = (event) => {
        const float32Data = event.data.samples;
        const int16Data = floatToInt16(float32Data);
        sendAudioData(int16Data);
      };

      workletNodeRef.current = workletNode;
    } finally {
      URL.revokeObjectURL(url);
    }
  }, [sendAudioData]);

  /**
   * Connect to voice chat
   */
  const connect = useCallback(async (voice: VoiceOption = 'alloy', instructions?: string) => {
    try {
      setState('connecting');
      setError(null);

      // Generate session ID
      sessionIdRef.current = `voice_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Initialize audio context
      const audioContext = new AudioContext({
        sampleRate: AUDIO_CONFIG.sampleRate,
      });
      audioContextRef.current = audioContext;

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: AUDIO_CONFIG.channelCount,
          sampleRate: AUDIO_CONFIG.sampleRate,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;

      // Create media source
      const source = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      // Initialize audio worklet
      await initializeAudioWorklet(audioContext);

      // Connect source to worklet
      if (workletNodeRef.current) {
        source.connect(workletNodeRef.current);
      }

      // Connect WebSocket
      const wsUrl = new URL(`${WS_BASE_URL}/voice/realtime`);
      wsUrl.searchParams.set('session_id', sessionIdRef.current);
      wsUrl.searchParams.set('voice', voice);
      if (instructions) {
        wsUrl.searchParams.set('instructions', instructions);
      }

      const ws = new WebSocket(wsUrl.toString());
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Voice WebSocket connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleServerMessage(message);
      };

      ws.onerror = (error) => {
        console.error('Voice WebSocket error:', error);
        setError('Connection error');
        setState('error');
      };

      ws.onclose = () => {
        console.log('Voice WebSocket closed');
        setState('disconnected');
      };

    } catch (err) {
      console.error('Failed to connect voice chat:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect');
      setState('error');
    }
  }, [initializeAudioWorklet]);

  /**
   * Handle messages from server
   */
  const handleServerMessage = useCallback((message: any) => {
    const msgType = message.type;

    switch (msgType) {
      case 'session.connected':
        setState('connected');
        break;

      case 'state.change':
        setState(message.state);
        break;

      case 'input_audio_buffer.speech_started':
        setState('listening');
        break;

      case 'input_audio_buffer.speech_stopped':
        setState('processing');
        break;

      case 'conversation.item.input_audio_transcription.completed':
        if (message.transcript) {
          setTranscript(prev => prev + ' ' + message.transcript);
        }
        break;

      case 'response.created':
        setState('speaking');
        currentResponseIdRef.current = message.response?.id || null;
        break;

      case 'response.audio.delta':
        if (message.delta) {
          queueAudio(message.delta);
        }
        break;

      case 'response.text.delta':
        if (message.delta) {
          setAiTranscript(prev => prev + message.delta);
        }
        break;

      case 'response.done':
        setState('listening');
        currentResponseIdRef.current = null;
        break;

      case 'response.cancelled':
        setState('listening');
        playbackQueueRef.current = [];
        currentResponseIdRef.current = null;
        break;

      case 'session.error':
        setError(message.error || 'Unknown error');
        setState('error');
        break;

      case 'error':
        console.error('Server error:', message.error);
        break;

      default:
        // Ignore unknown message types
        break;
    }
  }, [queueAudio]);

  /**
   * Disconnect from voice chat
   */
  const disconnect = useCallback(() => {
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    // Disconnect audio nodes
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Clear playback queue
    playbackQueueRef.current = [];
    isPlayingRef.current = false;

    setState('disconnected');
  }, []);

  /**
   * Start listening (manually trigger listening mode)
   */
  const startListening = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // Resume audio context if suspended
      if (audioContextRef.current?.state === 'suspended') {
        audioContextRef.current.resume();
      }
      setState('listening');
    }
  }, []);

  /**
   * Stop listening
   */
  const stopListening = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'input_audio_buffer.commit',
      }));
    }
  }, []);

  /**
   * Interrupt current AI response
   */
  const interrupt = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'response.cancel',
      }));
      
      if (currentResponseIdRef.current) {
        wsRef.current.send(JSON.stringify({
          type: 'conversation.item.truncate',
          item_id: currentResponseIdRef.current,
        }));
      }
      
      // Clear playback queue
      playbackQueueRef.current = [];
      isPlayingRef.current = false;
      
      setState('listening');
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    state,
    isConnected,
    isListening,
    isSpeaking,
    error,
    transcript,
    aiTranscript,
    connect,
    disconnect,
    startListening,
    stopListening,
    interrupt,
  };
}

export default useVoiceChat;
