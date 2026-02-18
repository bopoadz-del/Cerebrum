import { useState } from 'react';
import { motion } from 'framer-motion';
import { User, Bot, FileText, Copy, Check, Share2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Message } from '@/types';

interface ChatMessageProps {
  message: Message;
  index: number;
}

export function ChatMessage({ message, index }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [showActions, setShowActions] = useState(false);

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: true,
    }).format(date);
  };

  const formatDate = (date: Date) => {
    const now = new Date();
    const msgDate = new Date(date);
    const isToday = msgDate.toDateString() === now.toDateString();
    const isYesterday = msgDate.toDateString() === new Date(now.setDate(now.getDate() - 1)).toDateString();
    
    if (isToday) return 'Today';
    if (isYesterday) return 'Yesterday';
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
    }).format(msgDate);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Reasoner Chat',
          text: message.content,
        });
      } catch (err) {
        console.log('Share cancelled');
      }
    } else {
      handleCopy();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.3,
        delay: index * 0.05,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      className={cn('flex gap-3 mb-4 group', isUser ? 'flex-row-reverse' : 'flex-row')}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          isUser ? 'bg-gray-200' : 'bg-gradient-to-br from-indigo-500 to-purple-600'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-gray-600" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={cn('flex flex-col max-w-[80%]', isUser ? 'items-end' : 'items-start')}>
        {/* Date Badge (if not today) */}
        {index === 0 || formatDate(message.timestamp) !== formatDate(new Date(Date.now() - 86400000)) && (
          <div className="mb-2 px-3 py-1 bg-gray-100 rounded-full text-xs text-gray-500">
            {formatDate(message.timestamp)}
          </div>
        )}

        {/* Bubble */}
        <div
          className={cn(
            'relative px-4 py-3 text-sm leading-relaxed',
            isUser
              ? 'message-user bg-indigo-600 text-white'
              : 'message-ai bg-white border border-gray-200 text-gray-900 shadow-sm'
          )}
        >
          {message.content}

          {/* Action Buttons (hover) */}
          {!isUser && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: showActions ? 1 : 0 }}
              className="absolute -top-8 right-0 flex gap-1"
            >
              <button
                onClick={handleCopy}
                className="p-1.5 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
                title="Copy"
              >
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-gray-500" />
                )}
              </button>
              <button
                onClick={handleShare}
                className="p-1.5 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition-colors"
                title="Share"
              >
                <Share2 className="w-3.5 h-3.5 text-gray-500" />
              </button>
            </motion.div>
          )}
        </div>

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="mt-2 space-y-2">
            {message.attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="flex items-center gap-3 px-3 py-2 bg-white border border-gray-200 rounded-lg shadow-sm"
              >
                <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
                  <FileText className="w-4 h-4 text-indigo-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{attachment.name}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(attachment.size)}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="mt-1 text-xs text-gray-400 flex items-center gap-2">
          {formatTime(message.timestamp)}
          {isUser && <span className="text-gray-300">|</span>}
          {isUser && <span className="text-gray-400">Sent</span>}
        </span>
      </div>
    </motion.div>
  );
}
