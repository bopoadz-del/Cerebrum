import { QueryClient } from '@tanstack/react-query';

// Create a client with default options
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Time until data is considered stale (5 minutes)
      staleTime: 1000 * 60 * 5,
      // Time until inactive queries are removed from cache (10 minutes)
      gcTime: 1000 * 60 * 10,
      // Retry failed queries 3 times
      retry: 3,
      // Delay between retries
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      // Refetch on window focus
      refetchOnWindowFocus: true,
      // Refetch on reconnect
      refetchOnReconnect: true,
      // Don't refetch on mount if data exists
      refetchOnMount: 'always',
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
});

// Query keys for cache management
export const queryKeys = {
  // Auth
  auth: {
    user: ['auth', 'user'] as const,
    session: ['auth', 'session'] as const,
  },
  // Dashboard
  dashboard: {
    stats: ['dashboard', 'stats'] as const,
    activities: ['dashboard', 'activities'] as const,
  },
  // Registry
  registry: {
    services: ['registry', 'services'] as const,
    service: (id: string) => ['registry', 'services', id] as const,
  },
  // Learning
  learning: {
    models: ['learning', 'models'] as const,
    model: (id: string) => ['learning', 'models', id] as const,
    experiments: ['learning', 'experiments'] as const,
  },
  // Tasks
  tasks: {
    list: ['tasks'] as const,
    detail: (id: string) => ['tasks', id] as const,
  },
  // Documents
  documents: {
    list: ['documents'] as const,
    detail: (id: string) => ['documents', id] as const,
  },
  // Audit
  audit: {
    logs: ['audit', 'logs'] as const,
  },
  // Users
  users: {
    list: ['users'] as const,
    detail: (id: string) => ['users', id] as const,
  },
  // Capacity
  capacity: ['capacity'] as const,
  // Edge Devices
  edgeDevices: {
    list: ['edge-devices'] as const,
    detail: (id: string) => ['edge-devices', id] as const,
  },
  // BIM
  bim: {
    models: ['bim', 'models'] as const,
    layers: (modelId: string) => ['bim', 'models', modelId, 'layers'] as const,
  },
};

// Prefetch helper
export const prefetchQuery = async <T,>(
  queryKey: readonly unknown[],
  queryFn: () => Promise<T>
): Promise<void> => {
  await queryClient.prefetchQuery({
    queryKey,
    queryFn,
    staleTime: 1000 * 60 * 5,
  });
};

// Invalidate queries helper
export const invalidateQueries = async (
  queryKey: readonly unknown[]
): Promise<void> => {
  await queryClient.invalidateQueries({ queryKey });
};

// Optimistic update helper
export const optimisticUpdate = <T,>(
  queryKey: readonly unknown[],
  updater: (oldData: T | undefined) => T
): void => {
  queryClient.setQueryData(queryKey, updater);
};

export default queryClient;
