import { useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Paperclip, X, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
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
}: ChatInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && onAttach) {
      Array.from(files).forEach(onAttach);
    }
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files && onAttach) {
      Array.from(files).forEach(onAttach);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div
      className="bg-white border-t border-gray-200 px-4 py-4"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      {/* Attachments Preview */}
      <AnimatePresence>
        {attachments.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-2 mb-3"
          >
            {attachments.map((attachment) => (
              <motion.div
                key={attachment.id}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="flex items-center gap-2 px-3 py-1.5 bg-indigo-50 border border-indigo-100 rounded-lg"
              >
                <FileText className="w-4 h-4 text-indigo-600" />
                <span className="text-sm text-indigo-900 max-w-[150px] truncate">
                  {attachment.name}
                </span>
                <span className="text-xs text-indigo-500">{formatFileSize(attachment.size)}</span>
                {onRemoveAttachment && (
                  <button
                    onClick={() => onRemoveAttachment(attachment.id)}
                    className="ml-1 p-0.5 hover:bg-indigo-100 rounded transition-colors"
                  >
                    <X className="w-3.5 h-3.5 text-indigo-600" />
                  </button>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <div className="flex items-end gap-3">
        {/* Attach Button */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileChange}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          className="flex-shrink-0 w-10 h-10 rounded-xl text-gray-500 hover:text-gray-700 hover:bg-gray-100"
        >
          <Paperclip className="w-5 h-5" />
        </Button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            className={cn(
              'w-full px-4 py-3 pr-12 bg-gray-100 border-0 rounded-xl resize-none',
              'text-[15px] text-gray-900 placeholder:text-gray-400',
              'focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white',
              'transition-all duration-200'
            )}
            style={{ minHeight: '48px', maxHeight: '200px' }}
          />
          {value.length > 0 && (
            <span className="absolute right-3 bottom-3 text-xs text-gray-400">
              {value.length}
            </span>
          )}
        </div>

        {/* Send Button */}
        <Button
          type="button"
          onClick={onSend}
          disabled={isLoading || (!value.trim() && attachments.length === 0)}
          className={cn(
            'flex-shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700',
            'text-white shadow-md hover:shadow-lg transition-all duration-200',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none'
          )}
        >
          {isLoading ? (
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          ) : (
            <Send className="w-5 h-5" />
          )}
        </Button>
      </div>

      {/* Hint */}
      <p className="mt-2 text-xs text-gray-400 text-center">
        Press Enter to send, Shift + Enter for new line
      </p>
    </div>
  );
}
