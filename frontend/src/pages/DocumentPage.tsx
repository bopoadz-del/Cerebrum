import { useState } from 'react';
import { motion } from 'framer-motion';
import { File, Type, Image as ImageIcon, Table, Download, Eye } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AnalysisResult } from '@/types';

const ACCEPTED_FORMATS = ['.doc', '.docx', '.rtf', '.odt'];
const MAX_FILE_SIZE = 50; // MB

const mockResult: AnalysisResult = {
  id: '1',
  moduleId: 'document',
  fileName: 'Project-Proposal.docx',
  status: 'completed',
  createdAt: new Date(),
  completedAt: new Date(),
  summary: 'Document analysis completed. 24 pages with 3,847 words processed.',
  details: {
    pages: 24,
    words: 3847,
    characters: 28456,
    paragraphs: 156,
    headings: 12,
    tables: 3,
    images: 8,
    sections: [
      { name: 'Executive Summary', page: 1 },
      { name: 'Project Overview', page: 2 },
      { name: 'Technical Requirements', page: 5 },
      { name: 'Timeline & Milestones', page: 12 },
      { name: 'Budget & Resources', page: 18 },
      { name: 'Conclusion', page: 23 },
    ],
    metadata: {
      author: 'John Smith',
      created: '2024-01-10',
      modified: '2024-01-15',
      company: 'Acme Corporation',
    },
  },
};

export default function DocumentPage() {
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
        title="Document Analysis"
        description="Analyze Word documents for structure, content, and metadata"
        icon={File}
        iconColor="blue"
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
            <span className="text-gray-600">Analyzing document...</span>
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
                <File className="w-5 h-5 text-indigo-500" />
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
                  <p className="text-sm text-gray-500">Words</p>
                  <p className="font-semibold">{((result.details as any)?.words as number).toLocaleString()}</p>
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
          <Tabs defaultValue="structure" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="structure">Structure</TabsTrigger>
              <TabsTrigger value="metadata">Metadata</TabsTrigger>
              <TabsTrigger value="preview">Preview</TabsTrigger>
            </TabsList>

            <TabsContent value="structure">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Document Structure</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {((result.details as any)?.sections as Array<{ name: string; page: number }>)?.map(
                      (section, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                              <span className="text-sm font-medium text-indigo-600">
                                {index + 1}
                              </span>
                            </div>
                            <span className="font-medium text-gray-900">{section.name}</span>
                          </div>
                          <Badge variant="outline">Page {section.page}</Badge>
                        </div>
                      )
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="metadata">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Document Metadata</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries((result.details as any)?.metadata as Record<string, string>).map(
                      ([key, value]) => (
                        <div key={key} className="p-3 bg-gray-50 rounded-lg">
                          <p className="text-sm text-gray-500 capitalize">{key}</p>
                          <p className="font-medium text-gray-900">{value}</p>
                        </div>
                      )
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="preview">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">Document Preview</CardTitle>
                  <Button variant="outline" size="sm">
                    <Eye className="w-4 h-4 mr-1" />
                    Full Preview
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <File className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500">Preview not available in demo mode</p>
                    <Button className="mt-4" variant="outline">
                      <Download className="w-4 h-4 mr-1" />
                      Download Document
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </div>
  );
}
