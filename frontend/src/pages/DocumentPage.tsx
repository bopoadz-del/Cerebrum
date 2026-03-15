import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Eye } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { STORAGE_KEYS } from '@/context/AuthContext';

const ACCEPTED_FORMATS = ['.pdf', '.doc', '.docx', '.txt'];
const MAX_FILE_SIZE = 50;

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

interface DocResult {
  file_id: string;
  filename: string;
  content_type?: string;
  extracted_text?: string;
}

export default function DocumentPage() {
  const [result, setResult] = useState<DocResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (files: File[]) => {
    if (files.length === 0) return;
    
    setIsProcessing(true);
    setError(null);
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      
      const response = await fetch(`${API_BASE}/connectors/upload/chat`, {
        method: 'POST',
        headers: { 'Authorization': token ? `Bearer ${token}` : '' },
        body: formData,
      });
      
      if (!response.ok) throw new Error('Upload failed');
      
      const data = await response.json();
      
      setResult({
        file_id: data.file_id,
        filename: file.name,
        content_type: file.type,
        extracted_text: data.text || data.extracted_text,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="Document Analysis"
        description="Extract text and analyze documents"
        icon={FileText}
        iconColor="emerald"
      />

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <FileUpload acceptedFormats={ACCEPTED_FORMATS} maxFileSize={MAX_FILE_SIZE} onUpload={handleUpload} />
      </motion.div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {isProcessing && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-gray-600">Processing document...</span>
        </div>
      )}

      {result && !isProcessing && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Eye className="w-5 h-5 text-emerald-500" />
                <CardTitle>{result.filename}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">{result.extracted_text || 'No text extracted'}</pre>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
