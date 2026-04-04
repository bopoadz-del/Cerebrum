import React, { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, File, X, Check, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

interface FileUploadProps {
  acceptedFormats: string[];
  maxFileSize: number; // in MB
  onUpload: (files: File[]) => void;
  multiple?: boolean;
  onFileSelect?: (file: File, updateProgress: (progress: number, status: 'uploading' | 'completed' | 'error', error?: string) => void) => void;
  isProcessing?: boolean;
}

interface UploadFile {
  file: File;
  id: string;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

export function FileUpload({ 
  acceptedFormats, 
  maxFileSize, 
  onUpload, 
  multiple = true,
  onFileSelect,
  isProcessing = false
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [files, setFiles] = useState<UploadFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file: File): string | null => {
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    const isValidFormat = acceptedFormats.some(format => 
      format.toLowerCase() === fileExtension
    );
    
    if (!isValidFormat) {
      return `Invalid format. Accepted: ${acceptedFormats.join(', ')}`;
    }
    
    if (file.size > maxFileSize * 1024 * 1024) {
      return `File too large. Max size: ${maxFileSize}MB`;
    }
    
    return null;
  };

  // Real upload with progress tracking via callback
  const startUpload = useCallback((fileId: string, file: File) => {
    setFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, status: 'uploading' } : f
    ));

    if (onFileSelect) {
      // Use real progress from parent
      onFileSelect(file, (progress, status, error) => {
        setFiles(prev => prev.map(f => 
          f.id === fileId ? { ...f, progress, status, error } : f
        ));
      });
    } else {
      // Fallback to simulation if no real progress handler
      simulateUpload(fileId);
    }
  }, [onFileSelect]);

  // Simulated upload for fallback
  const simulateUpload = useCallback((fileId: string) => {
    setFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, status: 'uploading' } : f
    ));

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        setFiles(prev => prev.map(f => 
          f.id === fileId ? { ...f, progress: 100, status: 'completed' } : f
        ));
      } else {
        setFiles(prev => prev.map(f => 
          f.id === fileId ? { ...f, progress } : f
        ));
      }
    }, 200);
  }, []);

  const handleFiles = useCallback((newFiles: FileList | null) => {
    if (!newFiles) return;

    const filesArray = Array.from(newFiles);
    const uploadFiles: UploadFile[] = filesArray.map((file, index) => {
      const error = validateFile(file);
      return {
        file,
        id: `${Date.now()}-${index}`,
        progress: 0,
        status: error ? 'error' : 'pending',
        error: error || undefined,
      };
    });

    setFiles(prev => [...prev, ...uploadFiles]);

    // Start upload for valid files
    uploadFiles.forEach((uploadFile) => {
      if (uploadFile.status !== 'error') {
        startUpload(uploadFile.id, uploadFile.file);
      }
    });
  }, [acceptedFormats, maxFileSize, startUpload]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const handleAnalyze = () => {
    const completedFiles = files
      .filter(f => f.status === 'completed')
      .map(f => f.file);
    onUpload(completedFiles);
  };

  const completedCount = files.filter(f => f.status === 'completed').length;
  const uploadingCount = files.filter(f => f.status === 'uploading').length;

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <motion.div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'upload-zone cursor-pointer p-12 text-center transition-all duration-200',
          isDragOver && 'border-indigo-500 bg-indigo-50/50 scale-[1.02]',
          isProcessing && 'opacity-50 cursor-not-allowed'
        )}
        whileHover={!isProcessing ? { scale: 1.01 } : undefined}
        whileTap={!isProcessing ? { scale: 0.99 } : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={acceptedFormats.join(',')}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={isProcessing}
        />
        
        <motion.div
          animate={{ y: isDragOver ? -5 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-indigo-50 flex items-center justify-center">
            {isProcessing ? (
              <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
            ) : (
              <Upload className={cn(
                'w-8 h-8 transition-colors',
                isDragOver ? 'text-indigo-600' : 'text-indigo-400'
              )} />
            )}
          </div>
          
          <p className="text-lg font-medium text-gray-900 mb-1">
            {isProcessing 
              ? 'Processing...' 
              : isDragOver 
                ? 'Drop files here' 
                : 'Drag & drop files here'}
          </p>
          <p className="text-sm text-gray-500 mb-4">
            {isProcessing ? 'Please wait while we process your files' : 'or click to browse from your computer'}
          </p>
          
          {!isProcessing && (
            <>
              <div className="flex flex-wrap justify-center gap-2">
                {acceptedFormats.map((format) => (
                  <span
                    key={format}
                    className="px-2.5 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded-full"
                  >
                    {format}
                  </span>
                ))}
              </div>
              <p className="mt-3 text-xs text-gray-400">
                Maximum file size: {maxFileSize}MB
              </p>
            </>
          )}
        </motion.div>
      </motion.div>

      {/* File List */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-2"
          >
            {files.map((uploadFile) => (
              <motion.div
                key={uploadFile.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className={cn(
                  'flex items-center gap-4 p-4 bg-white border rounded-xl transition-colors',
                  uploadFile.status === 'error' ? 'border-red-200 bg-red-50' : 'border-gray-200',
                  isProcessing && 'opacity-75'
                )}
              >
                <div className={cn(
                  'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                  uploadFile.status === 'error' ? 'bg-red-100' : 
                  uploadFile.status === 'completed' ? 'bg-emerald-100' : 'bg-indigo-50'
                )}>
                  {uploadFile.status === 'completed' ? (
                    <Check className="w-5 h-5 text-emerald-600" />
                  ) : uploadFile.status === 'error' ? (
                    <AlertCircle className="w-5 h-5 text-red-600" />
                  ) : uploadFile.status === 'uploading' ? (
                    <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
                  ) : (
                    <File className="w-5 h-5 text-indigo-600" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {uploadFile.file.name}
                    </p>
                    <span className="text-xs text-gray-500 ml-2">
                      {formatFileSize(uploadFile.file.size)}
                    </span>
                  </div>
                  
                  {uploadFile.status === 'error' ? (
                    <p className="text-xs text-red-600">{uploadFile.error}</p>
                  ) : uploadFile.status === 'uploading' ? (
                    <div className="flex items-center gap-3">
                      <Progress value={uploadFile.progress} className="flex-1 h-1.5" />
                      <span className="text-xs text-gray-500 w-12 text-right">
                        {Math.round(uploadFile.progress)}%
                      </span>
                    </div>
                  ) : uploadFile.status === 'completed' ? (
                    <p className="text-xs text-emerald-600">Upload complete</p>
                  ) : (
                    <p className="text-xs text-gray-400">Waiting...</p>
                  )}
                </div>

                <button
                  onClick={() => removeFile(uploadFile.id)}
                  disabled={isProcessing}
                  className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Analyze Button */}
      {completedCount > 0 && !isProcessing && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-end"
        >
          <Button
            onClick={handleAnalyze}
            disabled={uploadingCount > 0}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 disabled:opacity-50"
          >
            {uploadingCount > 0 ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>Analyze {completedCount} file{completedCount > 1 ? 's' : ''}</>
            )}
          </Button>
        </motion.div>
      )}
    </div>
  );
}
