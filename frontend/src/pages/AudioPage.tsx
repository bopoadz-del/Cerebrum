import { useState } from 'react';
import { motion } from 'framer-motion';
import { Mic, Clock, MessageSquare, AlertCircle, FileAudio, Languages, Loader2 } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { processAudio, indexToChatWithSession, type ProcessingResult } from '@/lib/fileProcessing';

interface TranscriptionSegment {
  start: number;
  end: number;
  text: string;
}

interface AnalysisResult {
  id: string;
  fileName: string;
  status: 'completed' | 'error';
  summary: string;
  indexed?: boolean;
  processingTime?: number;
  details: {
    duration: number;
    durationFormatted: string;
    language: string;
    wordCount: number;
    transcription: string;
    segments: TranscriptionSegment[];
  };
}

const ACCEPTED_FORMATS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.mp4', '.webm'];
const MAX_FILE_SIZE = 100; // MB

// Get session ID from localStorage (set by chat interface)
const getSessionId = () => localStorage.getItem('cerebrum_chat_session_id') || undefined;

export default function AudioPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);

  const handleUpload = async (file: File) => {
    
    setIsAnalyzing(true);
    setError(null);
    setResult(null);
    setProcessingResult(null);

    // Process the audio
    const processed = await processAudio(file, (stage) => {
      console.log(`Audio ${stage}: ${file.name}`);
    });

    setIsAnalyzing(false);

    if (!processed.success) {
      setError(processed.error || 'Processing failed');
      toast.error(processed.error || 'Failed to transcribe audio');
      return;
    }

    setProcessingResult(processed);

    // Parse segments if available
    const segments: TranscriptionSegment[] = [];
    // Note: Full segments would come from API - simplified here

    const analysisResult: AnalysisResult = {
      id: `audio_${Date.now()}`,
      fileName: file.name,
      status: 'completed',
      summary: `Audio transcribed: ${processed.metadata.wordCount} words in ${processed.metadata.duration}`,
      details: {
        duration: 0, // Would come from API
        durationFormatted: processed.metadata.duration || '00:00',
        language: 'en',
        wordCount: processed.metadata.wordCount || 0,
        transcription: processed.text,
        segments,
      },
    };

    setResult(analysisResult);
    toast.success(`Transcribed ${file.name} - ${processed.metadata.wordCount} words`);

    // Auto-index to chat with session context
    if (processed.text) {
      setIsIndexing(true);
      const indexed = await indexToChatWithSession(
        file.name,
        processed.text,
        processed.metadata,
        getSessionId()
      );
      setIsIndexing(false);
      
      if (indexed.success) {
        setResult(prev => prev ? { ...prev, indexed: true } : null);
        const sessionMsg = getSessionId() ? ' linked to current chat session' : '';
        toast.success(`Indexed to chat${sessionMsg}!`);
      } else {
        toast.warning('Transcribed but not indexed to chat');
      }
    }
  };

  const handleManualIndex = async () => {
    if (!processingResult) return;
    
    setIsIndexing(true);
    const indexed = await indexToChatWithSession(
      processingResult.metadata.fileName,
      processingResult.text,
      processingResult.metadata,
      getSessionId()
    );
    setIsIndexing(false);
    
    if (indexed.success) {
      setResult(prev => prev ? { ...prev, indexed: true } : null);
      toast.success('Indexed to chat!');
    } else {
      toast.error('Failed to index');
    }
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="Audio Analysis"
        description="Transcribe audio, identify speakers, and analyze content"
        icon={Mic}
        iconColor="purple"
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <FileUpload
          acceptedTypes={ACCEPTED_FORMATS.join(',')}
          maxSize={MAX_FILE_SIZE}
          onUpload={handleUpload}
          multiple={false}
        />
      </motion.div>

      {(isAnalyzing || isIndexing) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-12"
        >
          <div className="flex items-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
            <span className="text-gray-600">
              {isAnalyzing ? 'Transcribing audio...' : 'Indexing to chat...'}
            </span>
          </div>
        </motion.div>
      )}

      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-700">Transcription Failed</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          </div>
        </motion.div>
      )}

      {result && !isAnalyzing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Status Banner */}
          <div className="flex items-center justify-between p-3 bg-emerald-50 border border-emerald-200 rounded-lg"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-emerald-700">
                ✅ Transcription Complete
              </span>
              {result.indexed && (
                <span className="text-xs text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded">
                  {getSessionId() ? 'Linked to current chat' : 'Searchable in chat'}
                </span>
              )}
            </div>
            {!result.indexed && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={handleManualIndex}
                disabled={isIndexing}
              >
                {isIndexing ? 'Indexing...' : 'Index to Chat'}
              </Button>
            )}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Clock className="w-5 h-5 text-indigo-500" />
                <div>
                  <p className="text-sm text-gray-500">Duration</p>
                  <p className="font-semibold">{result.details.durationFormatted}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <MessageSquare className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Words</p>
                  <p className="font-semibold">{result.details.wordCount.toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Languages className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Language</p>
                  <p className="font-semibold">{result.details.language.toUpperCase()}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <FileAudio className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <p className="font-semibold">Done</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Full Transcription</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-64 overflow-y-auto bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {result.details.transcription}
                </p>
              </div>
            </CardContent>
          </Card>

          {result.indexed && (
            <p className="text-sm text-emerald-600 bg-emerald-50 p-3 rounded-lg text-center">
              💬 This transcription is indexed{getSessionId() && ' to your current chat session'}. 
              Try asking: "What was said in the audio about {result.fileName.replace(/\\.[^/.]+$/, '')}?"
            </p>
          )}
        </motion.div>
      )}
    </div>
  );
}
