import { useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Paperclip, 
  X, 
  FileText, 
  AlertCircle, 
  Check, 
  Loader2, 
  Image as ImageIcon,
  Mic,
  Globe,
  Code2,
  Sparkles
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import type { Attachment } from '@/types';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onAttach?: (file: File) => void;
  attachments?: Attachment[];
  onRemoveAttachment?: (id: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  // New Kimi-like features
  onWebSearchToggle?: () => void;
  isWebSearchEnabled?: boolean;
  onCodeModeToggle?: () => void;
  isCodeModeEnabled?: boolean;
  onImageUpload?: (file: File) => void;
  enableVoice?: boolean;
  onVoiceStart?: () => void;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  onAttach,
  attachments = [],
  onRemoveAttachment,
  isLoading = false,
  placeholder = 'Type a message...',
  // New props
  onWebSearchToggle,
  isWebSearchEnabled = false,
  onCodeModeToggle,
  isCodeModeEnabled = false,
  onImageUpload,
  enableVoice = true,
  onVoiceStart,
}: ChatInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [showToolbar, setShowToolbar] = useState(false);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && onAttach) {
      Array.from(files).forEach(file => {
        // Route images to image handler if available
        if (file.type.startsWith('image/') && onImageUpload) {
          onImageUpload(file);
        } else {
          onAttach(file);
        }
      });
    }
    e.target.value = '';
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && onImageUpload) {
      Array.from(files).forEach(onImageUpload);
    }
    e.target.value = '';
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    files.forEach(file => {
      if (file.type.startsWith('image/') && onImageUpload) {
        onImageUpload(file);
      } else if (onAttach) {
        onAttach(file);
      }
    });
  }, [onAttach, onImageUpload]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Separate image and non-image attachments
  const imageAttachments = attachments.filter(att => att.type.startsWith('image/'));
  const fileAttachments = attachments.filter(att => !att.type.startsWith('image/'));
  const hasAttachments = attachments.length > 0;

  return (
    <div
      className={cn(
        'bg-white border-t border-gray-200 px-4 py-4 transition-colors duration-200',
        isDragOver && 'bg-indigo-50/50'
      )}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      {/* Drag Overlay */}
      <AnimatePresence>
        {isDragOver && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-indigo-500/10 backdrop-blur-sm flex items-center justify-center pointer-events-none"
          >
            <div className="bg-white rounded-2xl shadow-2xl p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-indigo-100 flex items-center justify-center">
                <ImageIcon className="w-8 h-8 text-indigo-600" />
              </div>
              <p className="text-xl font-semibold text-gray-900">Drop files here</p>
              <p className="text-sm text-gray-500 mt-1">Images and documents supported</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Image Attachments Preview */}
      <AnimatePresence>
        {imageAttachments.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-2 mb-3"
          >
            {imageAttachments.map((attachment) => (
              <motion.div
                key={attachment.id}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="relative group"
              >
                <div className="w-20 h-20 rounded-lg overflow-hidden border border-gray-200 bg-gray-100">
                  {attachment.url ? (
                    <img 
                      src={attachment.url} 
                      alt={attachment.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <ImageIcon className="w-6 h-6 text-gray-400" />
                    </div>
                  )}
                </div>
                
                {/* Status Overlay */}
                {attachment.status === 'uploading' && (
                  <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                  </div>
                )}
                {attachment.status === 'error' && (
                  <div className="absolute inset-0 bg-red-500/50 flex items-center justify-center">
                    <AlertCircle className="w-5 h-5 text-white" />
                  </div>
                )}
                
                {/* Remove Button */}
                {onRemoveAttachment && (
                  <button
                    onClick={() => onRemoveAttachment(attachment.id)}
                    className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* File Attachments */}
      <AnimatePresence>
        {fileAttachments.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-2 mb-3"
          >
            {fileAttachments.map((attachment) => (
              <motion.div
                key={attachment.id}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className={cn(
                  'flex flex-col gap-1.5 px-3 py-2 border rounded-lg min-w-[200px] max-w-[300px]',
                  attachment.status === 'error'
                    ? 'bg-red-50 border-red-200'
                    : attachment.status === 'complete'
                    ? 'bg-emerald-50 border-emerald-200'
                    : 'bg-indigo-50 border-indigo-100'
                )}
              >
                <div className="flex items-center gap-2">
                  {attachment.status === 'error' ? (
                    <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  ) : attachment.status === 'complete' ? (
                    <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                  ) : attachment.status === 'uploading' ? (
                    <Loader2 className="w-4 h-4 text-indigo-600 animate-spin flex-shrink-0" />
                  ) : (
                    <FileText className="w-4 h-4 text-indigo-600 flex-shrink-0" />
                  )}
                  <span
                    className={cn(
                      'text-sm max-w-[150px] truncate',
                      attachment.status === 'error'
                        ? 'text-red-900'
                        : attachment.status === 'complete'
                        ? 'text-emerald-900'
