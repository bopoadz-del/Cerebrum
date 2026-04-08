import { useState, useRef, useEffect } from 'react';
import { Bot, Trash2, Download, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatInput } from './ChatInput';
import { ChatMessage } from './ChatMessage';
import { FileUpload } from './FileUpload';
import { WebSearchIndicator } from './WebSearchIndicator';
import type { Message, Attachment } from '@/types';

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (content: string, attachments?: Attachment[]) => void;
  onFileUpload?: (file: File) => void;
  onClearChat?: () => void;
  onExportChat?: () => void;
  onRegenerate?: (messageIndex: number) => void;
  onFeedback?: (messageIndex: number, type: 'up' | 'down') => void;
  isLoading?: boolean;
  className?: string;
  enableFileUpload?: boolean;
  enableWebSearch?: boolean;
  enableCodeExecution?: boolean;

}

export function ChatInterface({
  messages,
  onSendMessage,
  onFileUpload,
  onClearChat,
  onExportChat,
  onRegenerate,
  onFeedback,
  isLoading = false,
  className,
  enableFileUpload = true,
  enableWebSearch = true,
  enableCodeExecution = true,

}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isWebSearchEnabled, setIsWebSearchEnabled] = useState(false);
  const [isCodeModeEnabled, setIsCodeModeEnabled] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() && attachments.length === 0) return;
    
    onSendMessage(input, attachments.length > 0 ? attachments : undefined);
    setInput('');
    setAttachments([]);
  };

  const handleAttach = (file: File) => {
    const newAttachment: Attachment = {
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      type: file.type,
      size: file.size,
      status: 'uploading',
      progress: 0,
    };
    setAttachments(prev => [...prev, newAttachment]);
    
    if (onFileUpload) {
      onFileUpload(file);
    }
  };

  const handleClearChat = () => {
    if (onClearChat) {
      onClearChat();
    }
    setAttachments([]);
    setInput('');
  };

  const handleExportChat = () => {
    if (onExportChat) {
      onExportChat();
      return;
    }
    // Default export implementation
    const exportData = {
      exportedAt: new Date().toISOString(),
      messages: messages,
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cerebrum-chat-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleRegenerate = (index: number) => {
    if (onRegenerate) {
      onRegenerate(index);
    }
  };

  const handleFeedback = (index: number, type: 'up' | 'down') => {
    if (onFeedback) {
      onFeedback(index, type);
    }
    // Store feedback in localStorage for now
    const feedbackKey = `feedback-${messages[index]?.id || index}`;
    localStorage.setItem(feedbackKey, type);
  };

  const handleRemoveAttachment = (id: string) => {
    setAttachments(prev => prev.filter(att => att.id !== id));
  };

  return (
    <div className={cn('flex flex-col h-full bg-white', className)}>
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">Cerebrum AI</h1>
            <p className="text-xs text-gray-500">Construction Intelligence</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {onExportChat && (
            <Button 
              variant="ghost" 
              size="icon" 
              className="text-gray-500"
              onClick={handleExportChat}
              title="Export chat"
            >
              <Download className="w-5 h-5" />
            </Button>
          )}
          {onClearChat && (
            <Button 
              variant="ghost" 
              size="icon" 
              className="text-gray-500"
              onClick={handleClearChat}
              title="Clear chat"
            >
              <Trash2 className="w-5 h-5" />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="text-gray-500">
            <Settings className="w-5 h-5" />
          </Button>
        </div>
      </header>

      {/* Messages Area */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 px-4 py-4">
        <div className="space-y-4 max-w-3xl mx-auto">
          {messages.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              Start a conversation...
            </div>
          )}

          {messages.map((message, index) => (
            <ChatMessage
              key={message.id || index}
              message={message}
              isLoading={isLoading && index === messages.length - 1 && message.role === 'assistant'}
              onRegenerate={() => handleRegenerate(index)}
              onFeedback={(type) => handleFeedback(index, type)}
            />
          ))}
          
          {isWebSearchEnabled && (
            <WebSearchIndicator query={input} isSearching={isLoading} />
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t border-gray-200">
        {enableFileUpload && (
          <FileUpload
            attachments={attachments}
            onRemove={handleRemoveAttachment}
          />
        )}
        
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          onAttach={enableFileUpload ? handleAttach : undefined}
          attachments={attachments}
          onRemoveAttachment={handleRemoveAttachment}
          isLoading={isLoading}
          placeholder="Type your message..."
          onWebSearchToggle={enableWebSearch ? () => setIsWebSearchEnabled(!isWebSearchEnabled) : undefined}
          isWebSearchEnabled={isWebSearchEnabled}
          onCodeModeToggle={enableCodeExecution ? () => setIsCodeModeEnabled(!isCodeModeEnabled) : undefined}
          isCodeModeEnabled={isCodeModeEnabled}
        />
      </div>
    </div>
  );
}
