import { useState, useEffect, useCallback } from 'react';

// Match the existing Project type EXACTLY
export interface Project {
  id: string;
  name: string;
  file_count: number;
  status: string;
}

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [backendAvailable, setBackendAvailable] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [connectionError, _setConnectionError] = useState<string | null>(null);
  const [indexingStatus, _setIndexingStatus] = useState(null);
  const [scanResults, _setScanResults] = useState(null);

  const refreshProjects = useCallback(async () => {
    setLoading(true);
    try {
      setProjects([]);
      setBackendAvailable(true);
    } catch (error) {
      console.error('Error:', error);
      setBackendAvailable(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const connectDrive = async () => { setIsConnected(false); };
  const disconnectDrive = async () => { setIsConnected(false); };
  const scanDrive = async () => { setScanning(false); };

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  return {
    projects,
    loading,
    backendAvailable,
    refreshProjects,
    getProjectFiles: async () => [],
    scanning,
    connectionError,
    indexingStatus,
    scanResults,
    isConnected,
    connectDrive,
    disconnectDrive,
    scanDrive
  };
}
