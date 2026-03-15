import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Table, Type, Image as ImageIcon } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { STORAGE_KEYS } from '@/context/AuthContext';

const ACCEPTED_FORMATS = ['.pdf'];
const MAX_FILE_SIZE = 50; // MB

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

interface PDFResult {
  file_id: string;
  filename: string;
  pages?: number;
  text_content?: string;
  tables?: Array<{ name: string; rows: number; columns: number }>;
  images?: number;
}

export default function PdfPage() {
  const [result, setResult] = useState<PDFResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (files: File[]) => {
    if (files.length === 0) return;
    
    setIsAnalyzing(true);
    setError(null);
    setResult(null);
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      
      // Use the chat upload endpoint which extracts text
      const response = await fetch(`${API_BASE}/connectors/upload/chat`, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: formData,
      });
      
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed: ${response.status}`);
      }
      
      const data = await response.json();
      
      setResult({
        file_id: data.file_id || data.id,
        filename: file.name,
        pages: data.pages || 1,
        text_content: data.text || data.extracted_text,
        images: data.images || 0,
      });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process PDF');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="PDF Analysis"
        description="Extract text and content from PDF documents"
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
          acceptedFormats={ACCEPTED_FORMATS}
          maxFileSize={MAX_FILE_SIZE}
          onUpload={handleUpload}
        />
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6"
        >
          <p className="text-red-600">{error}</p>
        </motion.div>
      )}

      {isAnalyzing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-12"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-gray-600">Extracting PDF content...</span>
          </div>
        </motion.div>
      )}

      {result && !isAnalyzing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <FileText className="w-5 h-5 text-indigo-500" />
                <div>
                  <p className="text-sm text-gray-500">Pages</p>
                  <p className="font-semibold">{result.pages || 1}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Type className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Text Length</p>
                  <p className="font-semibold">{result.text_content?.length?.toLocaleString() || 0} chars</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Table className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Tables</p>
                  <p className="font-semibold">{result.tables?.length || 0}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <ImageIcon className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Images</p>
                  <p className="font-semibold">{result.images || 0}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Content */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Extracted Text</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">{result.text_content || 'No text extracted'}</pre>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
