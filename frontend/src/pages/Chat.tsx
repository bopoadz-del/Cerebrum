import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Paperclip,
  MoreVertical,
  Phone,
  Video,
  Search,
  Smile,
  Bot,
  User,
  Clock,
  Check,
  CheckCheck,
  Sparkles,
  FileText,
  Image,
  Mic,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  status?: 'sent' | 'delivered' | 'read';
  attachments?: Array<{
    name: string;
    type: string;
    size?: string;
  }>;
}

interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  unread: number;
  type: 'ai' | 'user';
}

const mockConversations: Conversation[] = [
  {
    id: '1',
    title: 'Cerebrum AI Assistant',
    lastMessage: 'I can help you analyze the BIM model data.',
    timestamp: new Date(Date.now() - 1000 * 60 * 5),
    unread: 0,
    type: 'ai',
  },
  {
    id: '2',
    title: 'Project Team',
    lastMessage: 'The cost estimates are ready for review.',
    timestamp: new Date(Date.now() - 1000 * 60 * 30),
    unread: 3,
    type: 'user',
  },
  {
    id: '3',
    title: 'Safety Analysis Bot',
    lastMessage: '3 potential hazards detected in the latest scan.',
    timestamp: new Date(Date.now() - 1000 * 60 * 60),
    unread: 1,
    type: 'ai',
  },
];

const mockMessages: Message[] = [
  {
    id: '1',
    content: 'Hello! How can I help you today?',
    sender: 'ai',
    timestamp: new Date(Date.now() - 1000 * 60 * 10),
  },
  {
    id: '2',
    content: 'I need help analyzing the latest BIM model for structural issues.',
    sender: 'user',
    timestamp: new Date(Date.now() - 1000 * 60 * 8),
    status: 'read',
  },
  {
    id: '3',
    content: 'I can help you with that! I\'ll analyze the model for potential structural issues, clash detection, and code compliance.',
    sender: 'ai',
    timestamp: new Date(Date.now() - 1000 * 60 * 6),
  },
  {
    id: '4',
    content: 'Please upload the BIM file or provide the model ID.',
    sender: 'ai',
    timestamp: new Date(Date.now() - 1000 * 60 * 5),
  },
];

const Chat: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>(mockConversations);
  const [activeConversation, setActiveConversation] = useState<Conversation>(mockConversations[0]);
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = () => {
    if (!inputMessage.trim()) return;

    const newMessage: Message = {
      id: `${messages.length + 1}`,
      content: inputMessage,
      sender: 'user',
      timestamp: new Date(),
      status: 'sent',
    };

    setMessages([...messages, newMessage]);
    setInputMessage('');

    // Simulate AI response
    if (activeConversation.type === 'ai') {
      setIsTyping(true);
      setTimeout(() => {
        const aiResponse: Message = {
          id: `${messages.length + 2}`,
          content: 'I understand. Let me process that information and get back to you with a detailed analysis.',
          sender: 'ai',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, aiResponse]);
        setIsTyping(false);
      }, 2000);
    }
  };

  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Sidebar - Conversations */}
      <div className="w-80 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col">
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <Breadcrumb />
          <div className="flex items-center justify-between mt-2">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Messages</h1>
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <MoreVertical size={18} className="text-gray-500" />
            </button>
          </div>
          <div className="relative mt-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              placeholder="Search conversations..."
              className="w-full pl-9 pr-4 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => setActiveConversation(conv)}
              className={cn(
                'w-full flex items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors',
                activeConversation.id === conv.id && 'bg-blue-50 dark:bg-blue-900/20'
              )}
            >
              <div className="relative">
                <div
                  className={cn(
                    'w-10 h-10 rounded-full flex items-center justify-center',
                    conv.type === 'ai'
                      ? 'bg-purple-100 dark:bg-purple-900/20'
                      : 'bg-blue-100 dark:bg-blue-900/20'
                  )}
                >
                  {conv.type === 'ai' ? (
                    <Bot size={20} className="text-purple-600 dark:text-purple-400" />
                  ) : (
                    <User size={20} className="text-blue-600 dark:text-blue-400" />
                  )}
                </div>
                {conv.type === 'ai' && (
                  <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-purple-500 rounded-full flex items-center justify-center">
                    <Sparkles size={8} className="text-white" />
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0 text-left">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-gray-900 dark:text-white truncate">
                    {conv.title}
                  </p>
                  <span className="text-xs text-gray-400">
                    {formatTime(conv.timestamp)}
                  </span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                  {conv.lastMessage}
                </p>
              </div>
              {conv.unread > 0 && (
                <span className="w-5 h-5 bg-blue-500 text-white text-xs rounded-full flex items-center justify-center">
                  {conv.unread}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-950">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center',
                activeConversation.type === 'ai'
                  ? 'bg-purple-100 dark:bg-purple-900/20'
                  : 'bg-blue-100 dark:bg-blue-900/20'
              )}
            >
              {activeConversation.type === 'ai' ? (
                <Bot size={20} className="text-purple-600 dark:text-purple-400" />
              ) : (
                <User size={20} className="text-blue-600 dark:text-blue-400" />
              )}
            </div>
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-white">
                {activeConversation.title}
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {activeConversation.type === 'ai' ? 'AI Assistant' : 'Online'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <Phone size={18} className="text-gray-500" />
            </button>
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <Video size={18} className="text-gray-500" />
            </button>
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <MoreVertical size={18} className="text-gray-500" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'flex',
                message.sender === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              <div
                className={cn(
                  'max-w-[70%] rounded-2xl px-4 py-2',
                  message.sender === 'user'
                    ? 'bg-blue-600 text-white rounded-br-md'
                    : 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-bl-md'
                )}
              >
                <p
                  className={cn(
                    'text-sm',
                    message.sender === 'user'
                      ? 'text-white'
                      : 'text-gray-900 dark:text-white'
                  )}
                >
                  {message.content}
                </p>
                <div
                  className={cn(
                    'flex items-center justify-end gap-1 mt-1',
                    message.sender === 'user' ? 'text-blue-200' : 'text-gray-400'
                  )}
                >
                  <span className="text-xs">{formatTime(message.timestamp)}</span>
                  {message.sender === 'user' && message.status && (
                    <>
                      {message.status === 'read' ? (
                        <CheckCheck size={12} />
                      ) : (
                        <Check size={12} />
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <span
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0.1s' }}
                  />
                  <span
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: '0.2s' }}
                  />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <Paperclip size={20} className="text-gray-500" />
            </button>
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <Image size={20} className="text-gray-500" />
            </button>
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Type a message..."
                className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
              <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded">
                <Smile size={18} className="text-gray-400" />
              </button>
            </div>
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <Mic size={20} className="text-gray-500" />
            </button>
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim()}
              className="p-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg"
            >
              <Send size={20} className="text-white" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
