import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Brain, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from '@/components/ui/Toast';

interface SmartContextState {
  enabled: boolean;
  loading: boolean;
  error: string | null;
}

interface ContextPayload {
  documentIds: string[];
  projectId: string;
  userPreferences: Record<string, unknown>;
}

export const SmartContextToggle: React.FC = () => {
  const [state, setState] = useState<SmartContextState>({
    enabled: false,
    loading: false,
    error: null,
  });
  
  // Use ref to store AbortController so it persists across renders
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  }, []);

  const activateContext = useCallback(async () => {
    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new AbortController
    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      // Simulate API call to activate smart context
      const response = await fetch('/api/v1/context/activate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          documentIds: [],
          projectId: 'current-project',
          userPreferences: {},
        } as ContextPayload),
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
      });

      toast.success('Smart Context activated successfully');
      return data;
    } catch (error) {
      // Don't update state if request was aborted
      if (error instanceof DOMException && error.name === 'AbortError') {
        console.log('Context activation aborted');
        return;
      }

      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      setState({
        enabled: false,
        loading: false,
        error: errorMessage,
      });

      toast.error(`Failed to activate Smart Context: ${errorMessage}`);
      throw error;
    }
  }, []);

  const deactivateContext = useCallback(async () => {
    // Cancel any existing request
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
        },
        signal,
      });

      if (!response.ok) {
        throw new Error(`Failed to deactivate context: ${response.statusText}`);
      }

      setState({
        enabled: false,
        loading: false,
        error: null,
      });

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
  }, []);

  const handleToggle = useCallback(async () => {
    if (state.loading) {
      // Cancel ongoing operation
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
      return 'Smart Context On';
    }
    return 'Smart Context';
  };

  return (
    <button
      onClick={handleToggle}
      disabled={false} // Always allow clicking to cancel
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-all duration-200',
        getButtonStyles(),
        state.loading && 'cursor-pointer' // Allow clicking to cancel
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
  }>({
    enabled: false,
    documents: [],
    projectId: null,
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

  return {
    context,
    addDocument,
    removeDocument,
    clearDocuments,
    setProject,
  };
};

export default SmartContextToggle;
