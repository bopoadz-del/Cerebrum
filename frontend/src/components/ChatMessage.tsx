import { useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, User, Copy, Check, ThumbsUp, ThumbsDown, RefreshCw, FileText, Image as ImageIcon, Code } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { MarkdownRenderer } from './MarkdownRenderer';
import { CodeExecutionDisplay } from './CodeExecutionDisplay';
import { ReasoningDisplay } from './ReasoningDisplay';
import type { Message } from '@/types';

interface ChatMessageProps {
  message: Message;
  isLoading?: boolean;
  onRegenerate?: () => void;
  onFeedback?: (type: 'up' | 'down') => void;
}

export function ChatMessage({
  message,
  isLoading = false,
  onRegenerate,
  onFeedback,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex gap-3 p-4 rounded-xl',
        isUser ? 'bg-indigo-50/50' : 'bg-white'
      )}
    >
      {/* Avatar */}
      <div className={cn(
        'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
        isUser ? 'bg-indigo-600' : 'bg-gradient-to-br from-indigo-500 to-purple-600'
      )}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className={cn(
            'text-sm font-medium',
            isUser ? 'text-indigo-900' : 'text-gray-900'
          )}>
            {isUser ? 'You' : 'Cerebrum AI'}
          </span>
          {message.timestamp && (
            <span className="text-xs text-gray-400">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Message Content */}
        <div className="prose prose-sm max-w-none">
          {isLoading ? (
            <div className="flex items-center gap-2 text-gray-500">
              <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce delay-100" />
              <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce delay-200" />
            </div>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>

        {/* Reasoning Display */}
        {!isUser && message.reasoning && (
          <ReasoningDisplay 
            reasoning={{
              steps: message.reasoning,
              toolsConsidered: message.reasoning
                .filter(r => r.type === 'tool')
                .map(r => r.content),
              whyThisAnswer: 'Based on the reasoning steps above',
            }} 
          />
        )}

        {/* Attachments */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {message.attachments.map((att) => (
              <div
                key={att.id}
                className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg"
              >
                {att.type.startsWith('image/') ? (
                  <ImageIcon className="w-4 h-4 text-gray-500" />
                ) : (
                  <FileText className="w-4 h-4 text-gray-500" />
                )}
                <span className="text-sm text-gray-700 truncate max-w-[200px]">
                  {att.name}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        {!isUser && !isLoading && (
          <div className="flex items-center gap-1 mt-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-8 px-2 text-gray-500 hover:text-gray-700"
            >
              {copied ? (
                <Check className="w-4 h-4" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </Button>
            
            {onRegenerate && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRegenerate}
                className="h-8 px-2 text-gray-500 hover:text-gray-700"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            )}
            
            {onFeedback && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onFeedback('up')}
                  className="h-8 px-2 text-gray-500 hover:text-gray-700"
                >
                  <ThumbsUp className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onFeedback('down')}
                  className="h-8 px-2 text-gray-500 hover:text-gray-700"
                >
                  <ThumbsDown className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
