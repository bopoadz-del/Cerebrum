import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Message, Attachment } from '@/types';
import { STORAGE_KEYS } from '@/context/AuthContext';

interface UseAgentChatOptions {
  initialMessages?: Message[];
  apiBaseUrl?: string;
  sessionId?: string;
}

interface AgentResponse {
  success: boolean;
  action: string;
  layer: string;
  data: any;
  message: string;
  execution_time_ms?: number;
  related_conversations?: string[];
  suggested_next_actions?: string[];
  timestamp: string;
}

// Get auth token from localStorage
const getAuthToken = () => localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN) || '';

export function useAgentChat(options: UseAgentChatOptions = {}) {
  const { 
    initialMessages = [], 
    apiBaseUrl = '/api/v1',
    sessionId = uuidv4()
  } = options;
  
  const [isUploading, setIsUploading] = useState(false);
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `👋 **Welcome to Cerebrum AI Agent!**

I'm your autonomous construction intelligence assistant. I can:

**🏗️ Construction Tasks:**
• Analyze BIM models and extract quantities
• Calculate costs using RSMeans data
• Check for design clashes
• Generate material takeoffs

**🤖 Agent Capabilities:**
• Search through project history and conversations
• Navigate between system layers (coding, registry, validation, etc.)
• Self-modify to add new features
• Enhance and improve my own code

**💬 Try asking:**
• "Calculate drywall costs for Building A"
• "Search for previous foundation discussions"
• "What layers are available?"
• "Analyze this invoice and flag discrepancies"

**🛠️ Agent Commands:**
• \`/agent status\` - Check agent status
• \`/agent layers\` - List available layers
• \`/agent memory search <query>\` - Search conversation history
• \`/agent enhance\` - Analyze and improve code quality

How can I help you today?`,
      timestamp: new Date(),
    },
    ...initialMessages,
  ]);
  
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [currentLayer, setCurrentLayer] = useState<string>('coding');

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Check agent status on mount
  useEffect(() => {
    checkAgentStatus();
  }, []);

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

  // Execute task through the agent
  const executeAgentTask = async (task: string, context?: any): Promise<AgentResponse | null> => {
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

      const formatted = data.results.map((r: any, i: number) => {
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
      
      const layers = data.layers.map((l: any) => {
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

      const topFiles = data.prioritized_files.slice(0, 5).map((f: any) => {
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
        } catch (error) {
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
          const query = args.slice(1).join(' ');
          return await searchMemory(query);
        }
        return 'Usage: /agent memory search <query>';

      case 'search':
        if (args.length === 0) {
          return 'Usage: /agent search <query>';
        }
        return await searchMemory(args.join(' '));

      case 'enhance':
        return await runEnhancement(args[0]);

      case 'help':
        return `🤖 **Agent Commands:**

**Status & Info:**
• \`/agent status\` - Check agent status
• \`/agent layers\` - List available layers
• \`/agent help\` - Show this help

**Navigation:**
• \`/agent navigate <layer>\` - Switch to a layer
• \`/agent layer <layer>\` - Same as navigate

**Memory:**
• \`/agent search <query>\` - Search conversation history
• \`/agent memory search <query>\` - Same as above

**Self-Improvement:**
• \`/agent enhance\` - Scan for code improvements

**Natural Language:**
Just type your request and I'll route it to the appropriate layer!`;

      default:
        return `Unknown agent command: "${command}". Type /agent help for available commands.`;
    }
  };

  const sendMessage = useCallback(async () => {
    if (!inputValue.trim() && attachments.length === 0) return;
    
    const content = inputValue.trim();
    
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content,
      timestamp: new Date(),
      attachments: attachments.length > 0 ? [...attachments] : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setAttachments([]);
    setIsLoading(true);

    try {
      // Check for agent commands
      if (content.startsWith('/agent ')) {
        const parts = content.slice(7).trim().split(' ');
        const command = parts[0];
        const args = parts.slice(1);
        
        const response = await handleAgentCommand(command, args);
        
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: response,
          timestamp: new Date(),
        };
        
        setMessages((prev) => [...prev, aiMessage]);
      } else {
        // Execute through agent
        const result = await executeAgentTask(content);
        
        if (result) {
          let responseText = result.message;
          
          // Add data if present
          if (result.data && Object.keys(result.data).length > 0) {
            const dataPreview = JSON.stringify(result.data, null, 2).substring(0, 500);
            responseText += `\n\n\`\`\`json\n${dataPreview}${dataPreview.length >= 500 ? '...' : ''}\n\`\`\``;
          }
          
          // Add suggestions
          if (result.suggested_next_actions?.length) {
            responseText += '\n\n**Suggested next steps:**\n';
            responseText += result.suggested_next_actions.map(a => `• ${a}`).join('\n');
          }
          
          const aiMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: responseText,
            timestamp: new Date(),
          };
          
          setMessages((prev) => [...prev, aiMessage]);
        } else {
          // Fallback to regular chat
          const aiMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: `I understand: "${content}"\n\nThe agent system may be unavailable. Try:\n• Check your connection\n• Use /agent status to verify\n• Try again in a moment`,
            timestamp: new Date(),
          };
          
          setMessages((prev) => [...prev, aiMessage]);
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: `❌ Error: ${error instanceof Error ? error.message : 'Something went wrong'}`,
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [inputValue, attachments, currentLayer, sessionId]);

  const addAttachment = useCallback(async (file: File) => {
    setIsUploading(true);
    
    try {
      const tempAttachment: Attachment = {
        id: uuidv4(),
        name: file.name,
        type: file.type,
        size: file.size,
      };
      setAttachments((prev) => [...prev, tempAttachment]);
      
      // Upload via connectors endpoint
      const formData = new FormData();
      formData.append('file', file);
      
      const token = getAuthToken();
      const RAW_API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
      const API_URL = RAW_API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
        ? RAW_API_URL 
        : `${RAW_API_URL.replace(/\/?$/, '')}/api/v1`;
      
      const response = await fetch(`${API_URL}/connectors/upload/chat`, {
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
      };
      
      setAttachments((prev) =>
        prev.map((a) => (a.id === tempAttachment.id ? finalAttachment : a))
      );
      
    } catch (error) {
      console.error('File upload error:', error);
    } finally {
      setIsUploading(false);
    }
  }, []);

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
    sendMessage,
    addAttachment,
    removeAttachment,
    clearMessages,
    // Agent-specific
    executeAgentTask,
    searchMemory,
    getAgentLayers,
    navigateLayer,
  };
}
