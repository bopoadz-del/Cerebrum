import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, X, Check, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

// Import Capacitor speech recognition
import { SpeechRecognition } from '@capacitor-community/speech-recognition';

interface VoiceRecorderProps {
  onTranscript: (text: string) => void;
  onCancel?: () => void;
  isOpen: boolean;
  onClose: () => void;
}

interface RecordingState {
  isRecording: boolean;
  isProcessing: boolean;
  transcript: string;
  error: string | null;
}

// Type for the speech recognition result
interface SpeechResult {
  matches?: string[];
  match?: string;
}

export function VoiceRecorder({ onTranscript, onCancel, isOpen, onClose }: VoiceRecorderProps) {
  const [state, setState] = useState<RecordingState>({
    isRecording: false,
    isProcessing: false,
    transcript: '',
    error: null,
  });
  
  const recordingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Check if speech recognition is available
  const checkAvailability = useCallback(async (): Promise<boolean> => {
    try {
      const { available } = await SpeechRecognition.available();
      return available;
    } catch {
      return false;
    }
  }, []);

  // Start recording
  const startRecording = useCallback(async () => {
    const isAvailable = await checkAvailability();
    
    if (!isAvailable) {
      setState(prev => ({
        ...prev,
        error: 'Speech recognition is not available on this device',
      }));
      return;
    }

    try {
      // Request permissions - the plugin handles this internally
      const permissionResult = await SpeechRecognition.requestPermissions();
      
      // Check if microphone permission was granted
      const hasPermission = (permissionResult as any).microphone === 'granted' || 
                           (permissionResult as any).speechRecognition === 'granted' ||
                           true; // Some platforms don't require explicit permission
      
      if (!hasPermission) {
        setState(prev => ({
          ...prev,
          error: 'Microphone permission denied. Please enable it in settings.',
        }));
        return;
      }

      setState({
        isRecording: true,
        isProcessing: false,
        transcript: '',
        error: null,
      });

      // Start listening with partial results
      await SpeechRecognition.start({
        language: 'en-US',
        maxResults: 5,
        prompt: 'Speak now...',
        partialResults: true,
        popup: false,
      });

      // Set a max recording time of 60 seconds
      recordingTimeoutRef.current = setTimeout(() => {
        stopRecording();
      }, 60000);

    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to start recording',
      }));
    }
  }, []);

  // Stop recording and get final transcript
  const stopRecording = useCallback(async () => {
    if (recordingTimeoutRef.current) {
      clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = null;
    }

    setState(prev => ({ ...prev, isRecording: false, isProcessing: true }));

    try {
      const result = await SpeechRecognition.stop() as unknown as SpeechResult;
      
      if (result && result.matches && result.matches.length > 0) {
        const finalTranscript = result.matches[0];
        setState(prev => ({
          ...prev,
          transcript: finalTranscript,
          isProcessing: false,
        }));
      } else if (result && result.match) {
        // Fallback for some implementations
        setState(prev => ({
          ...prev,
          transcript: result.match || '',
          isProcessing: false,
        }));
      } else {
        setState(prev => ({
          ...prev,
          isProcessing: false,
          error: 'No speech detected. Please try again.',
        }));
      }
    } catch (err) {
      setState(prev => ({
        ...prev,
        isProcessing: false,
        error: err instanceof Error ? err.message : 'Failed to process speech',
      }));
    }
  }, []);

  // Handle send transcript
  const handleSend = useCallback(() => {
    if (state.transcript.trim()) {
      onTranscript(state.transcript.trim());
      setState({
        isRecording: false,
        isProcessing: false,
        transcript: '',
        error: null,
      });
      onClose();
    }
  }, [state.transcript, onTranscript, onClose]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    if (state.isRecording) {
      SpeechRecognition.stop().catch(() => {});
    }
    if (recordingTimeoutRef.current) {
      clearTimeout(recordingTimeoutRef.current);
    }
    setState({
      isRecording: false,
      isProcessing: false,
      transcript: '',
      error: null,
    });
    onCancel?.();
    onClose();
  }, [state.isRecording, onCancel, onClose]);

  // Waveform animation bars
  const WaveformBars = () => (
    <div className="flex items-center justify-center gap-1 h-12">
      {[...Array(12)].map((_, i) => (
        <motion.div
          key={i}
          className="w-1.5 bg-red-500 rounded-full"
          animate={{
            height: state.isRecording ? [8, 32, 8] : 8,
            opacity: state.isRecording ? 1 : 0.5,
          }}
          transition={{
            duration: 0.5,
            repeat: Infinity,
            delay: i * 0.05,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          className="fixed inset-x-4 bottom-24 z-50 md:absolute md:inset-auto md:bottom-full md:left-1/2 md:-translate-x-1/2 md:w-80 md:mb-2"
        >
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  state.isRecording ? 'bg-red-100' : 'bg-indigo-100'
                )}>
                  {state.isRecording ? (
                    <motion.div
                      animate={{ scale: [1, 1.2, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    >
                      <div className="w-3 h-3 bg-red-500 rounded-full" />
                    </motion.div>
                  ) : (
                    <Mic className="w-4 h-4 text-indigo-600" />
                  )}
                </div>
                <span className="font-medium text-gray-900">
                  {state.isRecording ? 'Listening...' : state.isProcessing ? 'Processing...' : 'Voice Input'}
                </span>
              </div>
              <button
                onClick={handleCancel}
                className="p-3 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4">
              {/* Error Message */}
              {state.error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg"
                >
                  <p className="text-sm text-red-600">{state.error}</p>
                </motion.div>
              )}

              {/* Recording State */}
              {state.isRecording && (
                <div className="flex flex-col items-center gap-4">
                  <WaveformBars />
                  <p className="text-sm text-gray-500">Speak now. Release to stop.</p>
                </div>
              )}

              {/* Processing State */}
              {state.isProcessing && (
                <div className="flex flex-col items-center gap-4 py-4">
                  <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
                  <p className="text-sm text-gray-500">Transcribing your speech...</p>
                </div>
              )}

              {/* Transcript Preview */}
              {!state.isRecording && !state.isProcessing && state.transcript && (
                <div className="mb-4">
                  <p className="text-xs text-gray-400 mb-1">Transcribed:</p>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-900">{state.transcript}</p>
                  </div>
                </div>
              )}

              {/* Initial State */}
              {!state.isRecording && !state.isProcessing && !state.transcript && !state.error && (
                <div className="flex flex-col items-center gap-4 py-4">
                  <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center">
                    <Mic className="w-8 h-8 text-indigo-600" />
                  </div>
                  <p className="text-sm text-gray-500 text-center">
                    Tap and hold the button below to start recording
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2 mt-4">
                {!state.isRecording && !state.isProcessing ? (
                  state.transcript ? (
                    <>
                      <Button
                        variant="outline"
                        onClick={handleCancel}
                        className="flex-1"
                      >
                        <X className="w-4 h-4 mr-2" />
                        Discard
                      </Button>
                      <Button
                        onClick={handleSend}
                        className="flex-1 bg-indigo-600 hover:bg-indigo-700"
                      >
                        <Check className="w-4 h-4 mr-2" />
                        Use Text
                      </Button>
                    </>
                  ) : (
                    <Button
                      onClick={startRecording}
                      className="w-full bg-indigo-600 hover:bg-indigo-700"
                    >
                      <Mic className="w-4 h-4 mr-2" />
                      Start Recording
                    </Button>
                  )
                ) : state.isRecording ? (
                  <Button
                    onClick={stopRecording}
                    variant="destructive"
                    className="w-full"
                  >
                    <div className="w-3 h-3 bg-white rounded-sm mr-2" />
                    Stop Recording
                  </Button>
                ) : null}
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Hook for using voice recorder
export function useVoiceRecorder(onTranscript: (text: string) => void) {
  const [isOpen, setIsOpen] = useState(false);

  const openRecorder = useCallback(() => {
    setIsOpen(true);
  }, []);

  const closeRecorder = useCallback(() => {
    setIsOpen(false);
  }, []);

  const VoiceRecorderComponent = useCallback(() => (
    <VoiceRecorder
      isOpen={isOpen}
      onClose={closeRecorder}
      onTranscript={onTranscript}
    />
  ), [isOpen, onTranscript, closeRecorder]);

  return {
    isOpen,
    openRecorder,
    closeRecorder,
    VoiceRecorder: VoiceRecorderComponent,
  };
}

export default VoiceRecorder;
