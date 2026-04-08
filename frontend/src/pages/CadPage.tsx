import { useState } from 'react';
import { motion } from 'framer-motion';
import { Box, Layers, Ruler, AlertTriangle } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { } from '@/components/ui/badge';
import { } from '@/components/ui/button';
import type { AnalysisResult } from '@/types';

interface CadIssue {
  type: string;
  message: string;
  location: string;
}

interface CadMeasurements {
  totalArea: string;
  perimeter: string;
  roomCount: number;
}

interface LayerSummary {
  name: string;
  entities: number;
  color: string;
}

interface CadDetails {
  layers: number;
  entities: number;
  dimensions: number;
  blocks: number;
  issues: CadIssue[];
  measurements: CadMeasurements;
  layerSummary: LayerSummary[];
}

const ACCEPTED_FORMATS = ['.dwg', '.dxf', '.step', '.iges'];
const MAX_FILE_SIZE = 100; // MB

const mockResult: AnalysisResult = {
  id: '1',
  type: 'analysis',
  fileName: 'Building-Floor-Plan.dwg',
  status: 'completed',
  createdAt: new Date().toISOString(),
  completedAt: new Date().toISOString(),
  summary: 'CAD analysis completed. 15 layers analyzed with 2 issues detected.',
  details: {
    layers: 15,
    entities: 2847,
    dimensions: 156,
    blocks: 42,
    issues: [
      { type: 'warning', message: 'Layer "HIDDEN" contains unused entities', location: 'Layer 7' },
      { type: 'error', message: 'Missing dimension reference', location: 'Block "DOOR_01"' },
    ],
    measurements: {
      totalArea: '2,450 m²',
      perimeter: '198 m',
      roomCount: 24,
    },
    layerSummary: [
      { name: 'WALLS', entities: 456, color: '#FF0000' },
      { name: 'DOORS', entities: 89, color: '#00FF00' },
      { name: 'WINDOWS', entities: 124, color: '#0000FF' },
      { name: 'DIMENSIONS', entities: 156, color: '#FFFF00' },
    ],
  },
};

export default function CadPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleUpload = async (_file: File) => {
    // Use file to avoid unused variable warning
    console.log('Uploading files:', 1);
    setIsAnalyzing(true);
    await new Promise((resolve) => setTimeout(resolve, 2500));
    setResult(mockResult);
    setIsAnalyzing(false);
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="CAD Analysis"
        description="Analyze CAD files for layer information, measurements, and issues"
        icon={Box}
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
          attachments={[]} onUpload={handleUpload}
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
            <span className="text-gray-600">Analyzing CAD file...</span>
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
                <Layers className="w-5 h-5 text-indigo-500" />
                <div>
                  <p className="text-sm text-gray-500">Layers</p>
                  <p className="font-semibold">{(result.details as any as CadDetails)?.layers}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Box className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Entities</p>
                  <p className="font-semibold">{((result.details as any as CadDetails)?.entities ?? 0).toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Ruler className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Dimensions</p>
                  <p className="font-semibold">{(result.details as any as CadDetails)?.dimensions}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Box className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Blocks</p>
                  <p className="font-semibold">{(result.details as any as CadDetails)?.blocks}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Measurements */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Measurements</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Total Area</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {(result.details as any as CadDetails)?.measurements?.totalArea}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Perimeter</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {(result.details as any as CadDetails)?.measurements?.perimeter}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Room Count</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {(result.details as any as CadDetails)?.measurements?.roomCount}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Layer Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Layer Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {((result.details as any as CadDetails)?.layerSummary)?.map((layer, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-4 h-4 rounded"
                          style={{ backgroundColor: layer.color }}
                        />
                        <span className="font-medium text-gray-900">{layer.name}</span>
                      </div>
                      <span className="text-sm text-gray-500">{layer.entities} entities</span>
                    </div>
                  )
                )}
              </div>
            </CardContent>
          </Card>

          {/* Issues */}
          {((result.details as any as CadDetails)?.issues)?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  Issues Detected
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {((result.details as any as CadDetails)?.issues)?.map((issue, index) => (
                      <div
                        key={index}
                        className={`flex items-start gap-3 p-3 rounded-lg ${
                          issue.type === 'error' ? 'bg-red-50' : 'bg-amber-50'
                        }`}
                      >
                        {issue.type === 'error' ? (
                          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
                        )}
                        <div>
                          <p className="font-medium text-gray-900">{issue.message}</p>
                          <p className="text-sm text-gray-500">{issue.location}</p>
                        </div>
                      </div>
                    ))}
                  </div>
              </CardContent>
            </Card>
          )}
        </motion.div>
      )}
    </div>
  );
}
