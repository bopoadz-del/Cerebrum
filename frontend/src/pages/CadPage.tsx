import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileDigit, Box, Layers } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { STORAGE_KEYS } from '@/context/AuthContext';

const ACCEPTED_FORMATS = ['.dwg', '.dxf', '.step', '.stp'];
const MAX_FILE_SIZE = 100;

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

interface CadResult {
  file_id: string;
  filename: string;
  file_type?: string;
  size?: number;
}

export default function CadPage() {
  const [result, setResult] = useState<CadResult | null>(null);
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
        file_type: file.name.split('.').pop(),
        size: file.size,
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
        title="CAD Analysis"
        description="Process CAD files and extract geometry"
        icon={FileDigit}
        iconColor="blue"
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
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-gray-600">Processing CAD file...</span>
        </div>
      )}

      {result && !isProcessing && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{result.filename}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
                  <Box className="w-5 h-5 text-blue-500" />
                  <div>
                    <p className="text-sm text-gray-500">File Type</p>
                    <p className="font-semibold">{result.file_type?.toUpperCase()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
                  <Layers className="w-5 h-5 text-blue-500" />
                  <div>
                    <p className="text-sm text-gray-500">Size</p>
                    <p className="font-semibold">{((result.size || 0) / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
