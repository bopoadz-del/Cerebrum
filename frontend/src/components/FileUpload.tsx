import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, X, FileText, Image as ImageIcon, Loader2, Check, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

type AttachmentStatus = 'uploading' | 'complete' | 'error';

interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  status: AttachmentStatus;
}

interface FileUploadProps {
  attachments: Attachment[];
  onRemove?: (id: string) => void;
  onUpload?: (file: File) => void;
  maxSize?: number;
  acceptedTypes?: string;
  className?: string;
}

export function FileUpload({
  attachments,
  onRemove,
  onUpload,
  maxSize = 10,
  acceptedTypes = '*/*',
  className,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleFile = (file: File) => {
    if (file.size > maxSize * 1024 * 1024) {
      alert(`File size must be less than ${maxSize}MB`);
      return;
    }
    onUpload?.(file);
  };

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return <ImageIcon className="w-5 h-5" />;
    return <FileText className="w-5 h-5" />;
  };

  const getStatusIcon = (status: AttachmentStatus) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'complete':
        return <Check className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className={cn('space-y-2', className)}>
      {/* Upload Area */}
      {attachments.length === 0 && onUpload && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            'border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all duration-200',
            isDragging
              ? 'border-indigo-500 bg-indigo-50'
              : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          )}
        >
          <div className="flex items-center justify-center gap-2 text-gray-600">
            <Upload className="w-5 h-5" />
            <span className="text-sm">Drop files here or click to upload</span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptedTypes}
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            className="hidden"
          />
        </div>
      )}

      {/* Attachment List */}
      <AnimatePresence>
        {attachments.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-2"
          >
            {attachments.map((attachment) => (
              <motion.div
                key={attachment.id}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg border',
                  attachment.status === 'error'
                    ? 'bg-red-50 border-red-200'
                    : attachment.status === 'complete'
                    ? 'bg-green-50 border-green-200'
                    : 'bg-gray-50 border-gray-200'
                )}
              >
                {getFileIcon(attachment.type)}
                <span className="text-sm truncate max-w-[150px]">{attachment.name}</span>
                {getStatusIcon(attachment.status)}
                {onRemove && (
                  <button
                    onClick={() => onRemove(attachment.id)}
                    className="p-1 hover:bg-black/10 rounded"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
