import { motion } from 'framer-motion';
import { Brain, Sparkles, FileText, Mic, Calendar, TrendingUp } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';

const SUGGESTED_PROMPTS = [
  { icon: FileText, text: 'Analyze this PDF document' },
  { icon: Mic, text: 'Transcribe and summarize audio' },
  { icon: Calendar, text: 'Check schedule for conflicts' },
  { icon: TrendingUp, text: 'Forecast next quarter trends' },
];

export function ChatInterface() {
  const {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    attachments,
    messagesEndRef,
    sendMessage,
    addAttachment,
    removeAttachment,
  } = useChat();

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">AI Assistant</h1>
            <p className="text-xs text-gray-500">Powered by Reasoner</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-sm text-gray-500">Online</span>
        </div>
      </header>

      {/* Chat Content */}
      <div className="flex-1 overflow-y-auto">
        {!hasMessages ? (
          /* Welcome State */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="flex flex-col items-center justify-center h-full px-6 py-12"
          >
            {/* Logo */}
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-6 shadow-xl shadow-indigo-500/20">
              <Brain className="w-10 h-10 text-white" />
            </div>

            {/* Title */}
            <h2 className="text-2xl font-semibold text-gray-900 mb-2 text-center">
              What can I help you analyze today?
            </h2>
            <p className="text-gray-500 text-center mb-8 max-w-md">
              Upload files or ask questions. I can analyze schedules, documents, audio, CAD files, and more.
            </p>

            {/* Suggested Prompts */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {SUGGESTED_PROMPTS.map((prompt, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 + 0.3 }}
                  onClick={() => setInputValue(prompt.text)}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 bg-white border border-gray-200 rounded-xl',
                    'text-left transition-all duration-200',
                    'hover:border-indigo-300 hover:shadow-md hover:-translate-y-0.5'
                  )}
                >
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                    <prompt.icon className="w-4 h-4 text-indigo-600" />
                  </div>
                  <span className="text-sm text-gray-700">{prompt.text}</span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        ) : (
          /* Chat Messages */
          <div className="max-w-3xl mx-auto px-6 py-8">
            {messages.map((message, index) => (
              <ChatMessage key={message.id} message={message} index={index} />
            ))}
            
            {/* Loading Indicator */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-4 mb-6"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                  <Brain className="w-4 h-4 text-white" />
                </div>
                <div className="flex items-center gap-1 px-4 py-3 bg-white border border-gray-200 rounded-2xl">
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

      {/* Input Area */}
      <div className="max-w-3xl mx-auto w-full">
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSend={sendMessage}
          onAttach={addAttachment}
          attachments={attachments}
          onRemoveAttachment={removeAttachment}
          isLoading={isLoading}
          placeholder="Type your message or drop files here..."
        />
      </div>
    </div>
  );
}
