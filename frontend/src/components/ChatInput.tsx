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
  onWebSearchToggle,
  isWebSearchEnabled = false,
  onCodeModeToggle,
  isCodeModeEnabled = false,
  onImageUpload,
  enableVoice = false,
  onVoiceStart,
}: ChatInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onAttach) {
      onAttach(file);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && onAttach) {
      onAttach(file);
    }
  }, [onAttach]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

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
            className="absolute inset-0 bg-indigo-500/10 border-2 border-dashed border-indigo-400 rounded-lg flex items-center justify-center pointer-events-none z-10"
          >
            <span className="text-indigo-600 font-medium">Drop file here</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            className={cn(
              'w-full min-h-[44px] max-h-[200px] resize-none rounded-xl border border-gray-200',
              'px-4 py-3 pr-24 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20',
              'focus:border-indigo-500 transition-all duration-200',
              isLoading && 'opacity-50 cursor-not-allowed'
            )}
            rows={1}
          />
          
          {/* Toolbar */}
          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              title="Attach file"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            
            {enableVoice && (
              <button
                onClick={onVoiceStart}
                disabled={isLoading}
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                title="Voice input"
              >
                <Mic className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Send Button */}
        <Button
          onClick={onSend}
          disabled={isLoading || (!value.trim() && !hasAttachments)}
          className="h-11 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Feature Toggles */}
      <div className="flex items-center gap-2 mt-2">
        {onWebSearchToggle && (
          <button
            onClick={onWebSearchToggle}
            className={cn(
              'flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium transition-all duration-200',
              isWebSearchEnabled
                ? 'bg-blue-100 text-blue-700 border border-blue-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            <Globe className="w-3 h-3" />
            Web Search
          </button>
        )}
        
        {onCodeModeToggle && (
          <button
            onClick={onCodeModeToggle}
            className={cn(
              'flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium transition-all duration-200',
              isCodeModeEnabled
                ? 'bg-purple-100 text-purple-700 border border-purple-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            <Code2 className="w-3 h-3" />
            Code
          </button>
        )}
      </div>

      {/* File Attachments */}
      <AnimatePresence>
        {fileAttachments.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-2 mt-3"
          >
            {fileAttachments.map((attachment) => (
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
                    ? 'bg-emerald-50 border-emerald-200'
                    : 'bg-indigo-50 border-indigo-100'
                )}
              >
                {attachment.status === 'error' ? (
                  <AlertCircle className="w-4 h-4 text-red-600" />
                ) : attachment.status === 'complete' ? (
                  <Check className="w-4 h-4 text-emerald-600" />
                ) : (
                  <Loader2 className="w-4 h-4 text-indigo-600 animate-spin" />
                )}
                <span className="text-sm truncate max-w-[150px]">{attachment.name}</span>
                {onRemoveAttachment && (
                  <button
                    onClick={() => onRemoveAttachment(attachment.id)}
                    className="p-0.5 rounded hover:bg-black/10"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileSelect}
        className="hidden"
        accept="*/*"
      />
    </div>
  );
}
