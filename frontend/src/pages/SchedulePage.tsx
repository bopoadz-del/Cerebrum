import { useState } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, AlertCircle, CheckCircle } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { } from '@/lib/utils';
import type { AnalysisResult } from '@/types';

const ACCEPTED_FORMATS = ['.xer', '.mpp', '.xml', '.csv'];
const MAX_FILE_SIZE = 50; // MB

// Mock analysis result
const mockResult: AnalysisResult = {
  id: '1',
  moduleId: 'schedule',
  fileName: 'Project-Schedule.xer',
  status: 'completed',
  createdAt: new Date(),
  completedAt: new Date(),
  summary: 'Schedule analysis completed with 3 critical issues found',
  details: {
    criticalPath: ['Task A', 'Task B', 'Task C'],
    delays: [
      { task: 'Foundation Work', days: 5, reason: 'Weather conditions' },
      { task: 'Electrical Installation', days: 2, reason: 'Material shortage' },
    ],
    resourceConflicts: [
      { resource: 'Team Alpha', tasks: ['Task 1', 'Task 2'], dates: 'Jan 15-20' },
    ],
    recommendations: [
      'Consider adding buffer time for weather-dependent tasks',
      'Prioritize electrical material procurement',
      'Reallocate Team Alpha resources to avoid conflicts',
    ],
  },
};

export default function SchedulePage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleUpload = async (_files: File[]) => {
    setIsAnalyzing(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setResult(mockResult);
    setIsAnalyzing(false);
  };

  return (
    <div className="p-8">
      <ModuleHeader
        title="Schedule Analysis"
        description="Analyze project schedules for delays, critical path, and resource conflicts"
        icon={Calendar}
        iconColor="emerald"
      />

      {/* Upload Section */}
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

      {/* Analysis Results */}
      {isAnalyzing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-12"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-gray-600">Analyzing schedule...</span>
          </div>
        </motion.div>
      )}

      {result && !isAnalyzing && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Summary Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <CardTitle className="text-lg">Analysis Complete</CardTitle>
                  <p className="text-sm text-gray-500">{result.fileName}</p>
                </div>
              </div>
              <Badge className="bg-emerald-100 text-emerald-700">Completed</Badge>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700">{result.summary}</p>
            </CardContent>
          </Card>

          {/* Results Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Delays */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Clock className="w-5 h-5 text-amber-500" />
                  <CardTitle className="text-base">Schedule Delays</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {((result.details as any)?.delays as Array<{ task: string; days: number; reason: string }>)?.map(
                    (delay, index) => (
                      <div
                        key={index}
                        className="flex items-start justify-between p-3 bg-amber-50 rounded-lg"
                      >
                        <div>
                          <p className="font-medium text-gray-900">{delay.task}</p>
                          <p className="text-sm text-gray-600">{delay.reason}</p>
                        </div>
                        <Badge variant="outline" className="text-amber-700 border-amber-200">
                          +{delay.days} days
                        </Badge>
                      </div>
                    )
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Resource Conflicts */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-500" />
                  <CardTitle className="text-base">Resource Conflicts</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {((result.details as any)?.resourceConflicts as Array<{
                    resource: string;
                    tasks: string[];
                    dates: string;
                  }>)?.map((conflict, index) => (
                    <div
                      key={index}
                      className="flex items-start justify-between p-3 bg-red-50 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-gray-900">{conflict.resource}</p>
                        <p className="text-sm text-gray-600">
                          Tasks: {conflict.tasks.join(', ')}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">{conflict.dates}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recommendations */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recommendations</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {((result.details as any)?.recommendations as string[])?.map((rec, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <div className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-medium text-indigo-600">{index + 1}</span>
                    </div>
                    <span className="text-gray-700">{rec}</span>
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
