import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  Sparkles, 
  FileText, 
  Mic, 
  Calendar, 
  TrendingUp,
  Globe,
  Code2,
  Image as ImageIcon,
  Search,
  Zap,
  MessageSquare,
  X
} from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/lib/utils';
import { ImageAnalysis } from './ImageAnalysis';

const SUGGESTED_PROMPTS = [
  { icon: FileText, text: 'Analyze this PDF document' },
  { icon: Mic, text: 'Transcribe and summarize audio' },
  { icon: Calendar, text: 'Check schedule for conflicts' },
  { icon: TrendingUp, text: 'Forecast next quarter trends' },
];

const CAPABILITY_CARDS = [
  { 
    icon: Search, 
    title: 'Web Search',
    description: 'Search the web for real-time information',
    color: 'bg-blue-500',
    action: 'web_search'
  },
  { 
    icon: Code2, 
    title: 'Code Execution',
    description: 'Write and execute code in multiple languages',
    color: 'bg-purple-500',
    action: 'code'
  },
  { 
    icon: ImageIcon, 
    title: 'Image Analysis',
    description: 'Upload and analyze images with AI',
    color: 'bg-emerald-500',
    action: 'image'
  },
  { 
    icon: Zap, 
    title: 'Smart Context',
    description: 'Get intelligent suggestions and insights',
    color: 'bg-amber-500',
    action: 'smart'
  },
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
    // New features
    isWebSearchEnabled,
    isCodeModeEnabled,
    imageUploads,
    toggleWebSearch,
    toggleCodeMode,
    addImageUpload,
    removeImageUpload,
    analyzeImage,
  } = useChat();

  const hasMessages = messages.length > 0;
  const [showCapabilities, setShowCapabilities] = useState(false);
  const [activePanel, setActivePanel] = useState<string | null>(null);

  const handleCapabilityClick = (action: string) => {
    switch (action) {
      case 'web_search':
        toggleWebSearch();
        setInputValue(prev => prev + ' ');
        break;
      case 'code':
        toggleCodeMode();
        setInputValue('```python\n\n```');
        break;
      case 'image':
        setActivePanel('image');
        break;
      case 'smart':
        setInputValue('Help me with: ');
        break;
    }
    setShowCapabilities(false);
  };

  const handleSend = () => {
    if (isWebSearchEnabled || isCodeModeEnabled) {
      // Use enhanced send for special modes
      sendMessage();
    } else {
      sendMessage();
    }
  };

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
            <p className="text-xs text-gray-500">Powered by Cerebrum</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Feature Toggles */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleWebSearch}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
                isWebSearchEnabled
                  ? 'bg-blue-100 text-blue-700 border border-blue-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
              title="Toggle web search"
            >
              <Globe className="w-4 h-4" />
              <span className="hidden sm:inline">Web</span>
              {isWebSearchEnabled && (
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              )}
            </button>

            <button
              onClick={toggleCodeMode}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
                isCodeModeEnabled
                  ? 'bg-purple-100 text-purple-700 border border-purple-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
              title="Toggle code mode"
            >
              <Code2 className="w-4 h-4" />
              <span className="hidden sm:inline">Code</span>
              {isCodeModeEnabled && (
                <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
              )}
            </button>

            <button
              onClick={() => setActivePanel(activePanel === 'image' ? null : 'image')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
                activePanel === 'image'
                  ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
              title="Image analysis"
            >
              <ImageIcon className="w-4 h-4" />
              <span className="hidden sm:inline">Image</span>
            </button>
          </div>

          {/* Status Indicator */}
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-