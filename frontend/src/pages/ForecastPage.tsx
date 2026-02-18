import { useState } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Calendar, Target, ArrowUpRight } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  ReferenceLine,
} from 'recharts';
import type { AnalysisResult } from '@/types';

const ACCEPTED_FORMATS = ['.csv', '.json', '.xlsx'];
const MAX_FILE_SIZE = 50; // MB

const forecastData = [
  { month: 'Jan', actual: 120, forecast: null, lower: null, upper: null },
  { month: 'Feb', actual: 135, forecast: null, lower: null, upper: null },
  { month: 'Mar', actual: 148, forecast: null, lower: null, upper: null },
  { month: 'Apr', actual: 162, forecast: null, lower: null, upper: null },
  { month: 'May', actual: 155, forecast: null, lower: null, upper: null },
  { month: 'Jun', actual: 178, forecast: null, lower: null, upper: null },
  { month: 'Jul', actual: null, forecast: 195, lower: 175, upper: 215 },
  { month: 'Aug', actual: null, forecast: 210, lower: 185, upper: 235 },
  { month: 'Sep', actual: null, forecast: 225, lower: 195, upper: 255 },
  { month: 'Oct', actual: null, forecast: 240, lower: 205, upper: 275 },
];

const mockResult: AnalysisResult = {
  id: '1',
  moduleId: 'forecast',
  fileName: 'sales-data.csv',
  status: 'completed',
  createdAt: new Date(),
  completedAt: new Date(),
  summary: 'Forecast analysis completed. 4-month prediction with 92% accuracy.',
  details: {
    forecastPeriod: 4,
    confidence: 92,
    trend: 'upward',
    growthRate: 15.3,
    predictions: [
      { period: 'July 2024', value: 195, confidence: 94, change: 9.6 },
      { period: 'August 2024', value: 210, confidence: 91, change: 7.7 },
      { period: 'September 2024', value: 225, confidence: 89, change: 7.1 },
      { period: 'October 2024', value: 240, confidence: 87, change: 6.7 },
    ],
    insights: [
      'Strong upward trend detected',
      'Seasonal pattern identified',
      'Growth rate accelerating',
    ],
  },
};

export default function ForecastPage() {
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
        title="Forecasting"
        description="Predict future trends based on historical data"
        icon={TrendingUp}
        iconColor="emerald"
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
            <span className="text-gray-600">Generating forecast...</span>
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
                <Calendar className="w-5 h-5 text-indigo-500" />
                <div>
                  <p className="text-sm text-gray-500">Forecast Period</p>
                  <p className="font-semibold">{(result.details as any)?.forecastPeriod} months</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Target className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Accuracy</p>
                  <p className="font-semibold">{(result.details as any)?.confidence}%</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <TrendingUp className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Trend</p>
                  <Badge className="bg-emerald-100 text-emerald-700 capitalize">
                    {((result.details as any)?.trend as string)}
                  </Badge>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <ArrowUpRight className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Growth Rate</p>
                  <p className="font-semibold">+{(result.details as any)?.growthRate}%</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Forecast Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Forecast Visualization</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={forecastData}>
                    <defs>
                      <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                    <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                      }}
                    />
                    <ReferenceLine x="Jun" stroke="#9ca3af" strokeDasharray="3 3" label="Now" />
                    <Area
                      type="monotone"
                      dataKey="upper"
                      stroke="none"
                      fill="#6366f1"
                      fillOpacity={0.1}
                    />
                    <Area
                      type="monotone"
                      dataKey="lower"
                      stroke="none"
                      fill="#fff"
                      fillOpacity={1}
                    />
                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={{ fill: '#10b981', r: 4 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="forecast"
                      stroke="#6366f1"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      dot={{ fill: '#6366f1', r: 4 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-6 mt-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                  <span className="text-sm text-gray-600">Actual</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-indigo-500" />
                  <span className="text-sm text-gray-600">Forecast</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-indigo-200" />
                  <span className="text-sm text-gray-600">Confidence Interval</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Predictions Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Monthly Predictions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {((result.details as any)?.predictions as Array<{
                  period: string;
                  value: number;
                  confidence: number;
                  change: number;
                }>)?.map((prediction, index) => (
                  <div key={index} className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">{prediction.period}</p>
                    <p className="text-2xl font-semibold text-gray-900 mt-1">
                      {prediction.value.toLocaleString()}
                    </p>
                    <div className="flex items-center justify-between mt-3">
                      <Badge variant="outline" className="text-xs">
                        {prediction.confidence}% confidence
                      </Badge>
                      <span className="text-sm text-emerald-600 flex items-center">
                        <ArrowUpRight className="w-4 h-4 mr-0.5" />
                        {prediction.change}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Insights */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Key Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {((result.details as any)?.insights as string[])?.map((insight, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-medium text-emerald-600">{index + 1}</span>
                    </div>
                    <span className="text-gray-700">{insight}</span>
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
