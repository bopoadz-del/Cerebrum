import { useState, useCallback, useRef } from 'react';
import type { Message, Attachment, ChatMode, CodeExecutionResult, WebSearchResult } from '@/types';

interface UseChatOptions {
  apiUrl?: string;
  initialMessages?: Message[];
  onError?: (error: Error) => void;
}

interface UseChatReturn {
  messages: Message[];
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  attachments: Attachment[];
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
  sendMessage: (content: string, attachments?: Attachment[]) => Promise<void>;
  addAttachment: (file: File) => void;
  removeAttachment: (id: string) => void;
  clearMessages: () => void;
  executeCode: (code: string) => Promise<CodeExecutionResult | null>;
  searchWeb: (query: string) => Promise<WebSearchResult | null>;
  analyzeImage: (file: File) => Promise<string | null>;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { apiUrl = '/api/v1', initialMessages = [], onError } = options;
  
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [mode, setMode] = useState<ChatMode>('standard');
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string, messageAttachments?: Attachment[]) => {
    if (!content.trim() && (!messageAttachments || messageAttachments.length === 0)) return;
    
    setIsLoading(true);
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      attachments: messageAttachments,
      timestamp: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    try {
      abortControllerRef.current = new AbortController();
      
      const response = await fetch(`${apiUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'cerebrum-default',
          messages: [
            ...messages.map(m => ({ role: m.role, content: m.content })),
            { role: 'user', content },
          ],
        }),
        signal: abortControllerRef.current.signal,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.choices[0].message.content,
        timestamp: new Date().toISOString(),
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        onError?.(error);
        
        // Add error message
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [messages, apiUrl, onError]);

  const addAttachment = useCallback((file: File) => {
    const newAttachment: Attachment = {
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      type: file.type,
      size: file.size,
      status: 'uploading',
      progress: 0,
    };
    setAttachments(prev => [...prev, newAttachment]);
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setAttachments(prev => prev.filter(att => att.id !== id));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const executeCode = useCallback(async (code: string): Promise<CodeExecutionResult | null> => {
    try {
      const response = await fetch(`${apiUrl}/chat/execute-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      
      if (!response.ok) throw new Error('Code execution failed');
      return await response.json();
    } catch (error) {
      onError?.(error as Error);
      return null;
    }
  }, [apiUrl, onError]);

  const searchWeb = useCallback(async (query: string): Promise<WebSearchResult | null> => {
    try {
      const response = await fetch(`${apiUrl}/chat/web-search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      
      if (!response.ok) throw new Error('Web search failed');
      return await response.json();
    } catch (error) {
      onError?.(error as Error);
      return null;
    }
  }, [apiUrl, onError]);

  const analyzeImage = useCallback(async (file: File): Promise<string | null> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${apiUrl}/chat/analyze-image`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) throw new Error('Image analysis failed');
      const data = await response.json();
      return data.analysis;
    } catch (error) {
      onError?.(error as Error);
      return null;
    }
  }, [apiUrl, onError]);

  return {
    messages,
    input,
    setInput,
    isLoading,
    attachments,
    mode,
    setMode,
    sendMessage,
    addAttachment,
    removeAttachment,
    clearMessages,
    executeCode,
    searchWeb,
    analyzeImage,
  };
}
