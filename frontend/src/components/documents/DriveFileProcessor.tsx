import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Brain, CheckCircle, AlertCircle, FileText, Tag, Clock } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface DriveFileProcessorProps {
  fileId: string;
  fileName: string;
  mimeType?: string;
  onProcessed?: (data: any) => void;
}

interface ProcessingResult {
  document_id: string;
  status: string;
  summary: string;
  entities_count: number;
  processing_time: number;
  results?: any;
}

export const DriveFileProcessor: React.FC<DriveFileProcessorProps> = ({
  fileId,
  fileName,
  mimeType,
  onProcessed
}) => {
  const [status, setStatus] = useState<'idle' | 'processing' | 'completed' | 'error'>('idle');
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [progress, setProgress] = useState<string>('');
  const { toast } = useToast();

  // Check if already processed on mount
  useEffect(() => {
    checkExistingProcessing();
  }, [fileId]);

  const checkExistingProcessing = async () => {
    try {
      const res = await fetch(`/api/v1/documents/drive/processed`);
      if (res.ok) {
        const data = await res.json();
        const existing = data.find((d: any) => d.drive_file_id === fileId);
        if (existing) {
          setStatus(existing.status === 'indexed' ? 'completed' : existing.status);
          setResult(existing);
        }
      }
    } catch (e) {
      // Silent fail
    }
  };

  const startProcessing = async () => {
    setStatus('processing');
    setProgress('Initializing AI analysis...');

    try {
      const response = await fetch(
        `/api/v1/documents/drive/${fileId}/process?operations=ocr,classification,ner`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Processing failed');
      }

      const data = await response.json();
      setResult(data);
      setStatus('completed');
      setProgress('Analysis complete');
      onProcessed?.(data);

      toast({
        title: "AI Analysis Complete",
        description: `Processed ${fileName} in ${data.processing_time?.toFixed(1)}s`
      });

    } catch (error: any) {
      setStatus('error');
      setProgress(error.message || 'Processing failed');
      toast({
        title: "Processing Failed",
        description: error.message,
        variant: "destructive"
      });
    }
  };

  const getIcon = () => {
    switch (status) {
      case 'processing': return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error': return <AlertCircle className="h-4 w-4 text-red-500" />;
      default: return <Brain className="h-4 w-4" />;
    }
  };

  const getButtonText = () => {
    switch (status) {
      case 'processing': return 'Analyzing...';
      case 'completed': return 'Analyzed';
      case 'error': return 'Retry';
      default: return 'AI Process';
    }
  };

  const isProcessable = mimeType?.includes('pdf') || 
                       mimeType?.includes('image') || 
                       mimeType?.includes('officedocument') ||
                       mimeType?.includes('text');

  if (!isProcessable) {
    return (
      <Badge variant="outline" className="text-gray-400">
        <FileText className="h-3 w-3 mr-1" />
        Not processable
      </Badge>
    );
  }

  return (
    <div className="space-y-4">
      <Button
        variant={status === 'completed' ? "outline" : "default"}
        size="sm"
        onClick={startProcessing}
        disabled={status === 'processing'}
        className="gap-2"
      >
        {getIcon()}
        {getButtonText()}
      </Button>

      {status === 'processing' && (
        <div className="flex items-center gap-2 text-sm text-blue-600">
          <Clock className="h-4 w-4 animate-pulse" />
          {progress}
        </div>
      )}

      {status === 'completed' && result && (
        <Card className="mt-4 bg-gray-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Brain className="h-4 w-4 text-blue-500" />
              AI Insights
              {result.results?.zvec_indexed && (
                <Badge variant="secondary" className="ml-2 text-xs">ZVec</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-sm text-gray-700">{result.summary}</p>
            </div>

            {result.entities_count > 0 && (
              <div className="flex items-center gap-2">
                <Tag className="h-4 w-4 text-gray-500" />
                <span className="text-xs text-gray-600">
                  {result.entities_count} entities extracted
                </span>
              </div>
            )}

            {result.processing_time && (
              <div className="text-xs text-gray-400">
                Processed in {result.processing_time.toFixed(1)}s
              </div>
            )}

            {result.results?.classification && (
              <Badge variant="secondary" className="mt-2">
                {result.results.classification.label || result.results.classification.document_type || 'Document'}
              </Badge>
            )}
          </CardContent>
        </Card>
      )}

      {status === 'error' && (
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded">
          {progress}
        </div>
      )}
    </div>
  );
};

export default DriveFileProcessor;
