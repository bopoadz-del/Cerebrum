import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { 
  Message, 
  Attachment, 
  ReasoningData, 
  ReasoningStep, 
  WebSearchData, 
  CodeExecutionData, 
  ImageAnalysisResult,
  ImageUpload 
} from '@/types';
import { STORAGE_KEYS } from '@/context/AuthContext';
import { uploadChatFile, formatFileSize, SUPPORTED_TYPES } from '@/lib/fileProcessing';
// API Configuration - fallback to production URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const getApiUrl = () => {
  const url = API_BASE_URL.replace(/\/?$/, '');
  return url.endsWith('/api/v1') ? url : `${url}/api/v1`;
};

interface RSMeansItem {
  id?: string;
  rsmeans_id?: string;
  description?: string;
  base_cost?: number;
  unit_cost?: number;
  unit?: string;
}

interface FormulaItem {
  name?: string;
  id?: string;
  category?: string;
  description?: string;
}

interface BuildingType {
  code: string;
  name: string;
  cost_per_sf: number;
  typical_size_sf?: number;
}

interface CityIndex {
  city: string;
  index: number;
  region: string;
}

interface SearchResult {
  name?: string;
  score?: number;
  content_preview?: string;
  source?: string;
}

interface MemoryResult {
  source: string;
  score: number;
  content?: string;
}

interface UseChatOptions {
  initialMessages?: Message[];
  onSendMessage?: (message: string, attachments?: Attachment[]) => Promise<void>;
  apiBaseUrl?: string;
}

// Parameter collection state for interactive commands
interface ParameterCollectionState {
  command: string | null;
  step: number;
  data: Record<string, string>;
}

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

// Map HTTP errors to user-friendly messages
const getUserFriendlyError = (status: number, defaultMessage: string): string => {
  const errorMessages: Record<number, string> = {
    400: 'Invalid request. Please check your input and try again.',
    401: 'Authentication failed. Please sign in again.',
    403: 'You don\'t have permission to do this.',
    404: 'Resource not found. It may have been removed or doesn\'t exist.',
    408: 'Request timed out. The server is taking too long to respond.',
    429: 'Too many requests. Please wait a moment and try again.',
    500: 'Server error. Our team has been notified. Please try again in a moment.',
    502: 'Service temporarily unavailable. Please try again shortly.',
    503: 'Service is busy. Please try again in a few moments.',
    504: 'Gateway timeout. The service is experiencing high load.',
  };

  // Handle network errors (no status code)
  if (status === 0) {
    return 'Network connection failed. Please check your internet connection.';
  }

  return errorMessages[status] || `Error: ${defaultMessage}`;
};

// Detect if query needs agent mode
const needsAgentMode = (input: string): { needsAgent: boolean; reason: string } => {
  const lower = input.toLowerCase();
  
  // Complex tasks that need agent
  const agentKeywords = [
    'generate code', 'create endpoint', 'build api', 'write function',
    'modify', 'refactor', 'fix bug', 'deploy', 'git commit',
    'analyze codebase', 'scan security', 'run tests', 'self healing',
    'create layer', 'add capability', 'modify layer',
    'bim model', 'clash detection', 'quantity takeoff',
    'edge device', 'jetson', 'deploy model',
    'autonomous', 'self modify', 'auto fix'
  ];
  
  for (const keyword of agentKeywords) {
    if (lower.includes(keyword)) {
      return { 
        needsAgent: true, 
        reason: `This task involves "${keyword}" which requires the Agent's full capabilities (14 layers, memory, tool execution)` 
      };
    }
  }
  
  // Multi-step tasks
  if (lower.includes('and then') || lower.includes('after that') || lower.includes('next step')) {
    return { 
      needsAgent: true, 
      reason: 'Multi-step tasks with dependencies are better handled by the Agent mode' 
    };
  }
  
  return { needsAgent: false, reason: '' };
};

// Highlight matching text in search results
const highlightMatch = (text: string, query: string): string => {
  if (!text || !query) return text;
  
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const queryWords = lowerQuery.split(/\s+/).filter(w => w.length > 2);
  
  // Find the best match position
  let matchIndex = lowerText.indexOf(lowerQuery);
  let matchLength = lowerQuery.length;
  
  // If exact phrase not found, try individual words
  if (matchIndex === -1 && queryWords.length > 0) {
    // Find the first word that matches
    for (const word of queryWords) {
      matchIndex = lowerText.indexOf(word);
      if (matchIndex !== -1) {
        matchLength = word.length;
        break;
      }
    }
  }
  
  if (matchIndex === -1) {
    // No match found, return first 100 chars
    return text.substring(0, 100) + (text.length > 100 ? '...' : '');
  }
  
  // Get context around the match (40 chars before, 60 after)
  const contextBefore = 40;
  const contextAfter = 60;
  const start = Math.max(0, matchIndex - contextBefore);
  const end = Math.min(text.length, matchIndex + matchLength + contextAfter);
  
  const before = text.substring(start, matchIndex);
  const match = text.substring(matchIndex, matchIndex + matchLength);
  const after = text.substring(matchIndex + matchLength, end);
  
  const prefix = start > 0 ? '...' : '';
  const suffix = end < text.length ? '...' : '';
  
  return `${prefix}${before}<mark>${match}</mark>${after}${suffix}`;
};

export function useChat(options: UseChatOptions = {}) {
  const { initialMessages = [], onSendMessage } = options;
  const apiBaseUrl = getApiUrl(); // Always use full API URL
  
  const [isUploading, setIsUploading] = useState(false);
  const [showAgentSuggestion, setShowAgentSuggestion] = useState<{show: boolean; reason: string}>({ show: false, reason: '' });
  
  // Parameter collection state for interactive commands
  const [paramCollection, setParamCollection] = useState<ParameterCollectionState>({
    command: null,
    step: 0,
    data: {},
  });
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `👋 **Welcome to Cerebrum AI!**

I have access to construction data and tools. Try these:

**📊 Cost & Estimation:**
• \`/cost concrete\` - Search RSMeans items
• \`/formula beam\` - Find construction formulas  
• \`/estimate office 50000\` - Building cost estimate
• \`/city Riyadh\` - Location cost index
• \`/calculate concrete_volume_rect\` - Run calculations

**🔍 Search & Documents:**
• \`/search safety violations\` - Search documents
• \`/process last invoice\` - Process invoice

**🔗 Integrations:**
• \`/connect drive\` - Connect OneDrive
• \`/status\` - Check system status

💡 **Tip:** For complex tasks (code generation, BIM analysis, multi-step workflows), switch to **🧠 Agent Mode** above!`,
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

  // Check if input needs agent mode
  useEffect(() => {
    if (inputValue.length > 10) {
      const check = needsAgentMode(inputValue);
      setShowAgentSuggestion({ show: check.needsAgent, reason: check.reason });
    } else {
      setShowAgentSuggestion({ show: false, reason: '' });
    }
  }, [inputValue]);

  // Get auth token from localStorage
  const getAuthToken = () => localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN) || '';

  // ============ ECONOMICS COMMANDS ============
  const handleCostCommand = async (args: string[]): Promise<string> => {
    const query = args.join(' ');
    if (!query) {
      return '❓ Usage: /cost <item>\n\nExamples:\n• /cost concrete\n• /cost pipe\n• /cost manhole';
    }
    
    try {
      const response = await fetch(`${apiBaseUrl}/economics/rsmeans/search?q=${encodeURIComponent(query)}&limit=5`);
      
      if (!response.ok) {
        return `❌ ${getUserFriendlyError(response.status, response.statusText)}`;
      }
      
      const data = await response.json();
      
      if (!data.results || data.results.length === 0) {
        return `🔍 No items found for "${query}"\n\nTry: concrete, pipe, rebar, asphalt, etc.`;
      }
      
      const items = data.results.map((item: RSMeansItem) => {
        const id = item.id || item.rsmeans_id || 'N/A';
        const desc = item.description || 'No description';
        const cost = item.base_cost || item.unit_cost || 0;
        const unit = item.unit || 'EA';
        return `**${id}** - ${desc}\n   💰 $${cost}/${unit}`;
      }).join('\n\n');
      
      return `📊 **RSMeans Items for "${query}"**\n\n${items}\n\n💡 Tip: Use \`/calculate <formula_id>\` for construction calculations`;
    } catch (error) {
      return `❌ Error searching costs: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  const handleFormulaCommand = async (args: string[]): Promise<string> => {
    const query = args.join(' ');
    if (!query) {
      return '❓ Usage: /formula <query>\n\nExamples:\n• /formula concrete\n• /formula beam\n• /formula runoff';
    }
    
    try {
      const response = await fetch(`${apiBaseUrl}/economics/formulas?q=${encodeURIComponent(query)}`);
      
      if (!response.ok) {
        return `❌ ${getUserFriendlyError(response.status, response.statusText)}`;
      }
      
      const data = await response.json();
      
      if (!data.results || data.results.length === 0) {
        return `🔍 No formulas found for "${query}"\n\nTry: concrete, beam, structural, hydraulics, etc.`;
      }
      
      const formulas = data.results.slice(0, 5).map((f: FormulaItem) => {
        const name = f.name || f.id;
        const cat = f.category || 'General';
        const desc = f.description || '';
        return `**${name}** (${cat})\n   ${desc}`;
      }).join('\n\n');
      
      return `📐 **Construction Formulas for "${query}"**\n\n${formulas}\n\n💡 Use \`/calculate <formula_id>\` to execute a formula`;
    } catch (error) {
      return `❌ Error searching formulas: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  const handleEstimateCommand = async (args: string[], isInteractive = false): Promise<string> => {
    // Check if we need to start interactive parameter collection
    if (!isInteractive && args.length < 2) {
      setParamCollection({
        command: 'estimate',
        step: 1,
        data: {},
      });
      return `🏗️ **Building Cost Estimate**

Let's estimate your building cost. I'll ask for the details one by one.

**Step 1:** What type of building?

Available types:
• **office** - Office building
• **warehouse** - Warehouse/industrial
• **residential-single** - Single-family home
• **residential-multi** - Multi-family residential
• **retail** - Retail store
• **hospital** - Healthcare facility
• **school** - Educational facility

Type one of the above (or use "/building-types" to see all options):`;
    }

    // If we're in interactive mode and have collected all params
    if (isInteractive) {
      const buildingType = paramCollection.data.buildingType;
      const sizeSf = parseFloat(paramCollection.data.sizeSf || '0');
      const city = paramCollection.data.city || 'National Average';

      if (!buildingType || isNaN(sizeSf) || sizeSf <= 0) {
        return '❌ Invalid parameters collected. Please try again with /estimate';
      }

      try {
        const response = await fetch(`${apiBaseUrl}/economics/estimate/quick?building_type=${buildingType}&size_sf=${sizeSf}&city=${encodeURIComponent(city)}`);

        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          if (error.detail?.includes('Unknown building type')) {
            return `❌ Unknown building type: "${buildingType}"\n\nUse /building-types to see available options.`;
          }
          return `❌ ${getUserFriendlyError(response.status, error.detail || response.statusText)}`;
        }

        const data = await response.json();

        return `🏢 **Building Cost Estimate**

**${data.building_type}**
📏 Size: ${data.size_sf.toLocaleString()} SF
📍 Location: ${data.city}
💵 Cost/SF: $${data.base_cost_per_sf}
📊 Location Factor: ${data.location_factor}

**💰 Total Estimated Cost: $${data.total_cost.toLocaleString()}**

${data.description || ''}`;
      } catch (error) {
        return `❌ Error calculating estimate: ${error instanceof Error ? error.message : 'Network error'}`;
      }
    }

    // Original non-interactive path
    const buildingType = args[0];
    const sizeSf = parseFloat(args[1]);
    const city = args[2] || 'National Average';

    if (isNaN(sizeSf)) {
      return '❌ Size must be a number (square feet)';
    }

    try {
      const response = await fetch(`${apiBaseUrl}/economics/estimate/quick?building_type=${buildingType}&size_sf=${sizeSf}&city=${encodeURIComponent(city)}`);

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        if (error.detail?.includes('Unknown building type')) {
          return `❌ Unknown building type: "${buildingType}"\n\nUse /building-types to see available options.`;
        }
        return `❌ ${getUserFriendlyError(response.status, error.detail || response.statusText)}`;
      }

      const data = await response.json();

      return `🏢 **Building Cost Estimate**

**${data.building_type}**
📏 Size: ${data.size_sf.toLocaleString()} SF
📍 Location: ${data.city}
💵 Cost/SF: $${data.base_cost_per_sf}
📊 Location Factor: ${data.location_factor}

**💰 Total Estimated Cost: $${data.total_cost.toLocaleString()}**

${data.description || ''}`;
    } catch (error) {
      return `❌ Error calculating estimate: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  const handleBuildingTypesCommand = async (): Promise<string> => {
    try {
      const response = await fetch(`${apiBaseUrl}/economics/building-types`);
      const data = await response.json();
      
      if (!data.building_types) {
        return '❌ Error loading building types';
      }
      
      const types = data.building_types.map((t: BuildingType) => {
        return `• **${t.code}** - ${t.name}\n   $${t.cost_per_sf}/SF (typical: ${t.typical_size_sf?.toLocaleString()} SF)`;
      }).join('\n\n');
      
      return `🏗️ **Available Building Types**\n\n${types}\n\n💡 Usage: /estimate <type_code> <size_sf> [city]`;
    } catch (error) {
      return `❌ Error: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  const handleCityCommand = async (args: string[]): Promise<string> => {
    const city = args.join(' ');
    if (!city) {
      return '❓ Usage: /city <city_name>\n\nExamples:\n• /city Riyadh\n• /city Dubai\n• /city "New York"';
    }
    
    try {
      const response = await fetch(`${apiBaseUrl}/economics/city-indices?region=`);
      const data = await response.json();
      
      // Find matching city
      const match = data.cities?.find((c: CityIndex) => 
        c.city.toLowerCase().includes(city.toLowerCase())
      );
      
      if (!match) {
        return `🔍 City "${city}" not found.\n\nTry major cities like: Riyadh, Dubai, New York, London, etc.`;
      }
      
      return `📍 **${match.city}**

📊 Cost Index: ${match.index}
🌍 Region: ${match.region}

An index of 1.0 = National Average
Higher = More expensive, Lower = Less expensive`;
    } catch (error) {
      return `❌ Error: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  const handleCalculateCommand = async (args: string[]): Promise<string> => {
    if (args.length === 0) {
      return '❓ Usage: /calculate <formula_id> [param1=value1 param2=value2 ...]\n\nExamples:\n• /calculate concrete_volume_rect length=10 width=20 depth=0.5\n• /calculate beam_moment_uniform w=1000 l=20\n\nUse /formula <query> to find formula IDs.';
    }
    
    const formulaId = args[0];
    const params: Record<string, number> = {};
    
    // Parse parameters
    for (let i = 1; i < args.length; i++) {
      const [key, value] = args[i].split('=');
      if (key && value) {
        params[key] = parseFloat(value);
      }
    }
    
    try {
      const response = await fetch(`${apiBaseUrl}/economics/formulas/${formulaId}`);
      
      if (!response.ok) {
        return `❌ Formula "${formulaId}" not found.\n\nUse /formula <query> to find available formulas.`;
      }
      
      const formulaData = await response.json();
      const formula = formulaData.formula;
      
      // Execute calculation
      const calcResponse = await fetch(`${apiBaseUrl}/economics/formulas/${formulaId}/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inputs: params }),
      });
      
      if (!calcResponse.ok) {
        const error = await calcResponse.json().catch(() => ({}));
        if (error.detail?.includes('Missing inputs')) {
          const required = formula.inputs?.join(', ') || 'unknown';
          return `❌ Missing parameters for **${formula.name}**

Required: ${required}

Example: /calculate ${formulaId} ${required.split(', ').map((p: string) => `${p}=1`).join(' ')}`;
        }
        return `❌ Calculation error: ${error.detail || calcResponse.statusText}`;
      }
      
      const result = await calcResponse.json();
      
      return `📐 **${result.formula_name}**

Formula: \`${formula.formula}\`

**Inputs:**
${Object.entries(result.inputs).map(([k, v]) => `• ${k} = ${v}`).join('\n')}

**Result: ${result.result} ${result.unit}**`;
    } catch (error) {
      return `❌ Error: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  // ============ DOCUMENT COMMANDS ============
  const handleChromaCommand = async (): Promise<string> => {
    try {
      const [statsRes, embedRes] = await Promise.all([
        fetch(`${apiBaseUrl}/documents/chroma/stats`, {
          headers: { 'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '' }
        }),
        fetch(`${apiBaseUrl}/health/embeddings`)
      ]);
      
      if (!statsRes.ok) {
        return `❌ Failed to get ChromaDB stats`;
      }
      
      const stats = await statsRes.json();
      const embed = embedRes.ok ? await embedRes.json() : null;
      
      const modelStatus = embed?.using_ml 
        ? `🧠 ML Model: ${embed.model} (${embed.dimension}d)`
        : `🔢 Hash Embeddings (fallback)`;
      
      return `📊 **Document Index Status**

Status: ${stats.ready ? '🟢 Ready' : '🔴 Not Ready'}
Indexed Documents: ${stats.total_documents || 0}
Storage: ${stats.mode || 'unknown'}
${modelStatus}

💡 Upload files via chat to index them for search
🔄 Run \`/hydrate\` to sync files with index`;
    } catch (error) {
      return `❌ Error: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  const handleHydrateCommand = async (full: boolean = false): Promise<string> => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/chroma/hydrate?full_scan=${full}`, {
        method: 'POST',
        headers: { 'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '' }
      });
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        return `❌ Hydration failed: ${getUserFriendlyError(response.status, error.detail || response.statusText)}`;
      }
      
      const data = await response.json();
      
      return `🔄 **Hydration Started**

Task ID: ${data.task_id?.slice(0, 8)}...
Mode: ${data.full_scan ? 'Full scan (includes cleanup)' : 'Quick sync'}

The slow worker will:
• Scan upload directory
• Index new files
• ${data.full_scan ? 'Remove orphaned entries' : 'Skip cleanup'}

Check \`/chroma\` in a few minutes for updated stats.

💡 Use \`/task ${data.task_id}\` to check progress`;
    } catch (error) {
      return `❌ Error: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  const handleTaskCommand = async (args: string[]): Promise<string> => {
    if (args.length === 0) {
      return '❓ Usage: /task <task_id>\n\nExample: /task abc123-...\n\nCheck the status of a background task.';
    }
    
    const taskId = args[0];
    
    try {
      const response = await fetch(`${apiBaseUrl}/state/task/${taskId}`, {
        headers: { 'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '' }
      });
      
      if (response.status === 404) {
        return `🔍 Task not found or expired\n\nTask IDs expire after 24 hours.`;
      }
      
      if (!response.ok) {
        return `❌ Failed to get task status`;
      }
      
      const data = await response.json();
      const progress = data.progress || 0;
      const status = data.status || 'unknown';
      const message = data.message || '';
      
      // Create progress bar
      const filled = Math.round(progress / 10);
      const bar = '█'.repeat(filled) + '░'.repeat(10 - filled);
      
      return `📊 **Task Status**

ID: ${taskId.slice(0, 16)}...
Status: ${status.toUpperCase()}
Progress: ${bar} ${progress}%

${message}`;
    } catch (error) {
      return `❌ Error: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  // ============ EXISTING COMMANDS ============
  const handleConnectCommand = async (args: string[]): Promise<string> => {
    const service = args[0]?.toLowerCase();
    
    switch (service) {
      case 'drive':
        try {
          const response = await fetch(`${apiBaseUrl}/drive/auth/url`);
          
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            return `❌ API Error: ${getUserFriendlyError(response.status, errorData.detail || response.statusText)}`;
          }
          
          const data = await response.json();
          
          if (data.auth_url) {
            const width = 500;
            const height = 600;
            const left = window.screenX + (window.outerWidth - width) / 2;
            const top = window.screenY + (window.outerHeight - height) / 2;
            
            window.open(
              data.auth_url,
              'google-oauth',
              `width=${width},height=${height},left=${left},top=${top}`
            );
            
            return '🔐 Opening OneDrive authorization... Please complete the OAuth flow in the popup.';
          }
          return '❌ Failed to get authorization URL';
        } catch (error) {
          return `❌ Failed to initiate OneDrive connection: ${error instanceof Error ? error.message : 'Unknown error'}`;
        }
        
      case 'procore':
        return '🔐 Procore integration - contact admin to configure OAuth.';
        
      case 'slack':
        return '🔐 Slack integration - contact admin to configure OAuth.';
        
      default:
        return `❓ Unknown service: "${service}". Available: drive, procore, slack`;
    }
  };

  const handleProcessCommand = async (args: string[]): Promise<string> => {
    const target = args.join(' ').toLowerCase();
    const token = getAuthToken();
    
    if (target.includes('last invoice') || target.includes('invoice')) {
      try {
        const response = await fetch(`${apiBaseUrl}/documents/process-invoice`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          },
          body: JSON.stringify({ source: 'onedrive', auto_detect: true }),
        });
        
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          return `❌ ${getUserFriendlyError(response.status, error.detail || response.statusText)}`;
        }
        
        const data = await response.json();
        return `📄 Invoice processing started (Task: ${data.task_id?.slice(0, 8) || 'N/A'}...). I'll notify you when complete.`;
      } catch (error) {
        return `❌ Failed to process invoice: ${error instanceof Error ? error.message : 'Network error'}`;
      }
    }
    
    if (target.includes('document')) {
      const docName = args.slice(1).join(' ');
      return `📄 Processing document: "${docName}"...\n\nSearching for matching documents...`;
    }
    
    return '❓ Usage: /process last invoice | /process document <name>';
  };

  const handleSafetyCommand = async (args: string[]): Promise<string> => {
    const subcommand = args[0]?.toLowerCase();
    const token = getAuthToken();
    
    if (subcommand === 'check') {
      const location = args.slice(1).join(' ');
      try {
        const response = await fetch(`${apiBaseUrl}/safety/analyze`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          },
          body: JSON.stringify({ location: location || 'all', type: 'hazard_detection' }),
        });
        
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          return `❌ Safety check failed: ${getUserFriendlyError(response.status, error.detail || response.statusText)}`;
        }
        
        const data = await response.json();
        return `🔍 Safety check completed for "${location || 'all areas'}"\n\nFound ${data.hazards_found || 0} potential hazards.\nReport ID: ${data.report_id}`;
      } catch (error) {
        return `❌ Safety check error: ${error instanceof Error ? error.message : 'Network error'}`;
      }
    }
    
    if (subcommand === 'report') {
      return `📊 **Safety Summary**\n\nUse /safety check <location> to run analysis.`;
    }
    
    return '❓ Usage: /safety check <location> | /safety report';
  };

  const handleSearchCommand = async (args: string[]): Promise<string> => {
    const query = args.join(' ');
    const token = getAuthToken();
    
    if (!query) {
      return '❓ Usage: /search <query>\n\nExamples:\n• /search safety violations\n• /search invoice rebar\n• /search project timeline';
    }
    
    try {
      // Search both documents AND memory (unified search)
      const [docResponse, memoryResponse] = await Promise.all([
        // Document search (ChromaDB)
        fetch(`${apiBaseUrl}/documents/search?query=${encodeURIComponent(query)}&top_k=5`, {
          method: 'GET',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          },
        }).catch(() => null),
        // Memory search (conversation history)
        fetch(`${apiBaseUrl}/agent/v2/memory/search?q=${encodeURIComponent(query)}&limit=5`, {
          headers: {
            'Authorization': token ? `Bearer ${token}` : ''
          },
        }).catch(() => null)
      ]);
      
      // Parse document results
      let docResults: SearchResult[] = [];
      let docTotal = 0;
      if (docResponse?.ok) {
        const docData = await docResponse.json();
        docResults = docData.results || [];
        docTotal = docData.total || 0;
      }
      
      // Parse memory results
      let memoryResults: MemoryResult[] = [];
      if (memoryResponse?.ok) {
        const memoryData = await memoryResponse.json();
        memoryResults = memoryData.results || [];
      }
      
      // Combine and check if any results
      const hasDocResults = docResults.length > 0;
      const hasMemoryResults = memoryResults.length > 0;
      
      if (!hasDocResults && !hasMemoryResults) {
        return `🔍 No results found for "${query}"\n\nTry:\n• Upload documents via chat first\n• Use different keywords\n• Check /chroma/stats for indexed documents`;
      }
      
      // Format document results with highlighting
      let docFormatted = '';
      if (hasDocResults) {
        docFormatted = docResults.map((r: SearchResult) => {
          const name = r.name || 'Unknown';
          const score = Math.round((r.score || 0) * 100);
          const source = r.source || 'upload';
          const highlightedContent = highlightMatch(r.content_preview || 'No preview available', query);
          return `📄 **${name}** (${score}% match) [${source}]\n${highlightedContent}`;
        }).join('\n\n');
      }
      
      // Format memory results with highlighting
      let memoryFormatted = '';
      if (hasMemoryResults) {
        memoryFormatted = memoryResults.map((r: MemoryResult, i: number) => {
          const score = Math.round((r.score || 0) * 100);
          const highlightedContent = highlightMatch(r.content?.substring(0, 200) || 'No content', query);
          return `💬 **Memory ${i + 1}** (${score}% match)\n${highlightedContent}`;
        }).join('\n\n');
      }
      
      // Build combined response
      let response = `🔍 **Search Results for "${query}"**\n\n`;
      
      if (hasDocResults) {
        response += `**📄 Documents (${docTotal} found):**\n\n${docFormatted}\n\n`;
      }
      
      if (hasMemoryResults) {
        response += `**💬 Conversation History (${memoryResults.length} found):**\n\n${memoryFormatted}\n\n`;
      }
      
      response += `---\n💡 *Searches both uploaded documents and conversation history*`
      
      return response;
      
    } catch (error) {
      return `❌ Search error: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  const handleHelpCommand = (): string => {
    return `📚 **Available Commands:**

**📊 Cost & Estimation:**
• \`/cost <item>\` - Search RSMeans (e.g., concrete, pipe)
• \`/formula <query>\` - Find construction formulas
• \`/estimate\` - Building cost estimate (interactive wizard)
• \`/building-types\` - List available building types
• \`/city <name>\` - Get location cost index
• \`/calculate <id> [params]\` - Execute formula calculation

**🔍 Search (Unified):**
• \`/search <query>\` - Search documents AND conversation memory
• \`/chroma\` - Check document index status
• \`/hydrate\` - Sync files with index (runs overnight)
• \`/hydrate full\` - Full scan + cleanup
• \`/task <task_id>\` - Check background task progress
• Upload files via chat to index them

**🛡️ Safety:**
• \`/safety check <location>\` - Run safety analysis
• \`/safety report\` - View safety summary

**⚙️ System:**
• \`/status\` - Check API status
• \`/help\` - Show this help

💡 **Tip:** For complex tasks (code generation, BIM analysis, multi-step workflows), use **🧠 Agent Mode**!`;
  };

  const handleStatusCommand = async (): Promise<string> => {
    try {
      const response = await fetch(`${getApiUrl()}/health/live`);
      const health = await response.json();
      
      return `✅ **System Status: Online**

API: 🟢 Healthy
Version: ${health.version || '1.0.0'}
Uptime: ${health.uptime_seconds || 'N/A'}s`;
    } catch {
      return `❌ **System Status: Offline**

API is not responding. Please check your connection.`;
    }
  };

  const executeCommand = async (parsed: ParsedCommand, isInteractive = false): Promise<string> => {
    switch (parsed.command) {
      // Economics commands
      case 'cost':
        return handleCostCommand(parsed.args);
      case 'formula':
        return handleFormulaCommand(parsed.args);
      case 'estimate':
        return handleEstimateCommand(parsed.args, isInteractive);
      case 'building-types':
        return handleBuildingTypesCommand();
      case 'city':
        return handleCityCommand(parsed.args);
      case 'calculate':
        return handleCalculateCommand(parsed.args);
      
      // Existing commands
      case 'connect':
        return handleConnectCommand(parsed.args);
      case 'process':
        return handleProcessCommand(parsed.args);
      case 'safety':
        return handleSafetyCommand(parsed.args);
      case 'search':
        return handleSearchCommand(parsed.args);
      case 'chroma':
        return handleChromaCommand();
      case 'hydrate':
        return handleHydrateCommand(parsed.args.includes('full'));
      case 'task':
        return handleTaskCommand(parsed.args);
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
    setShowAgentSuggestion({ show: false, reason: '' });
    
    // Handle interactive parameter collection
    if (paramCollection.command === 'estimate') {
      setIsLoading(true);
      
      try {
        let responseText = '';
        
        if (paramCollection.step === 1) {
          // User provided building type
          const buildingType = content.toLowerCase().trim();
          setParamCollection(prev => ({
            ...prev,
            step: 2,
            data: { ...prev.data, buildingType }
          }));
          
          responseText = `✅ Building type: **${buildingType}**

**Step 2:** What is the building size in square feet?

Examples: 50000, 2500, 100000`;
        } else if (paramCollection.step === 2) {
          // User provided size
          const sizeSf = content.trim();
          const sizeNum = parseFloat(sizeSf);
          
          if (isNaN(sizeNum) || sizeNum <= 0) {
            responseText = '❌ Please enter a valid number for square feet.\n\nExamples: 50000, 2500, 100000';
            setIsLoading(false);
            return;
          }
          
          setParamCollection(prev => ({
            ...prev,
            step: 3,
            data: { ...prev.data, sizeSf }
          }));
          
          responseText = `✅ Size: **${sizeNum.toLocaleString()} SF**

**Step 3 (Optional):** What city for location factor?

Type a city name (e.g., Riyadh, New York, Houston) or type **skip** for National Average.`;
        } else if (paramCollection.step === 3) {
          // User provided city or skipped
          const cityInput = content.trim().toLowerCase();
          const city = cityInput === 'skip' ? 'National Average' : content.trim();
          
          // Execute the estimate with collected parameters
          const finalData = {
            buildingType: paramCollection.data.buildingType!,
            sizeSf: paramCollection.data.sizeSf!,
            city
          };
          
          setParamCollection({ command: null, step: 0, data: {} });
          
          // Execute the estimate
          try {
            const estimateResponse = await fetch(`${apiBaseUrl}/economics/estimate/quick?building_type=${finalData.buildingType}&size_sf=${finalData.sizeSf}&city=${encodeURIComponent(city)}`);
            
            if (!estimateResponse.ok) {
              const error = await estimateResponse.json().catch(() => ({}));
              if (error.detail?.includes('Unknown building type')) {
                responseText = `❌ Unknown building type: "${finalData.buildingType}"\n\nUse /building-types to see available options.`;
              } else {
                responseText = `❌ Error: ${error.detail || estimateResponse.statusText}`;
              }
            } else {
              const data = await estimateResponse.json();
              responseText = `🏢 **Building Cost Estimate**

**${data.building_type}**
📏 Size: ${data.size_sf.toLocaleString()} SF
📍 Location: ${data.city}
💵 Cost/SF: $${data.base_cost_per_sf}
📊 Location Factor: ${data.location_factor}

**💰 Total Estimated Cost: $${data.total_cost.toLocaleString()}**

${data.description || ''}`;
            }
          } catch (error) {
            responseText = `❌ Error calculating estimate: ${error instanceof Error ? error.message : 'Network error'}`;
          }
        }
        
        const aiMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: responseText,
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
      return;
    }
    
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
      // Regular chat message - call AI API
      setIsLoading(true);
      
      // Add thinking message
      const thinkingMessageId = uuidv4();
      const thinkingMessage: Message = {
        id: thinkingMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isThinking: true,
      };
      setMessages((prev) => [...prev, thinkingMessage]);
      
      try {
        // Build conversation history for context
        const conversationHistory = messages.map(m => ({
          role: m.role,
          content: m.content
        }));
        
        // Add current user message
        conversationHistory.push({
          role: 'user',
          content: content
        });
        
        // Simulate reasoning steps for better UX
        const reasoningSteps: ReasoningStep[] = [
          { type: 'thought', content: 'Analyzing the user query...', timestamp: new Date().toISOString() },
        ];
        
        // Call chat completions API
        const response = await fetch(`${apiBaseUrl}/chat/completions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': getAuthToken() ? `Bearer ${getAuthToken()}` : '',
          },
          body: JSON.stringify({
            model: 'cerebrum-default',
            messages: conversationHistory,
            temperature: 0.7,
            max_tokens: 2048,
          }),
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.choices && data.choices[0] && data.choices[0].message) {
          // Build reasoning data from response if available
          const finalReasoning: ReasoningData = {
            steps: [
              ...reasoningSteps,
              { type: 'tool', content: 'Chat Completions API', details: 'Called cerebrum-default model' },
              { type: 'data', content: 'Conversation context analyzed', details: `${conversationHistory.length} messages in context` },
              { type: 'decision', content: 'Generated response based on context', details: `Tokens used: ${data.usage?.total_tokens || 'unknown'}` },
            ],
            toolsConsidered: ['Chat Completions API', 'Context Analysis'],
            dataLookedUp: ['Conversation history', 'User query'],
            whyThisAnswer: 'Response generated using the conversation context and the default AI model.',
          };
          
          const aiMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: data.choices[0].message.content,
            timestamp: new Date(),
            reasoning: finalReasoning,
          };
          
          // Replace thinking message with actual response
          setMessages((prev) => prev.map(m => m.id === thinkingMessageId ? aiMessage : m));
        } else {
          throw new Error('Invalid response from AI');
        }
      } catch (error) {
        console.error('Chat API error:', error);
        
        const errorMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: `❌ Error: ${error instanceof Error ? error.message : 'Failed to get AI response'}\n\nTry using a command like /help or switch to Agent Mode.`,
          timestamp: new Date(),
        };
        
        // Replace thinking message with error
        setMessages((prev) => prev.map(m => m.id === thinkingMessageId ? errorMessage : m));
      } finally {
        setIsLoading(false);
      }
    }
  }, [inputValue, attachments, onSendMessage, apiBaseUrl, paramCollection]);

  const addAttachment = useCallback(async (file: File) => {
    const tempAttachment: Attachment = {
      id: uuidv4(),
      name: file.name,
      type: file.type,
      size: file.size,
      status: 'uploading',
      uploadProgress: 0,
    };
    setAttachments((prev) => [...prev, tempAttachment]);
    setIsUploading(true);

    try {
      const result = await uploadChatFile(
        file,
        (percentage) => {
          // Update progress
          setAttachments((prev) =>
            prev.map((a) =>
              a.id === tempAttachment.id
                ? { ...a, uploadProgress: percentage }
                : a
            )
          );
        }
      );

      if (!result.success) {
        // Handle error
        setAttachments((prev) =>
          prev.map((a) =>
            a.id === tempAttachment.id
              ? { ...a, status: 'error', error: result.error }
              : a
          )
        );

        const errorMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: `❌ **File Upload Failed**\n\n📄 **${file.name}**\n\n${result.error || 'Unknown error'}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
        return;
      }

      // Success
      const finalAttachment: Attachment = {
        ...tempAttachment,
        url: result.data?.url,
        status: 'complete',
        uploadProgress: 100,
      };

      setAttachments((prev) =>
        prev.map((a) => (a.id === tempAttachment.id ? finalAttachment : a))
      );

      const successMsg = result.data?.text_extracted
        ? `✅ **File uploaded and indexed!**\n\n📄 **${file.name}**\n📊 Size: ${formatFileSize(file.size)}\n📝 Text extracted: ${result.data.text_length} characters`
        : `✅ **File uploaded!**\n\n📄 **${file.name}**\n📊 Size: ${formatFileSize(file.size)}`;

      const successMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: successMsg,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, successMessage]);
    } catch (error) {
      // Handle unexpected errors
      setAttachments((prev) =>
        prev.map((a) =>
          a.id === tempAttachment.id
            ? {
                ...a,
                status: 'error',
                error: error instanceof Error ? error.message : 'Unknown error',
              }
            : a
        )
      );

      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: `❌ **File Upload Failed**\n\n📄 **${file.name}**\n\n${error instanceof Error ? error.message : 'Network error. Please try again.'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
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

  // ============ WEB SEARCH FUNCTIONALITY ============
  const [isWebSearchEnabled, setIsWebSearchEnabled] = useState(false);

  const toggleWebSearc