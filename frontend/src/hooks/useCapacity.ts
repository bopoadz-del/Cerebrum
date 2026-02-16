import { useState, useEffect, useRef, useCallback } from 'react';

interface CapacityData {
  current: number;
  limit: number;
  percentage: number;
  status: 'healthy' | 'warning' | 'critical';
  lastUpdated: Date;
}

interface UseCapacityOptions {
  interval?: number; // Polling interval in milliseconds
  enabled?: boolean;
  onError?: (error: Error) => void;
  onThresholdReached?: (capacity: CapacityData) => void;
  warningThreshold?: number; // Percentage threshold for warning
  criticalThreshold?: number; // Percentage threshold for critical
}

const DEFAULT_OPTIONS: Required<UseCapacityOptions> = {
  interval: 5000, // 5 seconds default
  enabled: true,
  onError: () => {},
  onThresholdReached: () => {},
  warningThreshold: 70,
  criticalThreshold: 90,
};

/**
 * Hook for polling capacity data from the server
 * @param options - Configuration options
 * @returns Capacity data and control functions
 */
export const useCapacity = (options: UseCapacityOptions = {}) => {
  const {
    interval,
    enabled,
    onError,
    onThresholdReached,
    warningThreshold,
    criticalThreshold,
  } = { ...DEFAULT_OPTIONS, ...options };

  const [capacity, setCapacity] = useState<CapacityData>({
    current: 0,
    limit: 100,
    percentage: 0,
    status: 'healthy',
    lastUpdated: new Date(),
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const previousStatusRef = useRef<CapacityData['status']>('healthy');

  // Determine status based on percentage
  const getStatus = useCallback(
    (percentage: number): CapacityData['status'] => {
      if (percentage >= criticalThreshold) return 'critical';
      if (percentage >= warningThreshold) return 'warning';
      return 'healthy';
    },
    [warningThreshold, criticalThreshold]
  );

  // Fetch capacity data
  const fetchCapacity = useCallback(async () => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/capacity', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch capacity: ${response.statusText}`);
      }

      const data = await response.json();

      const percentage = Math.round((data.current / data.limit) * 100);
      const status = getStatus(percentage);

      const newCapacity: CapacityData = {
        current: data.current,
        limit: data.limit,
        percentage,
        status,
        lastUpdated: new Date(),
      };

      setCapacity(newCapacity);

      // Check if threshold was reached
      if (
        status !== 'healthy' &&
        previousStatusRef.current === 'healthy'
      ) {
        onThresholdReached(newCapacity);
      }

      previousStatusRef.current = status;
    } catch (err) {
      // Don't update error state if request was aborted
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }

      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      onError(error);
    } finally {
      setIsLoading(false);
    }
  }, [getStatus, onError, onThresholdReached]);

  // Start polling
  const startPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Initial fetch
    fetchCapacity();

    // Set up polling
    intervalRef.current = setInterval(fetchCapacity, interval);
  }, [fetchCapacity, interval]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  // Manual refresh
  const refresh = useCallback(async () => {
    await fetchCapacity();
  }, [fetchCapacity]);

  // Set up polling effect
  useEffect(() => {
    if (enabled) {
      startPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, startPolling, stopPolling]);

  return {
    capacity,
    isLoading,
    error,
    refresh,
    startPolling,
    stopPolling,
  };
};

/**
 * Hook for capacity with automatic alert notifications
 */
export const useCapacityWithAlerts = (options: UseCapacityOptions = {}) => {
  const { capacity, ...rest } = useCapacity({
    ...options,
    onThresholdReached: (cap) => {
      // Show browser notification if permitted
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Capacity Alert', {
          body: `Capacity reached ${cap.percentage}%. Current: ${cap.current}/${cap.limit}`,
          icon: '/favicon.ico',
        });
      }

      // Call original handler
      options.onThresholdReached?.(cap);
    },
  });

  return { capacity, ...rest };
};

/**
 * Hook for multiple capacity metrics
 */
export const useMultiCapacity = (
  endpoints: string[],
  options: UseCapacityOptions = {}
) => {
  const [capacities, setCapacities] = useState<Record<string, CapacityData>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const { interval, enabled } = { ...DEFAULT_OPTIONS, ...options };

  const fetchAllCapacities = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    setIsLoading(true);
    setError(null);

    try {
      const results = await Promise.all(
        endpoints.map(async (endpoint) => {
          const response = await fetch(endpoint, { signal });
          if (!response.ok) {
            throw new Error(`Failed to fetch ${endpoint}: ${response.statusText}`);
          }
          return response.json();
        })
      );

      const newCapacities: Record<string, CapacityData> = {};
      results.forEach((data, index) => {
        const key = endpoints[index];
        const percentage = Math.round((data.current / data.limit) * 100);
        newCapacities[key] = {
          current: data.current,
          limit: data.limit,
          percentage,
          status:
            percentage >= 90 ? 'critical' : percentage >= 70 ? 'warning' : 'healthy',
          lastUpdated: new Date(),
        };
      });

      setCapacities(newCapacities);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
    } finally {
      setIsLoading(false);
    }
  }, [endpoints]);

  useEffect(() => {
    if (enabled) {
      fetchAllCapacities();
      intervalRef.current = setInterval(fetchAllCapacities, interval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [enabled, interval, fetchAllCapacities]);

  return {
    capacities,
    isLoading,
    error,
    refresh: fetchAllCapacities,
  };
};

export default useCapacity;
