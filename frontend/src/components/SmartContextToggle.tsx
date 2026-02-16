import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Brain, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from '@/components/ui/Toast';

interface SmartContextState {
  enabled: boolean;
  loading: boolean;
  error: string | null;
  sessionToken: string | null;
  capacity: number;
}

interface ContextPayload {
  documentIds: string[];
  projectId: string;
  userPreferences: Record<string, unknown>;
}

interface SmartContextToggleProps {
  sessionToken?: string;
  onToggle?: (enabled: boolean) => void;
  onSessionChange?: (token: string | null) => void;
}

// Storage key for local persistence
const STORAGE_KEY = 'cerebrum_smart_context';

export const SmartContextToggle: React.FC<SmartContextToggleProps> = ({
  sessionToken: externalSessionToken,
  onToggle,
  onSessionChange,
}) => {
  const [state, setState] = useState<SmartContextState>({
    enabled: false,
    loading: false,
    error: null,
    sessionToken: externalSessionToken || null,
    capacity: 0,
  });
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load persisted state on mount
  useEffect(() => {
    if (!externalSessionToken) {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed.enabled && parsed.sessionToken) {
            setState(prev => ({
              ...prev,
              enabled: parsed.enabled,
              sessionToken: parsed.sessionToken,
            }));
          }
        } catch (e) {
          console.warn('Failed to parse stored smart context state:', e);
        }
      }
    }
  }, [externalSessionToken]);

  // Persist state changes
  useEffect(() => {
    if (!externalSessionToken) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        enabled: state.enabled,
        sessionToken: state.sessionToken,
      }));
    }
  }, [state.enabled, state.sessionToken, externalSessionToken]);

  // Update external session token if provided
  useEffect(() => {
    if (externalSessionToken !== undefined) {
      setState(prev => ({ ...prev, sessionToken: externalSessionToken }));
    }
  }, [externalSessionToken]);

  // Notify parent of session changes
  useEffect(() => {
    onSessionChange?.(state.sessionToken);
  }, [state.sessionToken, onSessionChange]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Start polling capacity when session is active
  useEffect(() => {
    if (state.enabled && state.sessionToken) {
      pollIntervalRef.current = setInterval(() => {
        fetchCapacity();
      }, 30000); // Poll every 30 seconds
      
      // Initial capacity fetch
      fetchCapacity();
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [state.enabled, state.sessionToken]);

  const fetchCapacity = useCallback(async () => {
    if (!state.sessionToken) return;
    
    try {
      const response = await fetch(`/api/v1/sessions/${state.sessionToken}/capacity`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setState(prev => ({ ...prev, capacity: data.capacity_percent }));
      }
    } catch (error) {
      // Silently fail - don't spam user with capacity errors
      console.warn('Failed to fetch capacity:', error);
    }
  }, [state.sessionToken]);

  const createSession = useCallback(async () => {
    const response = await fetch('/api/v1/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
      },
      body: JSON.stringify({
        title: 'Smart Context Session',
        ttl_hours: 24,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.session_token;
  }, []);

  const activateContext = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;
    
    setState((prev) => ({ ...prev, loading: true, error: null }));
    
    try {
      // Create session if we don't have one
      let token = state.sessionToken;
      if (!token) {
        token = await createSession();
        setState(prev => ({ ...prev, sessionToken: token }));
      }
      
      // Call activate endpoint
      const response = await fetch('/api/v1/context/activate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          documentIds: [],
          projectId: 'current-project',
          userPreferences: {},
          session_token: token,
        } as ContextPayload & { session_token: string }),
        signal,
      });
      
      if (!response.ok) {
        throw new Error(`Failed to activate context: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      setState({
        enabled: true,
        loading: false,
        error: null,
        sessionToken: token,
        capacity: data.capacity_percent || 0,
      });
      
      onToggle?.(true);
      toast.success('Smart Context activated successfully');
      return data;
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        console.log('Context activation aborted');
        return;
      }
      
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      setState((prev) => ({
        ...prev,
        enabled: false,
        loading: false,
        error: errorMessage,
      }));
      
      toast.error(`Failed to activate Smart Context: ${errorMessage}`);
      throw error;
    }
  }, [createSession, onToggle, state.sessionToken]);
  
  const deactivateContext = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;
    
    setState((prev) => ({ ...prev, loading: true, error: null }));
    
    try {
      const response = await fetch('/api/v1/context/deactivate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        signal,
      });
      
      if (!response.ok) {
        throw new Error(`Failed to deactivate context: ${response.statusText}`);
      }
      
      setState((prev) => ({
        ...prev,
        enabled: false,
        loading: false,
        error: null,
        capacity: 0,
      }));
      
      onToggle?.(false);
      toast.info('Smart Context deactivated');
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        console.log('Context deactivation aborted');
        return;
      }
      
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      setState((prev) => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));
      
      toast.error(`Failed to deactivate Smart Context: ${errorMessage}`);
    }
  }, [onToggle]);
  
  const handleToggle = useCallback(async () => {
    if (state.loading) {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setState((prev) => ({ ...prev, loading: false }));
      return;
    }
    
    if (state.enabled) {
      await deactivateContext();
    } else {
      await activateContext();
    }
  }, [state.enabled, state.loading, activateContext, deactivateContext]);
  
  const getButtonStyles = () => {
    if (state.loading) {
      return 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 border-yellow-300 dark:border-yellow-700';
    }
    if (state.error) {
      return 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-300 dark:border-red-700';
    }
    if (state.enabled) {
      return 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-300 dark:border-green-700';
    }
    return 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-700';
  };
  
  const getIcon = () => {
    if (state.loading) {
      return <Loader2 size={18} className="animate-spin" />;
    }
    if (state.error) {
      return <AlertCircle size={18} />;
    }
    if (state.enabled) {
      return <CheckCircle2 size={18} />;
    }
    return <Brain size={18} />;
  };
  
  const getLabel = () => {
    if (state.loading) {
      return state.enabled ? 'Deactivating...' : 'Activating...';
    }
    if (state.error) {
      return 'Error';
    }
    if (state.enabled) {
      return state.capacity > 0 ? `Smart Context (${state.capacity}%)` : 'Smart Context On';
    }
    return 'Smart Context';
  };
  
  return (
    <button
      onClick={handleToggle}
      disabled={false}
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-all duration-200',
        getButtonStyles(),
        state.loading && 'cursor-pointer'
      )}
      title={state.error || (state.enabled ? 'Click to deactivate' : 'Click to activate')}
      aria-pressed={state.enabled}
      aria-busy={state.loading}
    >
      {getIcon()}
      <span className="hidden sm:inline">{getLabel()}</span>
      <span className="sm:hidden">
        {state.loading ? '...' : state.enabled ? 'On' : 'Off'}
      </span>
    </button>
  );
};

// Hook for using smart context in other components
export const useSmartContext = () => {
  const [context, setContext] = useState<{
    enabled: boolean;
    documents: string[];
    projectId: string | null;
    sessionToken: string | null;
    capacity: number;
  }>({
    enabled: false,
    documents: [],
    projectId: null,
    sessionToken: null,
    capacity: 0,
  });

  const addDocument = useCallback((documentId: string) => {
    setContext((prev) => ({
      ...prev,
      documents: [...prev.documents, documentId],
    }));
  }, []);

  const removeDocument = useCallback((documentId: string) => {
    setContext((prev) => ({
      ...prev,
      documents: prev.documents.filter((id) => id !== documentId),
    }));
  }, []);

  const clearDocuments = useCallback(() => {
    setContext((prev) => ({
      ...prev,
      documents: [],
    }));
  }, []);

  const setProject = useCallback((projectId: string) => {
    setContext((prev) => ({
      ...prev,
      projectId,
    }));
  }, []);

  const setSessionToken = useCallback((token: string | null) => {
    setContext((prev) => ({
      ...prev,
      sessionToken: token,
    }));
  }, []);

  return {
    context,
    addDocument,
    removeDocument,
    clearDocuments,
    setProject,
    setSessionToken,
  };
};

export default SmartContextToggle;
