import { useState } from 'react';
import { motion } from 'framer-motion';
import { Image as ImageIcon, Type, ScanLine, Tags, AlertCircle, Copy, Loader2 } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { processDocument, indexToChatWithSession, type ProcessingResult } from '@/lib/fileProcessing';

interface AnalysisResult {
  id: string;
  fileName: string;
  status: 'completed' | 'error';
  summary: string;
  indexed?: boolean;
  processingTime?: number;
  details: {
    extractedText: string;
    wordCount: number;
    confidence: number;
    classification?: {
      document_type: string;
      category: string;
      confidence: number;
    };
    entities: Array<{
      text: string;
      type: string;
    }>;
  };
}

const ACCEPTED_FORMATS = ['.png', '.jpg', '.jpeg', '.tiff', '.pdf'];
const MAX_FILE_SIZE = 50; // MB

// Get session ID from localStorage (set by chat interface)
const getSessionId = () => localStorage.getItem('cerebrum_chat_session_id') || undefined;

export default function ImagePage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);

  const handleUpload = async (file: File) => {
    setIsAnalyzing(true);
    setError(null);
    setResult(null);
    setProcessingResult(null);

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    // Process the image
    const processed = await processDocument(file, (stage) => {
      console.log(`Image ${stage}: ${file.name}`);
    });

    setIsAnalyzing(false);

    if (!processed.success) {
      setError(processed.error || 'Processing failed');
      toast.error(processed.error || 'Failed to analyze image');
      return;
    }

    setProcessingResult(processed);

    const analysisResult: AnalysisResult = {
      id: `img_${Date.now()}`,
      fileName: file.name,
      status: 'completed',
      summary: `${processed.metadata.type} - ${processed.metadata.wordCount} words extracted`,
      details: {
        extractedText: processed.text.substring(0, 2000),
        wordCount: processed.metadata.wordCount || 0,
        confidence: processed.metadata.confidence || 0,
        classification: processed.metadata.type ? {
          document_type: processed.metadata.type,
          category: 'Image Document',
          confidence: processed.metadata.confidence || 0.9,
        } : undefined,
        entities: processed.metadata.entities?.map(text => ({ text, type: 'unknown' })) || [],
      },
    };

    setResult(analysisResult);
    toast.success(`Processed ${file.name} - ${processed.metadata.wordCount} words`);

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
        toast.warning('Processed but not indexed to chat');
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

  const groupEntitiesByType = (entities: AnalysisResult['details']['entities']) => {
    const grouped: Record<string, string[]> = {};
    entities.forEach(e => {
      if (!grouped[e.type]) grouped[e.type] = [];
      if (!grouped[e.type].includes(e.text)) {
        grouped[e.type].push(e.text);
      }
    });
    return grouped;
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="Image Analysis"
        description="Extract text from images using OCR and identify entities"
        icon={ImageIcon}
        iconColor="blue"
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
              {isAnalyzing ? 'Analyzing image...' : 'Indexing to chat...'}
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
              <p className="font-medium text-red-700">Analysis Failed</p>
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
                ✅ Analysis Complete
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

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {previewUrl && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Image Preview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="relative rounded-lg overflow-hidden bg-gray-100">
                    <img 
                      src={previewUrl} 
                      alt="Analyzed" 
                      className="w-full h-auto max-h-96 object-contain"
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Analysis Results</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {result.details.classification && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">Document Type</span>
                      <span className="text-sm font-medium bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">
                        {result.details.classification.document_type}
                      </span>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <Type className="w-5 h-5 text-emerald-500" />
                      <div>
                        <p className="text-xs text-gray-500">Words</p>
                        <p className="font-semibold">{result.details.wordCount.toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <ScanLine className="w-5 h-5 text-indigo-500" />
                      <div>
                        <p className="text-xs text-gray-500">OCR Confidence</p>
                        <p className="font-semibold">{Math.round(result.details.confidence * 100)}%</p>
                      </div>
                    </div>
                  </div>

                  {result.indexed && (
                    <p className="text-sm text-emerald-600 bg-emerald-50 p-3 rounded-lg mt-4">
                      💬 This image is indexed{getSessionId() && ' to your current chat session'}.
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>

          <Tabs defaultValue="text" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="text">Extracted Text</TabsTrigger>
              <TabsTrigger value="entities">Entities</TabsTrigger>
              <TabsTrigger value="raw">Raw Data</TabsTrigger>
            </TabsList>

            <TabsContent value="text">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">Extracted Text</CardTitle>
                  {result.details.extractedText && (
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(result.details.extractedText);
                        toast.success('Copied to clipboard');
                      }}
                    >
                      <Copy className="w-4 h-4 mr-1" />
                      Copy
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {result.details.extractedText ? (
                    <div className="max-h-96 overflow-y-auto">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-4 rounded-lg">
                        {result.details.extractedText}
                      </pre>
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">No text detected</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="entities">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Tags className="w-4 h-4" />
                    Named Entities
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {result.details.entities.length > 0 ? (
                    <div className="space-y-4">
                      {Object.entries(groupEntitiesByType(result.details.entities)).map(([type, items]) => (
                        <div key={type}>
                          <h4 className="text-sm font-medium text-gray-700 mb-2 capitalize">
                            {type.replace(/_/g, ' ')}
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {items.map((item, idx) => (
                              <span
                                key={idx}
                                className="px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full text-sm"
                              >
                                {item}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">No entities found</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="raw">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Processing Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between py-2 border-b border-gray-100">
                      <span className="text-gray-500">File ID</span>
                      <span className="font-mono text-gray-700">{result.id}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-100">
                      <span className="text-gray-500">File Name</span>
                      <span className="text-gray-700">{result.fileName}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-100">
                      <span className="text-gray-500">Status</span>
                      <span className="text-emerald-600 font-medium">{result.status}</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-100">
                      <span className="text-gray-500">Indexed to Chat</span>
                      <span className={result.indexed ? 'text-emerald-600' : 'text-gray-400'}>
                        {result.indexed ? 'Yes' : 'No'}
                      </span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-gray-100">
                      <span className="text-gray-500">Linked to Session</span>
                      <span className={getSessionId() ? 'text-emerald-600' : 'text-gray-400'}>
                        {getSessionId() ? 'Yes' : 'No active session'}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </div>
  );
}
