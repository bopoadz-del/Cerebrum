import { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Plus,
  Paperclip,
  Camera,
  Mic,
  Globe,
  X,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { Attachment } from '@/types';

interface ChatInputV2Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onAttachFile?: () => void;
  onOpenCamera?: () => void;
  onOpenMic?: () => void;
  onInternetSearch?: () => void;
  attachments?: Attachment[];
  onRemoveAttachment?: (id: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

const menuItems = [
  { id: 'file', icon: Paperclip, label: 'File', color: 'text-blue-600', bgColor: 'bg-blue-50' },
  { id: 'camera', icon: Camera, label: 'Camera', color: 'text-purple-600', bgColor: 'bg-purple-50' },
  { id: 'mic', icon: Mic, label: 'Voice', color: 'text-amber-600', bgColor: 'bg-amber-50' },
  { id: 'internet', icon: Globe, label: 'Internet', color: 'text-emerald-600', bgColor: 'bg-emerald-50' },
];

export function ChatInputV2({
  value,
  onChange,
  onSend,
  onAttachFile,
  onOpenCamera,
  onOpenMic,
  onInternetSearch,
  attachments = [],
  onRemoveAttachment,
  isLoading = false,
  placeholder = 'Type a message...',
}: ChatInputV2Props) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleMenuClick = (id: string) => {
    setIsMenuOpen(false);
    switch (id) {
      case 'file':
        onAttachFile?.();
        break;
      case 'camera':
        onOpenCamera?.();
        break;
      case 'mic':
        onOpenMic?.();
        break;
      case 'internet':
        onInternetSearch?.();
        break;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="bg-white border-t border-gray-200 px-4 py-4">
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
      <div className="flex items-end gap-2">
        {/* Plus Button with Menu */}
        <div className="relative">
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className={cn(
              'flex-shrink-0 w-10 h-10 rounded-xl transition-all duration-200',
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
              </motion.div>
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
              'text-sm text-gray-900 placeholder:text-gray-400',
              'focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white',
              'transition-all duration-200'
            )}
            style={{ minHeight: '44px', maxHeight: '150px' }}
          />
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
