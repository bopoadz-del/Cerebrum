import { useState } from 'react';
import { motion } from 'framer-motion';
import { Archive, FileText, Folder, Clock, Search, Download, Trash2 } from 'lucide-react';
import { ModuleHeader } from '@/components/ModuleHeader';
import { FileUpload } from '@/components/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { AnalysisResult } from '@/types';

const ACCEPTED_FORMATS = ['.zip', '.rar', '.7z', '.tar', '.gz'];
const MAX_FILE_SIZE = 500; // MB

const mockFiles = [
  { id: 1, name: 'Project-Documents.zip', size: '45.2 MB', date: '2024-01-15', type: 'zip', count: 156 },
  { id: 2, name: 'CAD-Drawings.rar', size: '128.5 MB', date: '2024-01-14', type: 'rar', count: 42 },
  { id: 3, name: 'Meeting-Recordings.zip', size: '256.8 MB', date: '2024-01-12', type: 'zip', count: 23 },
  { id: 4, name: 'Financial-Reports.7z', size: '18.3 MB', date: '2024-01-10', type: '7z', count: 89 },
];

const mockResult: AnalysisResult = {
  id: '1',
  moduleId: 'archive',
  fileName: 'Project-Backup.zip',
  status: 'completed',
  createdAt: new Date(),
  completedAt: new Date(),
  summary: 'Archive analysis completed. 312 files found across 15 folders.',
  details: {
    totalFiles: 312,
    totalFolders: 15,
    totalSize: '456.8 MB',
    compressedSize: '128.5 MB',
    compressionRatio: 72,
    fileTypes: [
      { type: 'PDF', count: 89, size: '125 MB' },
      { type: 'DOC/DOCX', count: 45, size: '68 MB' },
      { type: 'XLS/XLSX', count: 32, size: '42 MB' },
      { type: 'Images', count: 98, size: '156 MB' },
      { type: 'Other', count: 48, size: '65 MB' },
    ],
  },
};

export default function ArchivePage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleUpload = async (_files: File[]) => {
    setIsAnalyzing(true);
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setResult(mockResult);
    setIsAnalyzing(false);
  };

  const filteredFiles = mockFiles.filter((file) =>
    file.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-8">
      <ModuleHeader
        title="Archive Analysis"
        description="Extract and analyze contents of compressed archives"
        icon={Archive}
        iconColor="purple"
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

      {/* Archive List */}
      <Card className="mb-8">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Recent Archives</CardTitle>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search archives..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {filteredFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
                    <Archive className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {file.count} files • {file.size}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-400">{file.date}</span>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Download className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {isAnalyzing && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-12"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-gray-600">Extracting archive contents...</span>
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
                  <p className="text-sm text-gray-500">Files</p>
                  <p className="font-semibold">{((result.details as any)?.totalFiles as number).toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Folder className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="text-sm text-gray-500">Folders</p>
                  <p className="font-semibold">{(result.details as any)?.totalFolders as number}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Archive className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">Compressed</p>
                  <p className="font-semibold">{(result.details as any)?.compressedSize as string}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-3">
                <Clock className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Compression</p>
                  <p className="font-semibold">{(result.details as any)?.compressionRatio}%</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* File Types */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">File Type Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {((result.details as any)?.fileTypes as Array<{ type: string; count: number; size: string }>)?.map(
                  (fileType, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                          <FileText className="w-4 h-4 text-indigo-600" />
                        </div>
                        <span className="font-medium text-gray-900">{fileType.type}</span>
                      </div>
                      <div className="flex items-center gap-6">
                        <span className="text-sm text-gray-500">{fileType.count} files</span>
                        <span className="text-sm font-medium text-gray-900 w-20 text-right">
                          {fileType.size}
                        </span>
                      </div>
                    </div>
                  )
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
