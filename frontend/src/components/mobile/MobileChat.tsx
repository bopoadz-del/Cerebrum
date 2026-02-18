import { useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles, Calendar, MoreHorizontal, Copy, Share2 } from 'lucide-react';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInputV2 } from '@/components/ChatInputV2';
import { SmartContextToggle } from '@/components/SmartContextToggle';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface MobileChatProps {
  projectName?: string;
  chatTitle?: string;
  sessionToken?: string;
}

const SUGGESTED_PROMPTS = [
  'Analyze the Q4 financial data',
  'Generate a project timeline',
  'Review the CAD drawings',
  'Transcribe the meeting recording',
];

export function MobileChat({ projectName, sessionToken }: MobileChatProps) {
  const {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    attachments,
    messagesEndRef,
    sendMessage,
    removeAttachment,
  } = useChat();

  const [showActions, setShowActions] = useState(false);
  const [, setSmartContextEnabled] = useState(false);
  const hasMessages = messages.length > 0;

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const handleCopyChat = async () => {
    const chatText = messages.map(m => `${m.role}: ${m.content}`).join('\n\n');
    await navigator.clipboard.writeText(chatText);
  };

  const handleShareChat = async () => {
    if (navigator.share) {
      const chatText = messages.map(m => `${m.role}: ${m.content}`).join('\n\n');
      await navigator.share({
        title: 'Reasoner Chat',
        text: chatText,
      });
    } else {
      handleCopyChat();
    }
  };

  const handleSmartContextToggle = (enabled: boolean) => {
    setSmartContextEnabled(enabled);
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <header className="h-12 bg-white border-b border-gray-200 flex items-center justify-between px-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-indigo-100 flex items-center justify-center">
            <Sparkles className="w-3 h-3 text-indigo-600" />
          </div>
          <div>
            <h1 className="font-medium text-gray-900 text-sm">{projectName}</h1>
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <Calendar className="w-3 h-3" />
              {today}
            </div>
          </div>
        </div>
        
        <div className="relative">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setShowActions(!showActions)}
          >
            <MoreHorizontal className="w-5 h-5 text-gray-500" />
          </Button>
          
          {/* Actions Menu */}
          {showActions && (
            <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-[140px]">
              <button
                onClick={() => {
                  handleCopyChat();
                  setShowActions(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                <Copy className="w-4 h-4" />
                Copy Chat
              </button>
              <button
                onClick={() => {
                  handleShareChat();
                  setShowActions(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                <Share2 className="w-4 h-4" />
                Share Chat
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Chat Content */}
      <div className="flex-1 overflow-y-auto bg-gray-50/50">
        {!hasMessages ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-full px-4 py-8"
          >
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-4">
              <Bot className="w-7 h-7 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900 mb-1 text-center">
              What would you like to analyze?
            </h2>
            <p className="text-gray-500 text-center mb-6 text-sm">
              Ask questions or request analysis
            </p>

            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTED_PROMPTS.map((prompt, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => setInputValue(prompt)}
                  className={cn(
                    'px-3 py-2 bg-white border border-gray-200 rounded-lg',
                    'text-sm text-gray-700'
                  )}
                >
                  {prompt}
                </motion.button>
              ))}
            </div>
          </motion.div>
        ) : (
          <div className="px-3 py-4">
            {/* Smart Context Toggle */}
            <SmartContextToggle
              sessionToken={sessionToken}
              onToggle={handleSmartContextToggle}
            />

            {messages.map((message, index) => (
              <ChatMessage key={message.id} message={message} index={index} />
            ))}

            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-2 mb-4"
              >
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-3 h-3 text-white" />
                </div>
                <div className="flex items-center gap-1 px-2 py-1.5 bg-white border border-gray-200 rounded-xl">
                  <span className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200">
        <ChatInputV2
          value={inputValue}
          onChange={setInputValue}
          onSend={sendMessage}
          attachments={attachments}
          onRemoveAttachment={removeAttachment}
          isLoading={isLoading}
          placeholder="Type a message..."
        />
      </div>

      {/* Click outside to close menu */}
      {showActions && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => setShowActions(false)}
        />
      )}
    </div>
  );
}
