import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Folder, 
  FileText, 
  Upload, 
  X, 
  File,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { Attachment } from '@/types';

interface ProjectsTabProps {
  projectName?: string;
  onAttachFile?: (file: File) => void;
  attachments?: Attachment[];
  onRemoveAttachment?: (id: string) => void;
  isUploading?: boolean;
}

export function ProjectsTab({ 
  projectName,
  onAttachFile,
  attachments = [],
  onRemoveAttachment,
  isUploading = false
}: ProjectsTabProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onAttachFile) {
      onAttachFile(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && onAttachFile) {
      onAttachFile(file);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (['pdf'].includes(ext || '')) return <File className="w-5 h-5 text-red-500" />;
    if (['doc', 'docx'].includes(ext || '')) return <File className="w-5 h-5 text-blue-500" />;
    if (['xls', 'xlsx'].includes(ext || '')) return <File className="w-5 h-5 text-green-500" />;
    if (['ppt', 'pptx'].includes(ext || '')) return <File className="w-5 h-5 text-orange-500" />;
    if (['jpg', 'jpeg', 'png', 'gif'].includes(ext || '')) return <File className="w-5 h-5 text-purple-500" />;
    return <File className="w-5 h-5 text-gray-500" />;
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Folder className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">
            {projectName || 'Projects'}
          </h2>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Upload files to analyze with AI
        </p>
      </div>

      {/* Upload Area */}
      <div className="p-4">
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileSelect}
          className="hidden"
          accept=".pdf,.txt,.md,.doc,.docx,.png,.jpg,.jpeg,.tiff,.csv,.json,.xml,.html,.mp3,.mp4,.mov,.webm"
        />
        
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={cn(
            'min-h-[120px] rounded-xl border-2 border-dashed transition-all duration-200',
            'flex flex-col items-center justify-center p-6',
            'cursor-pointer touch-manipulation',
            isDragging 
              ? 'border-indigo-500 bg-indigo-50' 
              : 'border-gray-300 bg-gray-50 hover:border-indigo-400 hover:bg-gray-100'
          )}
          style={{ minHeight: '120px' }}
        >
          <div className={cn(
            'w-14 h-14 rounded-full flex items-center justify-center mb-3 transition-colors',
            isDragging ? 'bg-indigo-100' : 'bg-white'
          )}>
            <Upload className={cn(
              'w-7 h-7 transition-colors',
              isDragging ? 'text-indigo-600' : 'text-gray-400'
            )} />
          </div>
          <p className="text-base font-medium text-gray-900 text-center">
            Tap to upload files
          </p>
          <p className="text-sm text-gray-500 text-center mt-1">
            PDF, DOC, Images, and more
          </p>
        </div>
      </div>

      {/* Files List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">
          Attached Files ({attachments.length})
        </h3>
        
        {attachments.length === 0 && !isUploading && (
          <div className="text-center py-8 text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-base">No files attached yet</p>
          </div>
        )}

        <AnimatePresence>
          {isUploading && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex items-center gap-3 p-4 mb-3 bg-amber-50 border border-amber-200 rounded-xl"
            >
              <Loader2 className="w-5 h-5 text-amber-600 animate-spin" />
              <span className="text-base text-amber-900">Uploading...</span>
            </motion.div>
          )}

          {attachments.map((attachment) => (
            <motion.div
              key={attachment.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={cn(
                'flex items-center gap-3 p-4 mb-3 rounded-xl border transition-colors',
                attachment.status === 'error'
                  ? 'bg-red-50 border-red-200'
                  : attachment.status === 'uploading'
                  ? 'bg-amber-50 border-amber-200'
                  : 'bg-white border-gray-200'
              )}
            >
              {getFileIcon(attachment.name)}
              
              <div className="flex-1 min-w-0">
                <p className={cn(
                  'text-base font-medium truncate',
                  attachment.status === 'error' ? 'text-red-900' : 'text-gray-900'
                )}>
                  {attachment.name}
                </p>
                <p className={cn(
                  'text-sm',
                  attachment.status === 'error' ? 'text-red-600' : 'text-gray-500'
                )}>
                  {formatFileSize(attachment.size)}
                  {attachment.status === 'error' && attachment.error && (
                    <span className="ml-2">• {attachment.error}</span>
                  )}
                </p>
              </div>

              {attachment.status === 'uploading' ? (
                <Loader2 className="w-5 h-5 text-amber-600 animate-spin flex-shrink-0" />
              ) : attachment.status === 'error' ? (
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              ) : (
                <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0" />
              )}

              {onRemoveAttachment && attachment.status !== 'uploading' && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onRemoveAttachment(attachment.id)}
                  className="flex-shrink-0 w-10 h-10 rounded-full hover:bg-gray-100"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </Button>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
