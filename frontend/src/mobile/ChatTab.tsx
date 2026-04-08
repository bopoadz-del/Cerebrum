import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Bot, Loader2, Sparkles, Calendar, MessageSquare } from 'lucide-react';
import { ChatMessage } from '@/components/ChatMessage';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface ChatTabProps {
  projectName?: string;
}

const SUGGESTED_PROMPTS = [
  '/cost concrete foundation',
  '/formula beam moment',
  '/estimate warehouse 100000',
  '/city Riyadh',
];

export function ChatTab({ projectName }: ChatTabProps) {
  const {
    messages,
    input,
    setInput,
    isLoading,
    sendMessage,
    clearMessages,
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const hasMessages = messages.length > 0;
  const isProjectSelected = projectName && projectName !== 'Select a project';

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (input.trim()) {
      sendMessage(input, []);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="px-4 py-3 bg-white border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-indigo-600" />
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">
              {isProjectSelected ? projectName : 'Chat'}
            </h2>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Calendar className="w-3.5 h-3.5" />
              {today}
            </div>
          </div>
          {hasMessages && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearMessages}
              className="text-gray-500"
            >
              Clear
            </Button>
          )}
        </div>
      </header>

      {/* Chat Content */}
      <div className="flex-1 overflow-y-auto">
        {!hasMessages ? (
          /* Welcome State */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col items-center justify-center h-full px-6 py-8"
          >
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-5 shadow-lg">
              <Bot className="w-8 h-8 text-white" />
            </div>

            <h2 className="text-xl font-semibold text-gray-900 mb-2 text-center">
              Cerebrum AI
            </h2>
            <p className="text-gray-600 text-center mb-6 max-w-sm">
              Access RSMeans data, construction formulas, and cost estimates instantly.
            </p>

            <div className="grid grid-cols-2 gap-3 w-full max-w-sm mb-6">
              <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <p className="text-sm font-semibold text-indigo-600 mb-1">📊 Cost Data</p>
                <p className="text-xs text-gray-500">135+ RSMeans items</p>
              </div>
              <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <p className="text-sm font-semibold text-indigo-600 mb-1">📐 Formulas</p>
                <p className="text-xs text-gray-500">20+ calculations</p>
              </div>
              <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <p className="text-sm font-semibold text-indigo-600 mb-1">🏢 Estimates</p>
                <p className="text-xs text-gray-500">15 building types</p>
              </div>
              <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
                <p className="text-sm font-semibold text-indigo-600 mb-1">📍 Locations</p>
                <p className="text-xs text-gray-500">30+ city indices</p>
              </div>
            </div>

            <div className="flex flex-wrap justify-center gap-2 max-w-sm">
              {SUGGESTED_PROMPTS.map((prompt, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => setInput(prompt)}
                  className={cn(
                    'px-4 py-3 bg-white border border-gray-200 rounded-xl',
                    'text-sm text-gray-700 font-medium transition-all duration-200',
                    'hover:border-indigo-300 hover:shadow-sm active:bg-gray-50',
                    'min-h-[44px]'
                  )}
                >
                  {prompt}
                </motion.button>
              ))}
            </div>
          </motion.div>
        ) : (
          /* Chat Messages */
          <div className="px-4 py-4 space-y-4">
            {messages.map((message, index) => (
              <ChatMessage key={message.id} message={message} index={index} />
            ))}

            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-3"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="flex items-center gap-1.5 px-4 py-3 bg-white border border-gray-200 rounded-2xl shadow-sm">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area - Fixed at bottom */}
      <div className="p-4 bg-white border-t border-gray-200 flex-shrink-0">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isProjectSelected ? 'Type /help for commands...' : 'Type /help or select a project...'}
              rows={1}
              className={cn(
                'w-full px-4 py-3 pr-4 bg-gray-100 border-0 rounded-2xl resize-none',
                'text-base text-gray-900 placeholder:text-gray-400',
                'focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white',
                'transition-all duration-200'
              )}
              style={{ minHeight: '52px', maxHeight: '120px' }}
            />
          </div>

          <Button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={cn(
              'flex-shrink-0 w-14 h-[52px] rounded-2xl bg-indigo-600 hover:bg-indigo-700',
              'text-white shadow-md hover:shadow-lg transition-all duration-200',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none',
              'min-h-[52px]'
            )}
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
