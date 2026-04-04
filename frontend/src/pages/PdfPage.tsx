import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Table, Type, Image as ImageIcon, AlertCircle, Loader2 } from 'lucide-react';
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
  details: {
    pages: number;
    textBlocks: number;
    tables: number;
    images: number;
    extractedText?: string;
    extractedTables: unknown[];
    keyInsights: string[];
    classification?: {
      document_type: string;
      category: string;
      confidence: number;
    };
    entities?: Array<{
      text: string;
      type: string;
    }>;
  };
  processingTime?: number;
}

const ACCEPTED_FORMATS = ['.pdf'];
const MAX_FILE_SIZE = 50; // MB

// Get session ID from localStorage (set by chat interface)
const getSessionId = () => localStorage.getItem('cerebrum_chat_session_id') || undefined;

export default function PdfPage() {
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

    // Process the document
    const processed = await processDocument(file, (stage) => {
      console.log(`PDF ${stage}: ${file.name}`);
    });

    setIsAnalyzing(false);

    if (!processed.success) {
      setError(processed.error || 'Processing failed');
      toast.error(processed.error || 'Failed to process PDF');
      return;
    }

    setProcessingResult(processed);

    // Build analysis result
    const analysisResult: AnalysisResult = {
      id: `pdf_${Date.now()}`,
      fileName: file.name,
      status: 'completed',
      summary: `${processed.metadata.type} - ${processed.metadata.wordCount} words extracted`,
      details: {
        pages: Math.ceil((processed.metadata.wordCount || 0) / 300),
        textBlocks: processed.metadata.wordCount || 0,
        tables: 0,
        images: 0,
        extractedText: processed.text.substring(0, 2000),
        extractedTables: [],
        keyInsights: [
          `Document type: ${processed.metadata.type}`,
          `Extracted ${processed.metadata.wordCount} words`,
          processed.metadata.entities?.length 
            ? `Found entities: ${processed.metadata.entities.slice(0, 5).join(', ')}`
            : 'No entities detected',
        ],
        classification: processed.metadata.type ? {
          document_type: processed.metadata.type,
          category: 'PDF Document',
          confidence: processed.metadata.confidence || 0.9,
        } : undefined,
        entities: processed.metadata.entities?.map(text => ({ text, type: 'unknown' })),
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

  // Manual index button handler
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
        title="PDF Analysis"
        description="Extract text, tables, and images from PDF documents"
        icon={FileText}
        iconColor="red"
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
              {isAnalyzing ? 'Analyzing PDF...' : 'Indexing to chat...'}
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

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <FileText className="w-5 h-5 text-indigo-500" />
                <div>
                  <p className="text-sm text-gray-500">Pages</p>
                  <p className="font-semibold">{result.details.pages}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Type className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Words</p>
                  <p className="font-semibold">{result.details.textBlocks.toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Table className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Tables</p>
                  <p className="font-semibold">{result.details.tables}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <ImageIcon className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Images</p>
                  <p className="font-semibold">{result.details.images}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Content Tabs */}
          <Tabs defaultValue="summary" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="summary">Summary</TabsTrigger>
              <TabsTrigger value="text">Extracted Text</TabsTrigger>
              <TabsTrigger value="entities">Entities</TabsTrigger>
              <TabsTrigger value="insights">Insights</TabsTrigger>
            </TabsList>

            <TabsContent value="summary">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Document Analysis</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {result.details.classification && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">Type:</span>
                      <span className="text-sm font-medium bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">
                        {result.details.classification.document_type}
                      </span>
                    </div>
                  )}
                  
                  <p className="text-gray-700 leading-relaxed">{result.summary}</p>
                  
                  {result.indexed && (
                    <p className="text-sm text-emerald-600 bg-emerald-50 p-3 rounded-lg">
                      💬 This document is indexed{getSessionId() && ' to your current chat session'}. 
                      Try asking: "What was in the PDF about {result.details.classification?.document_type || 'this document'}?"
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="text">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Extracted Text</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="max-h-96 overflow-y-auto">
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-4 rounded-lg">
                      {result.details.extractedText || 'No text extracted'}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="entities">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Named Entities</CardTitle>
                </CardHeader>
                <CardContent>
                  {result.details.entities && result.details.entities.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {result.details.entities.map((entity, index) => (
                        <span
                          key={index}
                          className="px-2.5 py-1 text-sm bg-indigo-50 text-indigo-700 rounded-full"
                        >
                          {entity.text}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">No entities detected</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="insights">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Key Insights</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {result.details.keyInsights.map((insight, index) => (
                      <li key={index} className="flex items-start gap-3">
                        <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                          <span className="text-xs font-medium text-indigo-600">{index + 1}</span>
                        </div>
                        <span className="text-gray-700">{insight}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </div>
  );
}
