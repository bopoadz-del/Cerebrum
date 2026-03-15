import { useState } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, CheckCircle } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { STORAGE_KEYS } from '@/context/AuthContext';

const ACCEPTED_FORMATS = ['.mpp', '.xlsx', '.csv', '.json'];
const MAX_FILE_SIZE = 50;

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

interface ScheduleResult {
  file_id: string;
  filename: string;
  tasks?: number;
  duration?: string;
}

export default function SchedulePage() {
  const [result, setResult] = useState<ScheduleResult | null>(null);
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
        tasks: 0,
        duration: 'Unknown',
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
        title="Schedule Analysis"
        description="Analyze project schedules and timelines"
        icon={Calendar}
        iconColor="orange"
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
          <div className="w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-gray-600">Processing schedule...</span>
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
                  <CheckCircle className="w-5 h-5 text-orange-500" />
                  <div>
                    <p className="text-sm text-gray-500">Tasks</p>
                    <p className="font-semibold">{result.tasks}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
                  <Clock className="w-5 h-5 text-orange-500" />
                  <div>
                    <p className="text-sm text-gray-500">Duration</p>
                    <p className="font-semibold">{result.duration}</p>
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
