import { useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, TrendingUp, Activity, Filter, Download } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { } from '@/components/ui/progress';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { AnalysisResult } from '@/types';

const ACCEPTED_FORMATS = ['.csv', '.json', '.xlsx'];
const MAX_FILE_SIZE = 50; // MB

const chartData = [
  { time: '00:00', value: 120, anomaly: null },
  { time: '04:00', value: 135, anomaly: null },
  { time: '08:00', value: 148, anomaly: null },
  { time: '12:00', value: 320, anomaly: 320 },
  { time: '16:00', value: 142, anomaly: null },
  { time: '20:00', value: 380, anomaly: 380 },
  { time: '24:00', value: 125, anomaly: null },
];

const mockResult: AnalysisResult = {
  id: '1',
  moduleId: 'anomaly',
  fileName: 'sensor-data.csv',
  status: 'completed',
  createdAt: new Date(),
  completedAt: new Date(),
  summary: 'Anomaly detection completed. 2 anomalies found in 1,247 data points.',
  details: {
    totalPoints: 1247,
    anomalies: 2,
    confidence: 94.5,
    threshold: 250,
    anomalyList: [
      { timestamp: '12:00', value: 320, deviation: 128, severity: 'high' },
      { timestamp: '20:00', value: 380, deviation: 188, severity: 'critical' },
    ],
    statistics: {
      mean: 152.3,
      stdDev: 45.7,
      min: 98,
      max: 380,
    },
  },
};

export default function AnomalyPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleUpload = async (_files: File[]) => {
    setIsAnalyzing(true);
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setResult(mockResult);
    setIsAnalyzing(false);
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="Anomaly Detection"
        description="Detect anomalies and outliers in your data"
        icon={AlertTriangle}
        iconColor="amber"
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
            <span className="text-gray-600">Analyzing data for anomalies...</span>
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
                <Activity className="w-5 h-5 text-indigo-500" />
                <div>
                  <p className="text-sm text-gray-500">Data Points</p>
                  <p className="font-semibold">{((result.details as any)?.totalPoints as number).toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <div>
                  <p className="text-sm text-gray-500">Anomalies</p>
                  <p className="font-semibold">{(result.details as any)?.anomalies as number}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <TrendingUp className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Confidence</p>
                  <p className="font-semibold">{(result.details as any)?.confidence}%</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Filter className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Threshold</p>
                  <p className="font-semibold">{(result.details as any)?.threshold}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Anomaly Visualization</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                    <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                      }}
                    />
                    <ReferenceLine
                      y={(result.details as any)?.threshold as number}
                      stroke="#ef4444"
                      strokeDasharray="5 5"
                      label="Threshold"
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#6366f1"
                      strokeWidth={2}
                      dot={{ fill: '#6366f1', r: 4 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="anomaly"
                      stroke="#ef4444"
                      strokeWidth={0}
                      dot={{ fill: '#ef4444', r: 8 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Anomaly List */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Detected Anomalies</CardTitle>
              <Button variant="outline" size="sm">
                <Download className="w-4 h-4 mr-1" />
                Export
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {((result.details as any)?.anomalyList as Array<{
                  timestamp: string;
                  value: number;
                  deviation: number;
                  severity: string;
                }>)?.map((anomaly, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-4 bg-red-50 rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                        <AlertTriangle className="w-5 h-5 text-red-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">Value: {anomaly.value}</p>
                        <p className="text-sm text-gray-500">{anomaly.timestamp}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge className={anomaly.severity === 'critical' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>
                        {anomaly.severity}
                      </Badge>
                      <p className="text-sm text-red-600 mt-1">+{anomaly.deviation} deviation</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
