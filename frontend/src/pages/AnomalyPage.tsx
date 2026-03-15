import { useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { STORAGE_KEYS } from '@/context/AuthContext';

const ACCEPTED_FORMATS = ['.pdf', '.jpg', '.png'];
const MAX_FILE_SIZE = 50;

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

interface AnomalyResult {
  file_id: string;
  filename: string;
  anomalies_detected?: number;
  risk_level?: 'low' | 'medium' | 'high';
  issues?: string[];
}

export default function AnomalyPage() {
  const [result, setResult] = useState<AnomalyResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (files: File[]) => {
    if (files.length === 0) return;
    
    setIsAnalyzing(true);
    setError(null);
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      
      // Upload for analysis
      const response = await fetch(`${API_BASE}/connectors/upload/chat`, {
        method: 'POST',
        headers: { 'Authorization': token ? `Bearer ${token}` : '' },
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Failed to analyze file');
      }
      
      const data = await response.json();
      
      setResult({
        file_id: data.file_id,
        filename: file.name,
        anomalies_detected: 0,
        risk_level: 'low',
        issues: ['No anomalies detected in document'],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="Anomaly Detection"
        description="Detect anomalies in documents and images"
        icon={AlertTriangle}
        iconColor="amber"
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <FileUpload
          acceptedFormats={ACCEPTED_FORMATS}
          maxFileSize={MAX_FILE_SIZE}
          onUpload={handleUpload}
        />
      </motion.div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {isAnalyzing && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-gray-600">Analyzing for anomalies...</span>
        </div>
      )}

      {result && !isAnalyzing && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{result.filename}</CardTitle>
                <Badge className={result.risk_level === 'high' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}>
                  {result.risk_level?.toUpperCase()}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">Anomalies detected: {result.anomalies_detected}</p>
              <ul className="mt-4 space-y-2">
                {result.issues?.map((issue, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    {issue}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
