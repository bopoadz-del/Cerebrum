import { useState, useCallback, useRef } from 'react';
import type { Message, Attachment, ChatMode, CodeExecutionResult, WebSearchResult } from '@/types';
import { processDocument, processAudio } from '@/lib/fileProcessing';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_PREFIX = API_BASE_URL.endsWith('/api/v1') ? API_BASE_URL : `${API_BASE_URL}/api/v1`;

// Extended attachment type that includes the actual File object
interface FileAttachment extends Attachment {
  file?: File;
  extractedText?: string;
  file_key?: string; // Server-side file identifier
}

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
  isUploading: boolean;
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
  const { apiUrl = API_PREFIX, initialMessages = [], onError } = options;
  
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading] = useState(false);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [mode, setMode] = useState<ChatMode>('standard');
  
  const abortControllerRef = useRef<AbortController | null>(null);

  // Process a single file with OCR/transcription
  const processFile = async (attachment: FileAttachment): Promise<{ text: string; metadata: any } | null> => {
    if (!attachment.file) return null;

    const file = attachment.file;
    const isAudio = file.type.startsWith('audio/') || file.type.startsWith('video/');
    
    try {
      let result;
      if (isAudio) {
        result = await processAudio(file, (stage, percentage) => {
          if (stage === 'uploading' && percentage !== undefined) {
            setAttachments(prev => prev.map(att => 
              att.id === attachment.id 
                ? { ...att, progress: percentage, status: 'uploading' }
                : att
            ));
          }
        });
      } else {
        result = await processDocument(file, (stage, percentage) => {
          if (stage === 'uploading' && percentage !== undefined) {
            setAttachments(prev => prev.map(att => 
              att.id === attachment.id 
                ? { ...att, progress: percentage, status: 'uploading' }
                : att
            ));
          }
        });
      }

      if (result.success) {
        setAttachments(prev => prev.map(att => 
          att.id === attachment.id 
            ? { ...att, status: 'complete', progress: 100, extractedText: result.text }
            : att
        ));
        return { text: result.text, metadata: result.metadata };
      } else {
        setAttachments(prev => prev.map(att => 
          att.id === attachment.id 
            ? { ...att, status: 'error', error: result.error }
            : att
        ));
        return null;
      }
    } catch (error) {
      setAttachments(prev => prev.map(att => 
        att.id === attachment.id 
          ? { ...att, status: 'error', error: 'Processing failed' }
          : att
      ));
      return null;
    }
  };

  // Upload file to get file_key (using public endpoint - no auth required)
  const uploadFile = async (attachment: FileAttachment): Promise<string | null> => {
    if (!attachment.file) return null;

    console.log('[useChat] Uploading file:', attachment.name);

    const formData = new FormData();
    formData.append('file', attachment.file);

    try {
      const response = await fetch(`${API_PREFIX}/documents/upload/public`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        console.error('[useChat] Upload failed:', response.status);
        return null;
      }

      const data = await response.json();
      console.log('[useChat] Upload success, file_id:', data.file_id);
      return data.file_id;
    } catch (error) {
      console.error('[useChat] Upload error:', error);
      return null;
    }
  };

  const sendMessage = useCallback(async (content: string, messageAttachments?: Attachment[]) => {
    if (!content.trim() && (!messageAttachments || messageAttachments.length === 0)) return;
    
    setIsLoading(true);
    
    // Process all attachments - upload files and extract text
    const processedAttachments: FileAttachment[] = [];
    const extractedTexts: string[] = [];
    const fileKeys: string[] = [];
    
    if (messageAttachments && messageAttachments.length > 0) {
      for (const att of messageAttachments) {
        const fileAtt = att as FileAttachment;
        if (fileAtt.file) {
          // Upload file to get file_key
          console.log('[useChat] Processing attachment:', fileAtt.name);
          const fileKey = await uploadFile(fileAtt);
          
          if (fileKey) {
            fileKeys.push(fileKey);
            console.log('[useChat] Got file_key:', fileKey);
          }
          
          // Also extract text via OCR/transcription
          const result = await processFile(fileAtt);
          if (result) {
            processedAttachments.push({ ...fileAtt, extractedText: result.text, file_key: fileKey || undefined });
            extractedTexts.push(`[File: ${fileAtt.name}]
${result.text}`);
          } else {
            processedAttachments.push({ ...fileAtt, file_key: fileKey || undefined });
          }
        }
      }
    }
    
    // Build the full message content including extracted text from files
    let fullContent = content;
    if (extractedTexts.length > 0) {
      fullContent = content + '\n\n---\n\n' + extractedTexts.join('\n\n---\n\n');
    }
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      attachments: processedAttachments,
      timestamp: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    console.log('[useChat] Sending message with', fileKeys.length, 'file keys');
    
    try {
      abortControllerRef.current = new AbortController();
      
      const requestBody: any = {
        model: 'cerebrum-default',
        messages: [
          ...messages.map(m => ({ role: m.role, content: m.content })),
          { role: 'user', content: fullContent },
        ],
      };
      
      // Include file_keys if we have any
      if (fileKeys.length > 0) {
        requestBody.file_keys = fileKeys;
        console.log('[useChat] Including file_keys:', fileKeys);
      }
      
      // Include extracted_texts if we have any (helps backend when disk not shared)
      const extractedTextsList = processedAttachments
        .map(att => att.extractedText)
        .filter((text): text is string => !!text);
      if (extractedTextsList.length > 0) {
        requestBody.extracted_texts = extractedTextsList;
        console.log('[useChat] Including extracted_texts:', extractedTextsList.length);
      }
      
      const response = await fetch(`${apiUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
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
    const newAttachment: FileAttachment = {
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      type: file.type,
      size: file.size,
      status: 'pending' as const,
      progress: 0,
      file: file, // Store the actual File object
    };
    setAttachments(prev => [...prev, newAttachment]);
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setAttachments(prev => prev.filter(att => att.id !== id));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setAttachments([]);
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
    isUploading,
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
