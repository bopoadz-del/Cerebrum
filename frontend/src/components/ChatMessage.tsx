import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { User, Bot, FileText, Copy, Check, Share2, Image as ImageIcon, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Message } from '@/types';
import { ReasoningDisplay } from './ReasoningDisplay';
import { MarkdownRenderer } from './MarkdownRenderer';
import { WebSearchIndicator } from './WebSearchIndicator';
import { CodeExecutionDisplay } from './CodeExecutionDisplay';
import { ImageThumbnail, ImagePreviewModal } from './ImageAnalysis';

interface ChatMessageProps {
  message: Message;
  index: number;
}

export function ChatMessage({ message, index }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [isSearchCollapsed, setIsSearchCollapsed] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  // Calculate yesterday date once, memoized to avoid impure render
  const yesterdayStr = useMemo(() => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday.toDateString();
  }, []);

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: true,
    }).format(date);
  };

  const formatDate = (date: Date) => {
    const msgDate = new Date(date);
    const todayStr = new Date().toDateString();
    const msgDateStr = msgDate.toDateString();
    
    if (msgDateStr === todayStr) return 'Today';
    if (msgDateStr === yesterdayStr) return 'Yesterday';
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
          title: 'Cerebrum Chat',
          text: message.content,
        });
      } catch {
        console.log('Share cancelled');
      }
    } else {
      handleCopy();
    }
  };

  // Check if message has any special content
  const hasWebSearch = message.webSearch && message.webSearch.status !== 'error';
  const hasCodeExecution = message.codeExecution;
  const hasImageAnalysis = message.imageAnalysis;
  const hasAttachments = message.attachments && message.attachments.length > 0;
  const hasSuggestedReplies = message.suggestedReplies && message.suggestedReplies.length > 0;

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: 0.3,
          delay: index * 0.05,
          ease: [0.25, 0.46, 0.45, 0.94],
        }}
        className={cn('flex gap-3 mb-6 group', isUser ? 'flex-row-reverse' : 'flex-row')}
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
        <div className={cn('flex flex-col max-w-[85%]', isUser ? 'items-end' : 'items-start')}>
          {/* Date Badge (if not today) */}
          {index === 0 && (
            <div className="mb-2 px-3 py-1 bg-gray-100 rounded-full text-xs text-gray-500">
              {formatDate(message.timestamp)}
            </div>
          )}

          {/* Web Search Indicator */}
          {hasWebSearch && (
            <div className="mb-3 w-full max-w-lg">
              <WebSearchIndicator 
                searchData={message.webSearch!}
                isCollapsed={isSearchCollapsed}
                onToggleCollapse={() => setIsSearchCollapsed(!isSearchCollapsed)}
              />
            </div>
          )}

          {/* Main Message Bubble */}
          <div
            className={cn(
              'relative px-4 py-3',
              isUser
                ? 'message-user bg-indigo-600 text-white'
                : 'message-ai bg-white border border-gray-200 text-gray-900 shadow-sm'
            )}
          >
            {message.isThinking ? (
              <ReasoningDisplay isThinking />
            ) : (
              <>
                {/* Message Content with Markdown */}
                <div className={cn(
                  'text-sm leading-relaxed',
                  isUser ? 'text-white' : 'text-gray-800'
                )}>
                  {isUser ? (
                    // User messages: plain text or simple formatting
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  ) : (
                    // Assistant messages: full markdown rendering
                    <MarkdownRenderer content={message.content} />
                  )}
                </div>

                {/* Code Execution Display */}
                {hasCodeExecution && (
                  <div className="mt-4">
                    <CodeExecutionDisplay execution={message.codeExecution!} />
                  </div>
                )}

                {/* Image Analysis Result */}
                {hasImageAnalysis && (
                  <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Sparkles className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm text-gray-700">{message.imageAnalysis!.description}</p>
 