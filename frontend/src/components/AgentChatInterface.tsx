import { useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles, Plus, Layers, Brain } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInputV2 } from './ChatInputV2';
import { SmartContextToggle } from './SmartContextToggle';
import { useAgentChat } from '@/hooks/useAgentChat';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface AgentChatInterfaceProps {
  projectName?: string;
  chatTitle?: string;
  onNewChat?: () => void;
  sessionToken?: string;
}

const SUGGESTED_PROMPTS = [
  'Calculate drywall costs for Building A',
  'Search for previous foundation discussions',
  'What tools are available in the economics layer?',
  'Analyze the Q4 safety reports',
  'Navigate to the VDC layer',
];

export function AgentChatInterface({ projectName, chatTitle, onNewChat, sessionToken }: AgentChatInterfaceProps) {
  const {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    isUploading,
    attachments,
    messagesEndRef,
    currentLayer,
    sendMessage,
    addAttachment,
    removeAttachment,
    clearMessages,
  } = useAgentChat({ sessionId: sessionToken });

  const [, setSmartContextEnabled] = useState(false);
  const hasMessages = messages.length > 0;
  const isProjectSelected = projectName && projectName !== 'Select a project';

  const handleAttachFile = (file: File) => {
    addAttachment(file);
  };

  const handleOpenCamera = () => {
    alert('Camera feature: Would open camera capture modal');
  };

  const handleOpenMic = () => {
    alert('Voice input: Would start voice recording');
  };

  const handleInternetSearch = () => {
    setInputValue('/agent search ' + inputValue);
  };

  const handleNewChatClick = () => {
    clearMessages();
    onNewChat?.();
  };

  const handleSmartContextToggle = (enabled: boolean) => {
    setSmartContextEnabled(enabled);
    console.log('Smart Context:', enabled ? 'ENABLED' : 'DISABLED');
  };

  const handlePromptClick = (prompt: string) => {
    setInputValue(prompt);
  };

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <header className="h-14 border-b border-gray-200 flex items-center justify-between px-4 bg-white">
        <div className="flex items-center gap-3">
          {isProjectSelected ? (
            <>
              <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                <Brain className="w-4 h-4 text-indigo-600" />
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
                  <Badge variant="outline" className="text-xs ml-2 bg-indigo-50 text-indigo-700 border-indigo-200">
                    <Layers className="w-3 h-3 mr-1" />
                    {currentLayer}
                  </Badge>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                <Bot className="w-4 h-4 text-indigo-600" />
              </div>
              <div>
                <h1 className="font-medium text-gray-900 text-sm">Agent Chat</h1>
                <p className="text-xs text-gray-500">Connected to Cerebrum Agent</p>
              </div>
              <Badge variant="outline" className="text-xs ml-2 bg-indigo-50 text-indigo-700 border-indigo-200">
                <Layers className="w-3 h-3 mr-1" />
                {currentLayer}
              </Badge>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <SmartContextToggle onToggle={handleSmartContextToggle} />
          
          <Button
            variant="ghost"
            size="sm"
            className="text-gray-600 hover:text-gray-900"
            onClick={handleNewChatClick}
          >
            <Plus className="w-4 h-4 mr-1.5" />
            New Chat
          </Button>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        {!hasMessages ? (
          // Empty State
          <div className="flex flex-col items-center justify-center h-full px-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center max-w-lg"
            >
              {/* Logo */}
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-6 shadow-lg">
                <Brain className="w-8 h-8 text-white" />
              </div>

              {/* Welcome Text */}
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                Welcome to Cerebrum Agent
              </h2>
              <p className="text-gray-600 mb-8">
                Your autonomous construction intelligence assistant. I can analyze BIM models, 
                calculate costs, search your history, and even improve my own code.
              </p>

              {/* Suggested Prompts */}
              <div className="flex flex-wrap justify-center gap-2">
                {SUGGESTED_PROMPTS.map((prompt, index) => (
                  <motion.button
                    key={index}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.05 }}
                    onClick={() => handlePromptClick(prompt)}
                    className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-700 hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
                  >
                    {prompt}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          </div>
        ) : (
          // Messages List
          <div className="py-4 px-4 space-y-4">
            {messages.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <ChatMessage
                  message={message}
                  isLast={index === messages.length - 1}
                />
              </motion.div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className={cn(
        "border-t bg-white p-4",
        !hasMessages && "border-t-0"
      )}>
        {!hasMessages && (
          <div className="text-center text-sm text-gray-500 mb-4">
            {today}
          </div>
        )}
        
        <ChatInputV2
          value={inputValue}
          onChange={setInputValue}
          onSend={sendMessage}
          onAttach={handleAttachFile}
          onCamera={handleOpenCamera}
          onMic={handleOpenMic}
          onInternet={handleInternetSearch}
          isLoading={isLoading}
          isUploading={isUploading}
          attachments={attachments}
          onRemoveAttachment={removeAttachment}
          placeholder="Ask the agent anything... (try: Calculate drywall costs, /agent help)"
        />
      </div>
    </div>
  );
}
