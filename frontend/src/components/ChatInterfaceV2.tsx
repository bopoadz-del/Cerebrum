import { useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles, Plus, Calendar } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInputV2 } from './ChatInputV2';
import { SmartContextToggle } from './SmartContextToggle';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface ChatInterfaceV2Props {
  projectName?: string;
  chatTitle?: string;
  onNewChat?: () => void;
  sessionToken?: string;
}

const SUGGESTED_PROMPTS = [
  'Analyze the Q4 financial data',
  'Generate a project timeline',
  'Review the CAD drawings',
  'Transcribe the meeting recording',
];

export function ChatInterfaceV2({ projectName, chatTitle, onNewChat, sessionToken }: ChatInterfaceV2Props) {
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
    clearMessages,
  } = useChat();

  const [, setSmartContextEnabled] = useState(false);
  const hasMessages = messages.length > 0;
  const isProjectSelected = projectName && projectName !== 'Select a project';

  // Handler for file attachment
  const handleAttachFile = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files) {
        Array.from(files).forEach(file => addAttachment(file));
      }
    };
    input.click();
  };

  // Handler for camera (placeholder - would open camera modal)
  const handleOpenCamera = () => {
    alert('Camera feature: Would open camera capture modal');
  };

  // Handler for voice input (placeholder - would start voice recording)
  const handleOpenMic = () => {
    alert('Voice input: Would start voice recording');
  };

  // Handler for internet search (placeholder)
  const handleInternetSearch = () => {
    setInputValue('/search ' + inputValue);
  };

  // Handler for new chat button
  const handleNewChatClick = () => {
    clearMessages();
    onNewChat?.();
  };

  // Get current date for header
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  const handleSmartContextToggle = (enabled: boolean) => {
    setSmartContextEnabled(enabled);
    console.log('Smart Context:', enabled ? 'ENABLED' : 'DISABLED');
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <header className="h-14 border-b border-gray-200 flex items-center justify-between px-4 bg-white">
        <div className="flex items-center gap-3">
          {isProjectSelected ? (
            <>
              <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-indigo-600" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="font-medium text-gray-900 text-sm">{projectName}</h1>
                  {chatTitle && (
                    <span className="text-xs text-gray-400">/</span>
                  )}
                  {chatTitle && (
                    <span className="text-sm text-gray-600">{chatTitle}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Calendar className="w-3 h-3" />
                  {today}
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-500">Select a project to start chatting</p>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {isProjectSelected && (
            <>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="text-xs text-gray-500">Online</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleNewChatClick}
                className="h-8 text-indigo-600 hover:bg-indigo-50"
              >
                <Plus className="w-4 h-4 mr-1" />
                New Chat
              </Button>
            </>
          )}
        </div>
      </header>

      {/* Chat Content */}
      <div className="flex-1 overflow-y-auto bg-gray-50/50">
        {!hasMessages ? (
          /* Welcome State */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col items-center justify-center h-full px-6 py-12"
          >
            {/* Logo */}
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-5 shadow-lg">
              <Bot className="w-8 h-8 text-white" />
            </div>

            {/* Title */}
            <h2 className="text-xl font-semibold text-gray-900 mb-2 text-center">
              {isProjectSelected
                ? 'What would you like to analyze?'
                : 'Welcome to Reasoner'}
            </h2>
            <p className="text-gray-500 text-center mb-8 max-w-md text-sm">
              {isProjectSelected
                ? 'Ask questions or request analysis. I have access to all project files.'
                : 'Select a project from the sidebar to start analyzing your files.'}
            </p>

            {/* Suggested Prompts */}
            {isProjectSelected && (
              <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                {SUGGESTED_PROMPTS.map((prompt, index) => (
                  <motion.button
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => setInputValue(prompt)}
                    className={cn(
                      'px-4 py-2 bg-white border border-gray-200 rounded-lg',
                      'text-sm text-gray-700 transition-all duration-200',
                      'hover:border-indigo-300 hover:shadow-sm'
                    )}
                  >
                    {prompt}
                  </motion.button>
                ))}
              </div>
            )}
          </motion.div>
        ) : (
          /* Chat Messages */
          <div className="max-w-2xl mx-auto px-4 py-6">
            {/* Smart Context Toggle */}
            {isProjectSelected && (
              <SmartContextToggle
                sessionToken={sessionToken}
                onToggle={handleSmartContextToggle}
              />
            )}

            {messages.map((message, index) => (
              <ChatMessage key={message.id} message={message} index={index} />
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-3 mb-4"
              >
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-200 rounded-2xl">
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="bg-white">
        <div className="max-w-2xl mx-auto">
          <ChatInputV2
            value={inputValue}
            onChange={setInputValue}
            onSend={sendMessage}
            onAttachFile={handleAttachFile}
            onOpenCamera={handleOpenCamera}
            onOpenMic={handleOpenMic}
            onInternetSearch={handleInternetSearch}
            attachments={attachments}
            onRemoveAttachment={removeAttachment}
            isLoading={isLoading}
            placeholder={isProjectSelected ? 'Type /help for commands or ask anything...' : 'Select a project first'}
          />
        </div>
      </div>
    </div>
  );
}
