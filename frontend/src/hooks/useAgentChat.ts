import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Message, Attachment, ReasoningStep } from '@/types';
import { STORAGE_KEYS } from '@/context/AuthContext';
import { processAndIndexFile, validateFileOnSelect, type FileValidationResult } from '@/lib/fileProcessing';

// API Configuration - fallback to production URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const getApiUrl = () => {
  const url = API_BASE_URL.replace(/\/?$/, '');
  return url.endsWith('/api/v1') ? url : `${url}/api/v1`;
};

interface UseAgentChatOptions {
  initialMessages?: Message[];
  apiBaseUrl?: string;
  sessionId?: string;
}

interface AgentResponse {
  success: boolean;
  action: string;
  layer: string;
  data: Record<string, unknown>;
  message: string;
  execution_time_ms?: number;
  related_conversations?: string[];
  suggested_next_actions?: string[];
  timestamp: string;
  reasoning?: any;
}

interface MemoryResult {
  source: string;
  score: number;
  content?: string;
}

interface AgentLayer {
  name: string;
  capabilities: string[];
}

interface PrioritizedFile {
  file: string;
  total_issues: number;
}

// Get auth token from localStorage
const getAuthToken = () => localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN) || '';

export function useAgentChat(options: UseAgentChatOptions = {}) {
  const { 
    initialMessages = [], 
    sessionId = uuidv4()
  } = options;
  const apiBaseUrl = getApiUrl(); // Always use full API URL
  
  const [isUploading, setIsUploading] = useState(false);
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'What would you like to know?',
      timestamp: new Date().toISOString(),
    },
    ...initialMessages,
  ]);
  
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [currentLayer, setCurrentLayer] = useState<string>('coding');
  
  // Persist session ID to localStorage for cross-page context
  useEffect(() => {
    localStorage.setItem('cerebrum_chat_session_id', sessionId);
  }, [sessionId]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Check agent status on mount
  useEffect(() => {
    const checkAgentStatus = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/agent/v2/status/enhanced`);
        if (response.ok) {
          const data = await response.json();
          setCurrentLayer(data.current_layer || 'coding');
        }
      } catch (error) {
        console.log('Agent status check failed:', error);
      }
    };
    checkAgentStatus();
  }, [apiBaseUrl]);

  // Execute task through the agent
  const executeAgentTask = async (task: string, context?: Record<string, unknown>): Promise<AgentResponse | null> => {
    try {
      const response = await fetch(`${apiBaseUrl}/agent/v2/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '',
        },
        body: JSON.stringify({
          task,
          context: {
            ...context,
            session_id: sessionId,
            current_layer: currentLayer,
          },
          use_memory: true,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Agent error: ${response.status}`);
      }

      const result: AgentResponse = await response.json();
      
      // Update current layer if changed
      if (result.layer && result.layer !== currentLayer) {
        setCurrentLayer(result.layer);
      }
      
      return result;
    } catch (error) {
      console.error('Agent execution failed:', error);
      return null;
    }
  };

  // Search agent memory
  const searchMemory = async (query: string): Promise<string> => {
    try {
      const response = await fetch(`${apiBaseUrl}/agent/v2/memory/search?q=${encodeURIComponent(query)}&limit=5`, {
        headers: {
          'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '',
        },
      });

      if (!response.ok) {
        throw new Error('Memory search failed');
      }

      const data = await response.json();
      
      if (!data.results || data.results.length === 0) {
        return `No memories found for "${query}"`;
      }

      const formatted = data.results.map((r: MemoryResult, i: number) => {
        const score = Math.round(r.score * 10) / 10;
        return `${i + 1}. **${r.source}** (relevance: ${score})
   ${r.content?.substring(0, 150)}...`;
      }).join('\n\n');

      return `🔍 **Memory Search: "${query}"**\n\n${formatted}`;
    } catch (error) {
      return `❌ Memory search failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  };

  // Get agent layers
  const getAgentLayers = async (): Promise<string> => {
    try {
      const response = await fetch(`${apiBaseUrl}/agent/v2/layer/list`, {
        headers: {
          'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to get layers');
      }

      const data = await response.json();
      
      const layers = data.layers.map((l: AgentLayer) => {
        const caps = l.capabilities.slice(0, 3).join(', ');
        return `• **${l.name}** - ${caps}${l.capabilities.length > 3 ? '...' : ''}`;
      }).join('\n');

      return `🏗️ **Available Agent Layers**\n\n${layers}\n\n_Current layer: **${currentLayer}**_`;
    } catch (error) {
      return `❌ Failed to get layers: ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  };

  // Navigate to a layer
  const navigateLayer = async (layerName: string): Promise<string> => {
    try {
      const response = await fetch(`${apiBaseUrl}/agent/v2/layer/navigate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '',
        },
        body: JSON.stringify({ layer: layerName }),
      });

      if (!response.ok) {
        throw new Error('Navigation failed');
      }

      const data = await response.json();
      setCurrentLayer(layerName);

      const caps = data.capabilities?.slice(0, 5).map((c: string) => `• ${c}`).join('\n') || 'No capabilities listed';

      return `✅ **Navigated to ${layerName} layer**\n\n**Available tools:**\n${caps}\n\nYou can now use tools from this layer.`;
    } catch (error) {
      return `❌ Navigation failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  };

  // Run code enhancement
  const runEnhancement = async (target?: string): Promise<string> => {
    try {
      const scope = target || 'backend/app/agent';
      
      const response = await fetch(`${apiBaseUrl}/agent/enhance/scan`, {
        headers: {
          'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '',
        },
      });

      if (!response.ok) {
        // Fallback: try autonomous enhancement
        const autoResponse = await fetch(`${apiBaseUrl}/agent/enhance/autonomous?target=error+handling&scope=${encodeURIComponent(scope)}`, {
          method: 'POST',
          headers: {
            'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '',
          },
        });

        if (!autoResponse.ok) {
          throw new Error('Enhancement failed');
        }

        const data = await autoResponse.json();
        return `🔧 **Autonomous Enhancement**\n\nStatus: ${data.status}\n${data.file_enhanced ? `Enhanced: ${data.file_enhanced}` : ''}\n${data.issues_addressed ? `Issues addressed: ${data.issues_addressed}` : ''}`;
      }

      const data = await response.json();
      
      if (data.prioritized_files?.length === 0) {
        return '✅ No enhancement opportunities found. Your code looks good!';
      }

      const topFiles = data.prioritized_files.slice(0, 5).map((f: PrioritizedFile) => {
        return `• **${f.file}** - ${f.total_issues} issues`;
      }).join('\n');

      return `📊 **Code Enhancement Scan**\n\nFiles with improvement opportunities:\n${topFiles}\n\n_Use \`/agent enhance apply <filepath>\` to apply enhancements_`;
    } catch (error) {
      return `❌ Enhancement failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  };

  // Handle agent commands
  const handleAgentCommand = async (command: string, args: string[]): Promise<string> => {
    switch (command) {
      case 'status':
        try {
          const response = await fetch(`${apiBaseUrl}/agent/v2/status/enhanced`);
          const data = await response.json();
          return `📊 **Agent Status**\n\nSession: ${data.session_id?.slice(0, 8)}...\nCurrent Layer: **${data.current_layer}**\nAvailable Tools: ${data.available_tools}\nMemory Entries: ${data.memory_entries_indexed}`;
        } catch {
          return '❌ Agent status unavailable. Is the backend running?';
        }

      case 'layers':
        return await getAgentLayers();

      case 'navigate':
      case 'layer':
        if (args.length === 0) {
          return 'Usage: /agent navigate <layer_name>\nTry: coding, economics, vdc, edge, portal';
        }
        return await navigateLayer(args[0]);

      case 'memory':
        if (args[0] === 'search' && args.length > 1) {
          return `💡 **Use the unified search command instead:**\n\nType \`/search ${args.slice(1).join(' ')}\` in regular chat to search both documents AND conversation memory.`;
        }
        return 'Usage: Use \`/search <query>\` in regular chat to search both documents and memory.';

      case 'search':
        if (args.length === 0) {
          return '💡 **Use the unified search command:**\n\nType \`/search <query>\` in regular chat to search both documents AND conversation memory.';
        }
        return `💡 **Use the unified search command:**\n\nType \`/search ${args.join(' ')}\` in regular chat to search both documents AND conversation memory.`;

      case 'enhance':
        return await runEnhancement(args[0]);

      case 'task':
      case 'checkpoint':
        if (args.length === 0) {
          return 'Usage: /agent task <task_id>\n\nCheck working memory and progress for a task.';
        }
        try {
          const response = await fetch(`${apiBaseUrl}/agent/v2/memory/working/${sessionId}/${args[0]}`, {
            headers: { 'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '' }
          });
          
          if (!response.ok) {
            return `❌ Failed to get task memory`;
          }
          
          const data = await response.json();
          
          if (!data.exists) {
            return `🔍 No working memory found for task: ${args[0]}\n\nTask may be complete or expired (1 hour TTL).`;
          }
          
          const progressBar = '█'.repeat(Math.round(data.progress_percent / 10)) + '░'.repeat(10 - Math.round(data.progress_percent / 10));
          
          return `📊 **Task Progress: ${args[0].slice(0, 16)}...**

${progressBar} ${data.progress_percent}%

✅ Completed (${data.steps_completed.length}):
${data.steps_completed.map((s: string) => `  • ${s}`).join('\n') || '  None yet'}

⏳ Remaining (${data.steps_remaining.length}):
${data.steps_remaining.map((s: string) => `  • ${s}`).join('\n') || '  None - almost done!'}

🕐 Last updated: ${data.last_updated ? new Date(data.last_updated).toLocaleTimeString() : 'Unknown'}`;
        } catch (error) {
          return `❌ Error: ${error instanceof Error ? error.message : 'Network error'}`;
        }

      case 'clear':
        if (args.length === 0) {
          return 'Usage: /agent clear <task_id>\n\nClear working memory for a task.';
        }
        try {
          const response = await fetch(`${apiBaseUrl}/agent/v2/memory/working/${sessionId}/${args[0]}`, {
            method: 'DELETE',
            headers: { 'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '' }
          });
          
          const data = await response.json();
          return data.success 
            ? `✅ Cleared working memory for task: ${args[0].slice(0, 16)}...`
            : `❌ Failed to clear memory`;
        } catch (error) {
          return `❌ Error: ${error instanceof Error ? error.message : 'Network error'}`;
        }

      case 'help':
        return `🤖 **Agent Commands:**

**Status & Info:**
• \`/agent status\` - Check agent status
• \`/agent layers\` - List available layers
• \`/agent help\` - Show this help

**Navigation:**
• \`/agent navigate <layer>\` - Switch to a layer
• \`/agent layer <layer>\` - Same as navigate

**Search:**
• Use \`/search <query>\` in regular chat to search documents AND memory

**Working Memory (Task Checkpoints):**
• \`/agent task <task_id>\` - Check task progress
• \`/agent checkpoint <task_id>\` - Same as above
• \`/agent clear <task_id>\` - Clear task memory

**Self-Improvement:**
• \`/agent enhance\` - Scan for code improvements

**Natural Language:**
Just type your request and I'll route it to the appropriate layer!`;

      default:
        return `Unknown agent command: "${command}". Type /agent help for available commands.`;
    }
  };

  // Web search function - defined BEFORE sendMessage
  const performWebSearch = useCallback(async (query: string): Promise<string> => {
    try {
      const response = await fetch(`${apiBaseUrl}/agent/web-search/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '',
        },
        body: JSON.stringify({
          query,
          count: 5,
          country: 'US',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Web search failed');
      }

      const data = await response.json();
      
      if (!data.success) {
        return `🔍 **Web Search**: ${data.error || 'Search failed'}`;
      }

      if (!data.results || data.results.length === 0) {
        return `🔍 **Web Search**: No results found for "${query}"`;
      }

      const formatted = data.results.map((r: { title?: string; url?: string; description?: string; source?: string }, i: number) => {
        return `${i + 1}. **[${r.title}](${r.url})**
   ${r.description}
   Source: ${r.source}`;
      }).join('\n\n');

      return `🔍 **Web Search Results for "${query}"**\n\n${formatted}`;
    } catch (error) {
      console.error('Web search failed:', error);
      return `🔍 **Web Search Error**: ${error instanceof Error ? error.message : 'Search failed'}`;
    }
  }, [apiBaseUrl]);

  const sendMessage = useCallback(async () => {
    if (!inputValue.trim() && attachments.length === 0) return;
    
    const content = inputValue.trim();
    
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content,
      timestamp: new Date().toISOString(),
      attachments: attachments.length > 0 ? [...attachments] : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setAttachments([]);
    setIsLoading(true);

    // Add thinking message
    const thinkingMessageId = uuidv4();
    const thinkingMessage: Message = {
      id: thinkingMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
          };
    setMessages((prev) => [...prev, thinkingMessage]);

    try {
      // Check for agent commands
      if (content.startsWith('/agent ')) {
        const parts = content.slice(7).trim().split(' ');
        const command = parts[0];
        const args = parts.slice(1);
        
        const response = await handleAgentCommand(command, args);
        
        const reasoning: any = {
          steps: [
            { type: 'thought', content: 'Detected agent command', details: `Command: ${command}` },
            { type: 'tool', content: 'Agent Command Handler', details: `Executed /agent ${command}` },
            { type: 'decision', content: 'Returned command output', details: 'Direct command execution' },
          ],
          toolsConsidered: ['Agent Command Handler'],
          dataLookedUp: ['Agent commands registry'],
          whyThisAnswer: `Direct execution of /agent ${command} command.`,
        };
        
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: response,
          timestamp: new Date().toISOString(),
          reasoning,
        };
        
        // Replace thinking message with actual response
        setMessages((prev) => prev.map(m => m.id === thinkingMessageId ? aiMessage : m));
      } else {
        // Execute through agent
        const result = await executeAgentTask(content);
        
        // Perform web search if enabled (and not already handled by agent)
        let webSearchResult = '';
        if (webSearchEnabled && !content.startsWith('/agent')) {
          webSearchResult = await performWebSearch(content);
        }
        
        if (result || webSearchResult) {
          let responseText = '';
          
          // Build reasoning steps from agent execution
          const reasoningSteps: ReasoningStep[] = [
            { type: 'thought', content: 'Analyzing user request...', timestamp: new Date().toISOString() },
          ];
          
          // Add web search results first if available
          if (webSearchResult) {
            responseText += webSearchResult + '\n\n---\n\n';
            reasoningSteps.push({ type: 'tool', content: 'Web Search', details: 'Searched for relevant information' });
          }
          
          // Add agent result if available
          if (result) {
            responseText += result.message;
            
            reasoningSteps.push({ type: 'tool', content: `Agent Layer: ${result.layer}`, details: `Action: ${result.action}` });
            
            // Add data if present
            if (result.data && Object.keys(result.data).length > 0) {
              const dataPreview = JSON.stringify(result.data, null, 2).substring(0, 500);
              responseText += `\n\n\`\`\`json\n${dataPreview}${dataPreview.length >= 500 ? '...' : ''}\n\`\`\``;
              reasoningSteps.push({ type: 'data', content: 'Retrieved structured data', details: `${Object.keys(result.data).length} data fields` });
            }
            
            // Add suggestions
            if (result.suggested_next_actions?.length) {
              responseText += '\n\n**Suggested next steps:**\n';
              responseText += result.suggested_next_actions.map(a => `• ${a}`).join('\n');
            }
            
            // Use agent's reasoning if provided, otherwise build from result
            const finalReasoning: any = result.reasoning || {
              steps: [
                ...reasoningSteps,
                { type: 'decision', content: 'Generated response using agent layer', details: `Execution time: ${result.execution_time_ms || 'unknown'}ms` },
              ],
              toolsConsidered: ['Agent Execution', `Layer: ${result.layer}`],
              dataLookedUp: result.related_conversations || ['User query', 'Agent context'],
              whyThisAnswer: `Response generated using the ${result.layer} layer with action "${result.action}".`,
            };
            
            const aiMessage: Message = {
              id: uuidv4(),
              role: 'assistant',
              content: responseText,
              timestamp: new Date().toISOString(),
              reasoning: finalReasoning,
            };
            
            // Replace thinking message with actual response
            setMessages((prev) => prev.map(m => m.id === thinkingMessageId ? aiMessage : m));
          } else if (webSearchResult) {
            responseText += 'I found these web results for your query. Let me know if you need more specific information!';
            
            const reasoning: any = {
              steps: [
                ...reasoningSteps,
                { type: 'decision', content: 'Returned web search results', details: 'No agent result available' },
              ],
              toolsConsidered: ['Web Search'],
              dataLookedUp: ['Web search results'],
              whyThisAnswer: 'Response based on web search results only.',
            };
            
            const aiMessage: Message = {
              id: uuidv4(),
              role: 'assistant',
              content: responseText,
              timestamp: new Date().toISOString(),
              reasoning,
            };
            
            // Replace thinking message with actual response
            setMessages((prev) => prev.map(m => m.id === thinkingMessageId ? aiMessage : m));
          }
        } else {
          // Fallback to regular chat
          const reasoning: any = {
            steps: [
              { type: 'thought', content: 'Agent system unavailable' },
              { type: 'decision', content: 'Fell back to local response', details: 'Agent returned no result' },
            ],
            toolsConsidered: ['Agent System (unavailable)'],
            dataLookedUp: [],
            whyThisAnswer: 'Agent system was unavailable, provided fallback response.',
          };
          
          const aiMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: `I understand: "${content}"\n\nThe agent system may be unavailable. Try:\n• Check your connection\n• Use /agent status to verify\n• Try again in a moment`,
            timestamp: new Date().toISOString(),
            reasoning,
          };
          
          // Replace thinking message with fallback response
          setMessages((prev) => prev.map(m => m.id === thinkingMessageId ? aiMessage : m));
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: `❌ Error: ${error instanceof Error ? error.message : 'Something went wrong'}`,
        timestamp: new Date().toISOString(),
      };
      
      // Replace thinking message with error
      setMessages((prev) => prev.map(m => m.id === thinkingMessageId ? errorMessage : m));
    } finally {
      setIsLoading(false);
    }
  }, [inputValue, attachments, currentLayer, sessionId, webSearchEnabled, performWebSearch]);

  const addAttachment = useCallback(async (file: File): Promise<FileValidationResult | null> => {
    // Pre-upload validation - check size/type before starting upload
    const validation = validateFileOnSelect(file);
    if (!validation.valid) {
      // Return validation error for inline display
      return validation;
    }
    
    setIsUploading(true);
    
    // Check if file needs processing (PDF, Image, Audio, Video)
    const needsProcessing = 
      file.type === 'application/pdf' ||
      file.type.startsWith('image/') ||
      file.type.startsWith('audio/') ||
      file.type.startsWith('video/');
    
    if (needsProcessing) {
      // Process and index with session context
      try {
        const tempAttachment: Attachment = {
          id: uuidv4(),
          name: file.name,
          type: file.type,
          size: file.size,
          status: 'uploading',
        };
        setAttachments((prev) => [...prev, tempAttachment]);
        
        const { processing, indexing } = await processAndIndexFile(
          file,
          sessionId,
          (stage) => console.log(`Processing ${file.name}: ${stage}`)
        );
        
        if (processing.success && indexing.success) {
          const finalAttachment: Attachment = {
            ...tempAttachment,
            status: 'complete',
            url: indexing.message,
                      };
          setAttachments((prev) =>
            prev.map((a) => (a.id === tempAttachment.id ? finalAttachment : a))
          );
          
          // Add a system message about the processed file with suggested questions
          const systemMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: `📄 **Processed ${processing.metadata.type}: ${file.name}**\n\n✅ Extracted ${processing.metadata.wordCount || 'content'} and indexed to this chat context.\n\n**Suggested questions:**\n• "Summarize this document"\n• "Extract tables and data"\n• "Find costs and pricing"\n• "What are the key dates?"\n\nOr ask anything else about this file.`,
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, systemMessage]);
        } else {
          setAttachments((prev) =>
            prev.map((a) =>
              a.id === tempAttachment.id
                ? { ...a, status: 'error', error: processing.error || indexing.message }
                : a
            )
          );
          
          // Add error message
          const errorMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: `❌ **Failed to process ${file.name}**\n\n${processing.error || indexing.message || 'Unknown error'}`,
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, errorMessage]);
        }
      } catch (error) {
        console.error('File processing error:', error);
        
        // Add error message on exception
        const errorMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: `❌ **Failed to process ${file.name}**\n\n${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        // Keep isUploading true until entire flow completes
        setIsUploading(false);
      }
    } else {
      // Simple upload for other file types
      try {
        const tempAttachment: Attachment = {
          id: uuidv4(),
          name: file.name,
          type: file.type,
          size: file.size,
          status: 'uploading',
        };
        setAttachments((prev) => [...prev, tempAttachment]);
        
        const formData = new FormData();
        formData.append('file', file);
        
        const token = getAuthToken();
        
        const response = await fetch(`${getApiUrl()}/documents/upload/chat`, {
          method: 'POST',
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
          },
          body: formData,
        });
        
        if (!response.ok) {
          setAttachments((prev) => prev.filter((a) => a.id !== tempAttachment.id));
          throw new Error(`Upload failed: ${response.status}`);
        }
        
        const data = await response.json();
        
        const finalAttachment: Attachment = {
          ...tempAttachment,
          url: data.url,
          status: 'complete',
        };
        
        setAttachments((prev) =>
          prev.map((a) => (a.id === tempAttachment.id ? finalAttachment : a))
        );
        
        // Add success message with suggested questions
        const systemMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: `📄 **Uploaded: ${file.name}**\n\n✅ File ready. You can now ask questions about this file.`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, systemMessage]);
      } catch (error) {
        console.error('File upload error:', error);
        
        // Add error message
        const errorMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: `❌ **Failed to upload ${file.name}**\n\n${error instanceof Error ? error.message : 'Upload failed'}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsUploading(false);
      }
    }
    
    // Return null on success (validation passed and upload completed)
    return null;
  }, [sessionId]);

  const removeAttachment = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    isUploading,
    attachments,
    messagesEndRef,
    currentLayer,
    webSearchEnabled,
    setWebSearchEnabled,
    sendMessage,
    addAttachment,
    removeAttachment,
    clearMessages,
    performWebSearch,
    // Agent-specific
    executeAgentTask,
    searchMemory,
    getAgentLayers,
    navigateLayer,
  };
}
