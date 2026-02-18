import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, Table, Type, Image as ImageIcon } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AnalysisResult } from '@/types';

const ACCEPTED_FORMATS = ['.pdf'];
const MAX_FILE_SIZE = 50; // MB

const mockResult: AnalysisResult = {
  id: '1',
  moduleId: 'pdf',
  fileName: 'Q4-Financial-Report.pdf',
  status: 'completed',
  createdAt: new Date(),
  completedAt: new Date(),
  summary: 'PDF analysis completed. 24 pages processed with 3 tables and 12 images extracted.',
  details: {
    pages: 24,
    textBlocks: 156,
    tables: 3,
    images: 12,
    summary: `This quarterly financial report shows strong performance across all divisions. Revenue increased by 15% compared to Q3, with the technology division leading growth at 28%. Operating expenses were well-controlled, resulting in a 22% increase in net income.`,
    extractedTables: [
      { name: 'Revenue Breakdown', rows: 8, columns: 4 },
      { name: 'Expense Summary', rows: 12, columns: 3 },
      { name: 'Profit/Loss', rows: 6, columns: 5 },
    ],
    keyInsights: [
      'Revenue up 15% quarter-over-quarter',
      'Technology division shows strongest growth at 28%',
      'Operating expenses reduced by 5%',
      'Net income increased by 22%',
    ],
  },
};

export default function PdfPage() {
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
                  <p className="font-semibold">{(result.details as any)?.pages as number}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Type className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Text Blocks</p>
                  <p className="font-semibold">{(result.details as any)?.textBlocks as number}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Table className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Tables</p>
                  <p className="font-semibold">{(result.details as any)?.tables as number}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <ImageIcon className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Images</p>
                  <p className="font-semibold">{(result.details as any)?.images as number}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Content Tabs */}
          <Tabs defaultValue="summary" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="summary">Summary</TabsTrigger>
              <TabsTrigger value="tables">Tables</TabsTrigger>
              <TabsTrigger value="insights">Key Insights</TabsTrigger>
            </TabsList>

            <TabsContent value="summary">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Document Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-700 leading-relaxed">{(result.details as any)?.summary as string}</p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="tables">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {((result.details as any)?.extractedTables as Array<{ name: string; rows: number; columns: number }>)?.map(
                  (table, index) => (
                    <Card key={index}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium text-gray-900">{table.name}</p>
                            <p className="text-sm text-gray-500 mt-1">
                              {table.rows} rows × {table.columns} columns
                            </p>
                          </div>
                          <Button variant="ghost" size="sm">
                            <Download className="w-4 h-4 mr-1" />
                            CSV
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )
                )}
              </div>
            </TabsContent>

            <TabsContent value="insights">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Key Insights</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {((result.details as any)?.keyInsights as string[])?.map((insight, index) => (
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
