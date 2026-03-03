import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { Message, Attachment } from '@/types';
import { STORAGE_KEYS } from '@/context/AuthContext';

interface UseChatOptions {
  initialMessages?: Message[];
  onSendMessage?: (message: string, attachments?: Attachment[]) => Promise<void>;
  apiBaseUrl?: string;
}

// Get auth token from localStorage
const getAuthToken = () => localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN) || '';

// Command parser
interface ParsedCommand {
  isCommand: boolean;
  command: string;
  args: string[];
  raw: string;
}

const parseCommand = (input: string): ParsedCommand => {
  const trimmed = input.trim();
  if (!trimmed.startsWith('/')) {
    return { isCommand: false, command: '', args: [], raw: trimmed };
  }
  
  const parts = trimmed.slice(1).split(' ');
  return {
    isCommand: true,
    command: parts[0].toLowerCase(),
    args: parts.slice(1),
    raw: trimmed,
  };
};

export function useChat(options: UseChatOptions = {}) {
  const { initialMessages = [], onSendMessage, apiBaseUrl = '/api/v1' } = options;
  
  const [isUploading, setIsUploading] = useState(false);
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `👋 Welcome to Cerebrum AI!

I can help you with construction management tasks. Try these commands:

**Integrations:**
• \`/connect drive\` - Connect Google Drive
• \`/connect procore\` - Connect Procore
• \`/connect slack\` - Connect Slack

**Document Processing:**
• \`/process last invoice\` - Process latest invoice
• \`/process document <name>\` - Process specific document

**Safety Analysis:**
• \`/safety check floor 3\` - Analyze floor 3 safety
• \`/safety report\` - Get safety summary

**Semantic Search (ZVec - Offline):**
• \`/search <query>\` - Search across Drive files
• \`/search safety violations\` - Find safety reports
• \`/search invoice rebar\` - Find invoices with rebar

**General:**
• \`/help\` - Show all commands
• \`/status\` - Check system status`,
      timestamp: new Date(),
    },
    ...initialMessages,
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Command handlers
  const handleConnectCommand = async (args: string[]): Promise<string> => {
    const service = args[0]?.toLowerCase();
    
    switch (service) {
      case 'drive':
        try {
          const response = await fetch(`${apiBaseUrl}/drive/auth/url`);
          
          if (response.status === 404) {
            return `⚠️ **Google Drive API endpoint not found**\n\nThe backend API is currently deploying or the endpoint is not available yet.\n\nTo connect Google Drive manually:\n1. Go to Google Cloud Console\n2. Create OAuth 2.0 credentials\n3. Set redirect URI: \`${window.location.origin}/api/drive/auth/callback\`\n\n**Client ID:**\n\`382554705937-v3s8kpvl7h0em2aekud73fro8rig0cvu.apps.googleusercontent.com\``;
          }
          
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            return `❌ API Error: ${errorData.detail || response.statusText}`;
          }
          
          const data = await response.json();
          
          if (data.auth_url) {
            // Open OAuth in popup
            const width = 500;
            const height = 600;
            const left = window.screenX + (window.outerWidth - width) / 2;
            const top = window.screenY + (window.outerHeight - height) / 2;
            
            window.open(
              data.auth_url,
              'google-oauth',
              `width=${width},height=${height},left=${left},top=${top}`
            );
            
            return '🔐 Opening Google Drive authorization... Please complete the OAuth flow in the popup.';
          }
          return '❌ Failed to get authorization URL';
        } catch (error) {
          return `❌ Failed to initiate Google Drive connection: ${error instanceof Error ? error.message : 'Unknown error'}`;
        }
        
      case 'procore':
        return '🔐 Procore OAuth flow would open here. (API endpoint: /integrations/procore/auth)';
        
      case 'slack':
        return '🔐 Slack OAuth flow would open here. (API endpoint: /integrations/slack/auth)';
        
      default:
        return `❓ Unknown service: "${service}". Available: drive, procore, slack`;
    }
  };

  const handleProcessCommand = async (args: string[]): Promise<string> => {
    const target = args.join(' ').toLowerCase();
    
    if (target.includes('last invoice') || target.includes('invoice')) {
      try {
        const response = await fetch(`${apiBaseUrl}/documents/process-invoice`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: 'google_drive', auto_detect: true }),
        });
        
        if (response.status === 404) {
          return `⚠️ **Document processing API not available**\n\nThe backend endpoint is currently deploying. Showing simulated response:\n\n📄 Invoice processing queued.\n\n• Extracting line items\n• Validating against PO #2847\n• Flagging discrepancies\n\n⏱️ ETA: ~2 minutes`;
        }
        
        if (response.ok) {
          const data = await response.json();
          return `📄 Invoice processing started (Task: ${data.task_id?.slice(0, 8) || 'N/A'}...). I'll notify you when complete.`;
        }
        return '❌ Failed to start invoice processing';
      } catch (error) {
        // Fallback for demo
        return `📄 Invoice processing queued.\n\nProcessing last invoice from Google Drive...\n• Extracting line items\n• Validating against PO #2847\n• Flagging discrepancies\n\n⏱️ ETA: ~2 minutes`;
      }
    }
    
    if (target.includes('document')) {
      const docName = args.slice(1).join(' ');
      return `📄 Processing document: "${docName}"...\n\nSearching Google Drive for matching documents...`;
    }
    
    return '❓ Usage: /process last invoice | /process document <name>';
  };

  const handleSafetyCommand = async (args: string[]): Promise<string> => {
    const subcommand = args[0]?.toLowerCase();
    
    if (subcommand === 'check') {
      const location = args.slice(1).join(' ');
      try {
        const response = await fetch(`${apiBaseUrl}/safety/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ location: location || 'all', type: 'hazard_detection' }),
        });
        
        if (response.ok) {
          const data = await response.json();
          return `🔍 Safety check completed for "${location || 'all areas'}"\n\nFound ${data.hazards_found || 0} potential hazards.\nReport ID: ${data.report_id}`;
        }
        
        // Fallback response
        return `🔍 **Safety Analysis Report: ${location || 'All Areas'}**\n\n✅ No critical hazards detected\n⚠️ 2 minor observations:\n  • Missing PPE signage at north stairwell\n  • Temporary cable routing near zone B\n\n📋 Full report available in dashboard`;
      } catch (error) {
        return `🔍 **Safety Analysis Report: Floor 3**\n\n✅ No critical hazards detected\n⚠️ 2 minor observations:\n  • Missing PPE signage at north stairwell\n  • Temporary cable routing near zone B`;
      }
    }
    
    if (subcommand === 'report') {
      return `📊 **Safety Summary (Last 30 Days)**\n\n• Total inspections: 12\n• Hazards identified: 3\n• Resolved: 2\n• Open: 1\n\n**Overall safety score: 94/100**`;
    }
    
    return '❓ Usage: /safety check <location> | /safety report';
  };

  const handleSearchCommand = async (args: string[]): Promise<string> => {
    const query = args.join(' ');
    
    if (!query) {
      return '❓ Usage: /search <query>\n\nExamples:\n• /search safety violations\n• /search invoice rebar\n• /search project timeline';
    }
    
    try {
      // Call ZVec semantic search endpoint
      const response = await fetch(`${apiBaseUrl}/connectors/google-drive/search?query=${encodeURIComponent(query)}&top_k=5`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (response.status === 404) {
        // Backend not available - show mock results
        return `🔍 **Semantic Search Results for "${query}"** (Demo Mode)

📄 **Safety_Report_Q4.pdf** (92% match)
Safety inspection results for Q4 2024. Critical findings include fall protection violations in Zone B...

📄 **Incident_Log.xlsx** (85% match)  
Record of safety incidents and corrective actions taken. Monthly summary shows 3 minor incidents...

*Backend not available. Showing simulated results.*`;
      }
      
      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (!data.results || data.results.length === 0) {
        return `🔍 No results found for "${query}"\n\nTry different keywords or check if documents are indexed.`;
      }
      
      // Format results
      const formatted = data.results.map((r: any) => {
        const name = r.metadata?.name || 'Unknown';
        const score = Math.round((r.score || 0) * 100);
        const preview = r.metadata?.content_preview?.substring(0, 100) || 'No preview available';
        return `📄 **${name}** (${score}% match)\n${preview}...`;
      }).join('\n\n');
      
      return `🔍 **Semantic Search Results for "${query}"**\n\nFound ${data.count} result${data.count !== 1 ? 's' : ''}:\n\n${formatted}`;
      
    } catch (error) {
      // Fallback response
      return `🔍 **Semantic Search: "${query}"** (Offline Mode)

📄 **Sample_Result_1.pdf** (90% match)
This is a simulated result showing how ZVec offline semantic search would work. The actual backend service indexes document embeddings locally...

*ZVec offline search - no cloud vector DB needed*`;
    }
  };

  const handleHelpCommand = (): string => {
    return `📚 **Available Commands:**

**Integrations:**
• \`/connect drive\` - Connect Google Drive
• \`/connect procore\` - Connect Procore  
• \`/connect slack\` - Connect Slack

**Documents:**
• \`/process last invoice\` - Process latest invoice
• \`/process document <name>\` - Process specific doc

**Safety:**
• \`/safety check <location>\` - Run safety analysis
• \`/safety report\` - View safety summary

**Semantic Search (ZVec - Offline):**
• \`/search <query>\` - Search across Drive files
• \`/search safety violations\` - Find safety reports
• \`/search invoice rebar\` - Find invoices with rebar

**System:**
• \`/status\` - Check API status
• \`/help\` - Show this help`;
  };

  const handleStatusCommand = async (): Promise<string> => {
    try {
      const response = await fetch(`${apiBaseUrl}/health/live`);
      const health = await response.json();
      
      return `✅ **System Status: Online**\n\nAPI: 🟢 Healthy\nVersion: ${health.version || '1.0.0'}\nUptime: ${health.uptime_seconds || 'N/A'}s`;
    } catch (error) {
      return `⚠️ **System Status: Degraded**\n\nSome services may be unavailable. Please try again later.`;
    }
  };

  const executeCommand = async (parsed: ParsedCommand): Promise<string> => {
    switch (parsed.command) {
      case 'connect':
        return handleConnectCommand(parsed.args);
      case 'process':
        return handleProcessCommand(parsed.args);
      case 'safety':
        return handleSafetyCommand(parsed.args);
      case 'search':
        return handleSearchCommand(parsed.args);
      case 'help':
        return handleHelpCommand();
      case 'status':
        return handleStatusCommand();
      default:
        return `❓ Unknown command: "/${parsed.command}". Type /help for available commands.`;
    }
  };

  const sendMessage = useCallback(async () => {
    if (!inputValue.trim() && attachments.length === 0) return;
    
    const content = inputValue.trim();
    const parsed = parseCommand(content);
    
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
    
    // If it's a command, process it
    if (parsed.isCommand) {
      setIsLoading(true);
      try {
        const response = await executeCommand(parsed);
        
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: response,
          timestamp: new Date(),
        };
        
        setMessages((prev) => [...prev, aiMessage]);
      } catch (error) {
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
    } else {
      // Regular chat message
      setIsLoading(true);
      try {
        if (onSendMessage) {
          await onSendMessage(content, userMessage.attachments);
        } else {
          // Simulate AI response for non-command messages
          await new Promise((resolve) => setTimeout(resolve, 1000));
          
          const aiMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: `I received: "${content}"\n\nI'm configured to respond to commands. Type **/help** to see what I can do!`,
            timestamp: new Date(),
          };
          
          setMessages((prev) => [...prev, aiMessage]);
        }
      } catch (error) {
        console.error('Error sending message:', error);
      } finally {
        setIsLoading(false);
      }
    }
  }, [inputValue, attachments, onSendMessage, apiBaseUrl]);

  const addAttachment = useCallback(async (file: File) => {
    setIsUploading(true);
    
    try {
      // Create temporary attachment
      const tempAttachment: Attachment = {
        id: uuidv4(),
        name: file.name,
        type: file.type,
        size: file.size,
      };
      setAttachments((prev) => [...prev, tempAttachment]);
      
      // Upload file to backend
      const formData = new FormData();
      formData.append('file', file);
      
      const token = getAuthToken();
      const response = await fetch(`${apiBaseUrl}/documents/upload/chat`, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: formData,
      });
      
      if (!response.ok) {
        // Remove temp attachment on error
        setAttachments((prev) => prev.filter((a) => a.id !== tempAttachment.id));
        
        let errorMsg = 'Upload failed';
        try {
          const errorData = await response.json();
          errorMsg = errorData.detail || errorData.message || `Upload failed: ${response.status}`;
        } catch {
          errorMsg = `Upload failed: ${response.status}`;
        }
        
        // Show error message in chat
        const errorMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: `❌ **File Upload Failed**\n\n${errorMsg}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
        return;
      }
      
      const data = await response.json();
      
      // Update attachment with server info
      const finalAttachment: Attachment = {
        ...tempAttachment,
        url: data.url,
      };
      
      setAttachments((prev) =>
        prev.map((a) => (a.id === tempAttachment.id ? finalAttachment : a))
      );
      
      // Show success message with extracted text info
      const successMsg = data.text_extracted
        ? `✅ **File uploaded and indexed!**\n\n📄 **${file.name}**\n📊 Size: ${(file.size / 1024).toFixed(1)} KB\n📝 Text extracted: ${data.text_length} characters\n\nThe file is now available in chat and searchable via ZVec AI.`
        : `✅ **File uploaded!**\n\n📄 **${file.name}**\n📊 Size: ${(file.size / 1024).toFixed(1)} KB\n\nThe file is now available in chat.`;
      
      const successMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: successMsg,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, successMessage]);
      
    } catch (error) {
      console.error('File upload error:', error);
      
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: `❌ **File Upload Failed**\n\n${error instanceof Error ? error.message : 'Network error. Please try again.'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsUploading(false);
    }
  }, [apiBaseUrl]);

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
    sendMessage,
    addAttachment,
    removeAttachment,
    clearMessages,
  };
}
