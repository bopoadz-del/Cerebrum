import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mic, 
  MicOff, 
  PhoneOff, 
  Phone, 
  Settings,
  Volume2,
  MessageSquare,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useVoiceChat, type VoiceOption } from '@/hooks/useVoiceChat';
import { cn } from '@/lib/utils';

// Voice options with descriptions
const VOICE_OPTIONS: { value: VoiceOption; label: string; description: string }[] = [
  { value: 'alloy', label: 'Alloy', description: 'Balanced and neutral' },
  { value: 'echo', label: 'Echo', description: 'Warm and soft' },
  { value: 'fable', label: 'Fable', description: 'British accent' },
  { value: 'onyx', label: 'Onyx', description: 'Deep and authoritative' },
  { value: 'nova', label: 'Nova', description: 'Energetic and bright' },
  { value: 'shimmer', label: 'Shimmer', description: 'Clear and crisp' },
];

// Connection state display mapping
const STATE_DISPLAY: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  idle: { 
    label: 'Ready', 
    color: 'text-gray-500', 
    icon: <Mic className="w-5 h-5" /> 
  },
  connecting: { 
    label: 'Connecting...', 
    color: 'text-yellow-500', 
    icon: <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" /> 
  },
  connected: { 
    label: 'Connected', 
    color: 'text-green-500', 
    icon: <CheckCircle2 className="w-5 h-5" /> 
  },
  listening: { 
    label: 'Listening...', 
    color: 'text-blue-500', 
    icon: <Volume2 className="w-5 h-5" /> 
  },
  speaking: { 
    label: 'Speaking...', 
    color: 'text-purple-500', 
    icon: <Volume2 className="w-5 h-5" /> 
  },
  processing: { 
    label: 'Processing...', 
    color: 'text-orange-500', 
    icon: <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" /> 
  },
  disconnected: { 
    label: 'Disconnected', 
    color: 'text-gray-500', 
    icon: <PhoneOff className="w-5 h-5" /> 
  },
  error: { 
    label: 'Error', 
    color: 'text-red-500', 
    icon: <AlertCircle className="w-5 h-5" /> 
  },
};

interface VoiceChatInterfaceProps {
  className?: string;
}

/**
 * Voice Chat Interface Component
 * 
 * Provides a visual interface for real-time voice chat with the AI.
 * Features:
 * - Push-to-talk or continuous mode
 * - Visual feedback for connection status
 * - Voice selection
 * - Transcript display
 * - Interrupt capability
 */
export function VoiceChatInterface({ className }: VoiceChatInterfaceProps) {
  const voiceChat = useVoiceChat();
  const [selectedVoice, setSelectedVoice] = useState<VoiceOption>('alloy');
  const [showSettings, setShowSettings] = useState(false);
  const [showTranscript, setShowTranscript] = useState(true);
  const [pushToTalk, setPushToTalk] = useState(false);
  const [isPressed, setIsPressed] = useState(false);

  const stateDisplay = STATE_DISPLAY[voiceChat.state] || STATE_DISPLAY.idle;

  // Handle connect button
  const handleConnect = useCallback(() => {
    voiceChat.connect(selectedVoice);
  }, [voiceChat, selectedVoice]);

  // Handle disconnect
  const handleDisconnect = useCallback(() => {
    voiceChat.disconnect();
  }, [voiceChat]);

  // Handle push-to-talk start
  const handleTalkStart = useCallback(() => {
    setIsPressed(true);
    if (voiceChat.isConnected) {
      voiceChat.startListening();
    }
  }, [voiceChat]);

  // Handle push-to-talk end
  const handleTalkEnd = useCallback(() => {
    setIsPressed(false);
    if (voiceChat.isConnected) {
      voiceChat.stopListening();
    }
  }, [voiceChat]);

  // Handle interrupt
  const handleInterrupt = useCallback(() => {
    voiceChat.interrupt();
  }, [voiceChat]);

  // Determine if we should show the main talk button
  const showTalkButton = voiceChat.isConnected && pushToTalk;
  const showContinuousButton = voiceChat.isConnected && !pushToTalk;

  return (
    <div className={cn(
      "flex flex-col h-full bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden",
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
            voiceChat.isConnected ? "bg-indigo-100 text-indigo-600" : "bg-gray-100 text-gray-500"
          )}>
            <Phone className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Voice Chat</h3>
            <div className="flex items-center gap-2 text-sm">
              <span className={stateDisplay.color}>
                {stateDisplay.icon}
              </span>
              <span className={cn("font-medium", stateDisplay.color)}>
                {stateDisplay.label}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Settings button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowSettings(!showSettings)}
            className={cn(showSettings && "bg-gray-200")}
          >
            <Settings className="w-4 h-4" />
          </Button>

          {/* Transcript toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowTranscript(!showTranscript)}
            className={cn(showTranscript && "bg-gray-200")}
          >
            <MessageSquare className="w-4 h-4" />
          </Button>

          {/* Connect/Disconnect button */}
          {voiceChat.isConnected ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDisconnect}
              className="gap-2"
            >
              <PhoneOff className="w-4 h-4" />
              End Call
            </Button>
          ) : (
            <Button
              variant="default"
              size="sm"
              onClick={handleConnect}
              disabled={voiceChat.state === 'connecting'}
              className="gap-2 bg-indigo-600 hover:bg-indigo-700"
            >
              <Phone className="w-4 h-4" />
              {voiceChat.state === 'connecting' ? 'Connecting...' : 'Start Call'}
            </Button>
          )}
        </div>
      </div>

      {/* Settings Panel */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-b border-gray-200 bg-gray-50 overflow-hidden"
          >
            <div className="p-4 space-y-4">
              {/* Voice selection */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Voice
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {VOICE_OPTIONS.map((voice) => (
                    <button
                      key={voice.value}
                      onClick={() => setSelectedVoice(voice.value)}
                      disabled={voiceChat.isConnected}
                      className={cn(
                        "px-3 py-2 text-left rounded-lg border transition-all text-sm",
                        selectedVoice === voice.value
                          ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                          : "border-gray-200 hover:border-gray-300 bg-white",
                        voiceChat.isConnected && "opacity-50 cursor-not-allowed"
                      )}
                    >
                      <div className="font-medium">{voice.label}</div>
                      <div className="text-xs text-gray-500">{voice.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Mode toggle */}
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">
                  Push-to-Talk Mode
                </label>
                <button
                  onClick={() => setPushToTalk(!pushToTalk)}
                  className={cn(
                    "relative w-11 h-6 rounded-full transition-colors",
                    pushToTalk ? "bg-indigo-600" : "bg-gray-300"
                  )}
                >
                  <span
                    className={cn(
                      "absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform",
                      pushToTalk ? "translate-x-5" : "translate-x-0"
                    )}
                  />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Visualizer / Status Area */}
        <div className="flex-1 flex items-center justify-center relative">
          {/* Connection visualizer */}
          <div className="relative">
            {/* Animated rings when listening/speaking */}
            {(voiceChat.isListening || voiceChat.isSpeaking) && (
              <>
                <motion.div
                  className={cn(
                    "absolute inset-0 rounded-full",
                    voiceChat.isListening ? "bg-blue-400" : "bg-purple-400"
                  )}
                  initial={{ scale: 1, opacity: 0.3 }}
                  animate={{ scale: 1.5, opacity: 0 }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                <motion.div
                  className={cn(
                    "absolute inset-0 rounded-full",
                    voiceChat.isListening ? "bg-blue-400" : "bg-purple-400"
                  )}
                  initial={{ scale: 1, opacity: 0.3 }}
                  animate={{ scale: 1.5, opacity: 0 }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: 0.5 }}
                />
              </>
            )}

            {/* Main circle */}
            <div
              className={cn(
                "w-32 h-32 rounded-full flex items-center justify-center transition-all",
                voiceChat.isListening && "bg-blue-100 scale-110",
                voiceChat.isSpeaking && "bg-purple-100 scale-110",
                voiceChat.state === 'processing' && "bg-orange-100",
                !voiceChat.isConnected && "bg-gray-100",
                voiceChat.isConnected && !voiceChat.isListening && !voiceChat.isSpeaking && voiceChat.state !== 'processing' && "bg-green-100"
              )}
            >
              {voiceChat.isListening ? (
                <Mic className="w-12 h-12 text-blue-500" />
              ) : voiceChat.isSpeaking ? (
                <Volume2 className="w-12 h-12 text-purple-500" />
              ) : voiceChat.state === 'processing' ? (
                <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
              ) : voiceChat.isConnected ? (
                <CheckCircle2 className="w-12 h-12 text-green-500" />
              ) : (
                <MicOff className="w-12 h-12 text-gray-400" />
              )}
            </div>
          </div>

          {/* Interrupt button (when AI is speaking) */}
          {voiceChat.isSpeaking && (
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              onClick={handleInterrupt}
              className="absolute bottom-8 px-4 py-2 bg-red-500 text-white rounded-full font-medium shadow-lg hover:bg-red-600 transition-colors"
            >
              Tap to interrupt
            </motion.button>
          )}
        </div>

        {/* Push-to-Talk Button */}
        {showTalkButton && (
          <div className="p-4 flex justify-center">
            <button
              onMouseDown={handleTalkStart}
              onMouseUp={handleTalkEnd}
              onTouchStart={handleTalkStart}
              onTouchEnd={handleTalkEnd}
              onMouseLeave={() => isPressed && handleTalkEnd()}
              className={cn(
                "w-full max-w-xs py-4 rounded-2xl font-semibold text-lg transition-all select-none",
                isPressed
                  ? "bg-blue-600 text-white scale-95 shadow-inner"
                  : "bg-blue-500 text-white hover:bg-blue-600 shadow-lg"
              )}
            >
              {isPressed ? 'Listening...' : 'Hold to Talk'}
            </button>
          </div>
        )}

        {/* Continuous Mode Indicator */}
        {showContinuousButton && (
          <div className="p-4 text-center">
            <p className="text-sm text-gray-500">
              Voice activity detection is active. Just start speaking.
            </p>
          </div>
        )}

        {/* Error display */}
        {voiceChat.error && (
          <div className="p-4 mx-4 mb-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm font-medium">{voiceChat.error}</span>
            </div>
          </div>
        )}

        {/* Transcript Panel */}
        <AnimatePresence>
          {showTranscript && voiceChat.isConnected && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="border-t border-gray-200 bg-gray-50 overflow-hidden"
            >
              <div className="p-4 max-h-48 overflow-y-auto">
                {/* User transcript */}
                {voiceChat.transcript && (
                  <div className="mb-3">
                    <div className="text-xs font-medium text-gray-500 mb-1">You</div>
                    <div className="text-sm text-gray-800 bg-white p-3 rounded-lg border border-gray-200">
                      {voiceChat.transcript}
                    </div>
                  </div>
                )}

                {/* AI transcript */}
                {voiceChat.aiTranscript && (
                  <div>
                    <div className="text-xs font-medium text-indigo-500 mb-1">AI</div>
                    <div className="text-sm text-gray-800 bg-indigo-50 p-3 rounded-lg border border-indigo-100">
                      {voiceChat.aiTranscript}
                    </div>
                  </div>
                )}

                {!voiceChat.transcript && !voiceChat.aiTranscript && (
                  <div className="text-center text-gray-400 text-sm py-4">
                    Start speaking to see the transcript...
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default VoiceChatInterface;
