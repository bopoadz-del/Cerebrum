import { useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Plus,
  Paperclip,
  Mic,
  Globe,
  X,
  FileText,
  Loader2,
  Camera,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { VoiceRecorder } from './VoiceRecorder';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Progress } from '@/components/ui/progress';
import type { Attachment } from '@/types';

interface ChatInputV2Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onAttachFile?: (file: File) => void;
  onOpenCamera?: () => void;
  onOpenMic?: () => void;
  onInternetSearch?: () => void;
  attachments?: Attachment[];
  onRemoveAttachment?: (id: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  isUploading?: boolean;
  webSearchEnabled?: boolean;
  codeModeEnabled?: boolean;
  imageModeEnabled?: boolean;
}

const menuItems = [
  { id: 'file', icon: Paperclip, label: 'File', color: 'text-blue-600', bgColor: 'bg-blue-50' },
  { id: 'internet', icon: Globe, label: 'Internet', color: 'text-emerald-600', bgColor: 'bg-emerald-50' },
];

// Coming soon features with tooltips
const comingSoonItems = [
  { id: 'camera', icon: Camera, label: 'Camera', color: 'text-gray-400', bgColor: 'bg-gray-100', tooltip: 'Camera feature coming soon' },
];

export function ChatInputV2({
  value,
  onChange,
  onSend,
  onAttachFile,
  onOpenCamera: _onOpenCamera,
  onOpenMic: _onOpenMic,
  onInternetSearch,
  attachments = [],
  onRemoveAttachment,
  isLoading = false,
  placeholder = 'Type a message...',
  isUploading = false,
  webSearchEnabled = false,
  codeModeEnabled = false,
  imageModeEnabled = false,
}: ChatInputV2Props) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isVoiceRecorderOpen, setIsVoiceRecorderOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onAttachFile) {
      onAttachFile(file);
    }
    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleMenuClick = (id: string) => {
    setIsMenuOpen(false);
    switch (id) {
      case 'file':
        fileInputRef.current?.click();
        break;
      // Camera feature disabled - not yet implemented
      // case 'camera':
      //   onOpenCamera?.();
      //   break;
      case 'internet':
        onInternetSearch?.();
        break;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Handle voice transcript
  const handleVoiceTranscript = useCallback((transcript: string) => {
    // Append transcript to current input value
    const newValue = value ? `${value} ${transcript}` : transcript;
    onChange(newValue);
    
    // Focus the textarea after voice input
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 100);
  }, [value, onChange]);

  // Toggle voice recorder
  const toggleVoiceRecorder = () => {
    setIsVoiceRecorderOpen(!isVoiceRecorderOpen);
    setIsMenuOpen(false);
  };

  return (
    <div className="bg-white border-t border-gray-200 px-4 py-4">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileSelect}
        className="hidden"
        accept=".pdf,.txt,.md,.doc,.docx,.png,.jpg,.jpeg,.tiff,.csv,.json,.xml,.html,.mp3,.mp4,.mov,.webm"
      />

      {/* Voice Recorder Overlay */}
      <VoiceRecorder
        isOpen={isVoiceRecorderOpen}
        onClose={() => setIsVoiceRecorderOpen(false)}
        onTranscript={handleVoiceTranscript}
        onCancel={() => setIsVoiceRecorderOpen(false)}
      />

      {/* Attachments Preview */}
      <AnimatePresence>
        {(attachments.length > 0 || isUploading) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-2 mb-3"
          >
            {attachments.map((attachment) => {
              const isLargeFile = attachment.size > 5 * 1024 * 1024; // > 5MB
              const isUploading = attachment.status === 'uploading';
              const progress = attachment.uploadProgress || 0;

              return (
                <motion.div
                  key={attachment.id}
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  className={cn(
                    'flex flex-col gap-1.5 px-3 py-2 rounded-lg border min-w-[200px]',
                    isUploading
                      ? 'bg-amber-50 border-amber-100'
                      : attachment.status === 'error'
                      ? 'bg-red-50 border-red-100'
                      : 'bg-indigo-50 border-indigo-100'
                  )}
                >
                  <div className="flex items-center gap-2">
                    <FileText className={cn(
                      'w-4 h-4',
                      isUploading ? 'text-amber-600' : attachment.status === 'error' ? 'text-red-600' : 'text-indigo-600'
                    )} />
                    <span className={cn(
                      'text-sm max-w-[150px] truncate',
                      isUploading ? 'text-amber-900' : attachment.status === 'error' ? 'text-red-900' : 'text-indigo-900'
                    )}>
                      {attachment.name}
                    </span>
                    <span className={cn(
                      'text-xs',
                      isUploading ? 'text-amber-600' : attachment.status === 'error' ? 'text-red-500' : 'text-indigo-500'
                    )}>
                      {formatFileSize(attachment.size)}
                    </span>
                    {onRemoveAttachment && !isUploading && (
                      <button
                        onClick={() => onRemoveAttachment(attachment.id)}
                        className="ml-1 p-0.5 hover:bg-indigo-100 rounded transition-colors"
                      >
                        <X className="w-3.5 h-3.5 text-indigo-600" />
                      </button>
                    )}
                  </div>
                  {/* Progress bar for uploading files or large files */}
                  {isUploading && (
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1">
                        <Progress value={progress} className="h-1.5" />
                      </div>
                      {isLargeFile && (
                        <span className="text-xs text-amber-700 font-medium min-w-[40px] text-right">
                          {progress}%
                        </span>
                      )}
                    </div>
                  )}
                  {/* Error message */}
                  {attachment.status === 'error' && attachment.error && (
                    <p className="text-xs text-red-600 mt-1">{attachment.error}</p>
                  )}
                </motion.div>
              );
            })}
            {/* Legacy uploading indicator for attachments without progress info */}
            {isUploading && attachments.length === 0 && (
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-100 rounded-lg"
              >
                <Loader2 className="w-4 h-4 text-amber-600 animate-spin" />
                <span className="text-sm text-amber-700">Uploading...</span>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Area */}
      <div className="flex items-end gap-2">
        {/* Plus Button with Menu */}
        <div className="relative">
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className={cn(
              'flex-shrink-0 w-12 h-12 rounded-xl transition-all duration-200',
              isMenuOpen
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            )}
          >
            <Plus className={cn('w-5 h-5 transition-transform', isMenuOpen && 'rotate-45')} />
          </Button>

          {/* Dropdown Menu */}
          <AnimatePresence>
            {isMenuOpen && (
              <TooltipProvider delayDuration={100}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: 10 }}
                  transition={{ duration: 0.15 }}
                  className="absolute bottom-full left-0 mb-2 w-40 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden z-50"
                >
                  {menuItems.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleMenuClick(item.id)}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                    >
                      <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', item.bgColor)}>
                        <item.icon className={cn('w-4 h-4', item.color)} />
                      </div>
                      <span className="text-sm font-medium text-gray-700">{item.label}</span>
                    </button>
                  ))}
                  {/* Coming Soon Items with Tooltips */}
                  {comingSoonItems.map((item) => (
                    <Tooltip key={item.id}>
                      <TooltipTrigger asChild>
                        <button
                          disabled
                          className="w-full flex items-center gap-3 px-4 py-3 opacity-50 cursor-not-allowed transition-colors text-left"
                        >
                          <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', item.bgColor)}>
                            <item.icon className={cn('w-4 h-4', item.color)} />
                          </div>
                          <span className="text-sm font-medium text-gray-500">{item.label}</span>
                        </button>
                      </TooltipTrigger>
                      <TooltipContent side="right">
                        <p>{item.tooltip}</p>
                      </TooltipContent>
                    </Tooltip>
                  ))}
                </motion.div>
              </TooltipProvider>
            )}
          </AnimatePresence>
        </div>

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
              'text-base text-gray-900 placeholder:text-gray-400',
              'focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white',
              'transition-all duration-200'
            )}
            style={{ minHeight: '48px', maxHeight: '150px' }}
          />
        </div>

        {/* Mic Button */}
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={toggleVoiceRecorder}
          className={cn(
            'flex-shrink-0 w-12 h-12 rounded-xl transition-all duration-200',
            isVoiceRecorderOpen
              ? 'bg-red-100 text-red-600 border-red-200 hover:bg-red-200'
              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
          )}
          title="Voice input"
        >
          <Mic className={cn('w-5 h-5', isVoiceRecorderOpen && 'animate-pulse')} />
        </Button>

        {/* Send Button */}
        <Button
          type="button"
          onClick={onSend}
          disabled={isLoading || (!value.trim() && attachments.length === 0)}
          className={cn(
            'flex-shrink-0 w-12 h-12 rounded-xl bg-indigo-600 hover:bg-indigo-700',
            'text-white shadow-md hover:shadow-lg transition-all duration-200',
            'disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none'
          )}
        >
          {isLoading ? (
            <div className="flex gap-0.5">
              <span className="w-1 h-1 bg-white rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1 h-1 bg-white rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1 h-1 bg-white rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          ) : (
            <Send className="w-4 h-4" />
          )}
        </Button>
      </div>

      {/* Click outside to close menu */}
      {isMenuOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsMenuOpen(false)}
        />
      )}
    </div>
  );
}
