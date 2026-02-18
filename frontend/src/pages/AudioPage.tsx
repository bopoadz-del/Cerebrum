import { useState } from 'react';
import { motion } from 'framer-motion';
import { Mic, Play, Pause, Volume2, Clock, User, MessageSquare } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import type { AnalysisResult } from '@/types';

const ACCEPTED_FORMATS = ['.mp3', '.wav', '.m4a', '.ogg', '.flac'];
const MAX_FILE_SIZE = 100; // MB

// Mock analysis result
const mockResult: AnalysisResult = {
  id: '1',
  moduleId: 'audio',
  fileName: 'Meeting-Recording.mp3',
  status: 'completed',
  createdAt: new Date(),
  completedAt: new Date(),
  summary: 'Audio analysis completed. 45 minutes of content processed.',
  details: {
    duration: '45:32',
    speakers: 4,
    transcription: [
      { time: '00:00', speaker: 'John', text: 'Welcome everyone to our weekly project review meeting.' },
      { time: '00:15', speaker: 'Sarah', text: 'Thanks John. I have updates on the development progress.' },
      { time: '00:45', speaker: 'Mike', text: 'Before we start, I want to raise a concern about the timeline.' },
    ],
    sentiment: {
      overall: 'positive',
      breakdown: { positive: 65, neutral: 25, negative: 10 },
    },
    keyMoments: [
      { time: '12:30', description: 'Budget discussion' },
      { time: '28:45', description: 'Timeline concerns raised' },
      { time: '38:20', description: 'Action items assigned' },
    ],
  },
};

export default function AudioPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime] = useState(0);

  const handleUpload = async (_files: File[]) => {
    setIsAnalyzing(true);
    await new Promise((resolve) => setTimeout(resolve, 2500));
    setResult(mockResult);
    setIsAnalyzing(false);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="Audio Analysis"
        description="Transcribe audio, identify speakers, and analyze sentiment"
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
          acceptedFormats={ACCEPTED_FORMATS}
          maxFileSize={MAX_FILE_SIZE}
          onUpload={handleUpload}
        />
      </motion.div>

      {isAnalyzing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-12"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-gray-600">Transcribing audio...</span>
          </div>
        </motion.div>
      )}

      {result && !isAnalyzing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Audio Player */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="w-12 h-12 rounded-full"
                >
                  {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                </Button>
                <div className="flex-1">
                  <Progress value={(currentTime / 2732) * 100} className="h-2" />
                  <div className="flex justify-between mt-2 text-sm text-gray-500">
                    <span>{formatTime(currentTime)}</span>
                    <span>{(result.details as any)?.duration as string}</span>
                  </div>
                </div>
                <Volume2 className="w-5 h-5 text-gray-400" />
              </div>
            </CardContent>
          </Card>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Clock className="w-5 h-5 text-indigo-500" />
                <div>
                  <p className="text-sm text-gray-500">Duration</p>
                  <p className="font-semibold">{(result.details as any)?.duration as string}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <User className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Speakers</p>
                  <p className="font-semibold">{(result.details as any)?.speakers as number}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <MessageSquare className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Sentiment</p>
                  <Badge className="bg-emerald-100 text-emerald-700">
                    {((result.details as any)?.sentiment as { overall: string })?.overall}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Transcription */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Transcription</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {((result.details as any)?.transcription as Array<{ time: string; speaker: string; text: string }>)?.map(
                  (item, index) => (
                    <div key={index} className="flex gap-4">
                      <span className="text-sm text-gray-400 w-12 flex-shrink-0">{item.time}</span>
                      <div>
                        <span className="text-sm font-medium text-indigo-600">{item.speaker}</span>
                        <p className="text-gray-700 mt-0.5">{item.text}</p>
                      </div>
                    </div>
                  )
                )}
              </div>
            </CardContent>
          </Card>

          {/* Key Moments */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Key Moments</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {((result.details as any)?.keyMoments as Array<{ time: string; description: string }>)?.map(
                  (moment, index) => (
                    <button
                      key={index}
                      className="flex items-center gap-2 px-3 py-2 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
                    >
                      <span className="text-sm font-medium text-indigo-600">{moment.time}</span>
                      <span className="text-sm text-gray-700">{moment.description}</span>
                    </button>
                  )
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
