/**
 * useMobileFileSystem Hook
 * 
 * React hook for accessing mobile file system functionality
 * with proper state management and error handling.
 */

import { useState, useEffect, useCallback } from 'react';
import { 
  fileSystem, 
  backgroundSync,
  type SpecialFolder, 
  type FileMetadata, 
  type SyncConfig,
  type SyncStatus 
} from '@/mobile';

interface UseFileSystemOptions {
  folder?: SpecialFolder;
  autoLoad?: boolean;
}

interface UseFileSystemReturn {
  files: FileMetadata[];
  isLoading: boolean;
  error: string | null;
  permissions: boolean;
  loadFiles: (subPath?: string) => Promise<void>;
  refresh: () => Promise<void>;
  requestPermissions: () => Promise<boolean>;
  readFile: (path: string) => Promise<string | Blob>;
  writeFile: (path: string, data: string) => Promise<void>;
  deleteFile: (path: string) => Promise<void>;
  createFolder: (path: string) => Promise<void>;
}

export function useMobileFileSystem(
  options: UseFileSystemOptions = {}
): UseFileSystemReturn {
  const { folder = 'DOCUMENTS', autoLoad = true } = options;
  
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState(false);

  // Check permissions on mount
  useEffect(() => {
    checkPermissions();
  }, []);

  // Auto-load files if enabled
  useEffect(() => {
    if (autoLoad && permissions) {
      loadFiles();
    }
  }, [folder, permissions, autoLoad]);

  const checkPermissions = useCallback(async () => {
    try {
      const status = await fileSystem.requestPermissions();
      setPermissions(status.read);
      return status.read;
    } catch (err) {
      setError('Failed to check permissions');
      return false;
    }
  }, []);

  const requestPermissions = useCallback(async () => {
    const granted = await checkPermissions();
    if (granted && autoLoad) {
      await loadFiles();
    }
    return granted;
  }, [checkPermissions, autoLoad]);

  const loadFiles = useCallback(async (subPath?: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const fileList = await fileSystem.listFiles(folder, subPath);
      setFiles(fileList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files');
      setFiles([]);
    } finally {
      setIsLoading(false);
    }
  }, [folder]);

  const refresh = useCallback(async () => {
    await loadFiles();
  }, [loadFiles]);

  const readFile = useCallback(async (path: string) => {
    return fileSystem.readFile(path, folder);
  }, [folder]);

  const writeFile = useCallback(async (path: string, data: string) => {
    await fileSystem.writeFile(path, data, folder);
    await refresh();
  }, [folder, refresh]);

  const deleteFile = useCallback(async (path: string) => {
    await fileSystem.deleteFile(path, folder);
    await refresh();
  }, [folder, refresh]);

  const createFolder = useCallback(async (path: string) => {
    await fileSystem.createDirectory(path, folder);
    await refresh();
  }, [folder, refresh]);

  return {
    files,
    isLoading,
    error,
    permissions,
    loadFiles,
    refresh,
    requestPermissions,
    readFile,
    writeFile,
    deleteFile,
    createFolder,
  };
}

// Hook for background sync
interface UseBackgroundSyncReturn {
  status: SyncStatus;
  isMonitoring: boolean;
  startMonitoring: (config: SyncConfig) => Promise<string>;
  stopMonitoring: (folderId?: string) => Promise<void>;
  syncNow: () => Promise<void>;
}

export function useBackgroundSync(): UseBackgroundSyncReturn {
  const [status, setStatus] = useState<SyncStatus>({
    isRunning: false,
    folder: null,
    filesScanned: 0,
    filesUploaded: 0,
    filesFailed: 0,
    lastSyncTime: null,
    nextSyncTime: null,
    errors: [],
  });
  const [isMonitoring, setIsMonitoring] = useState(false);

  useEffect(() => {
    // Initialize and set up status listener
    backgroundSync.initialize();
    
    const interval = setInterval(() => {
      const currentStatus = backgroundSync.getStatus();
      setStatus(currentStatus);
      setIsMonitoring(currentStatus.isRunning);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const startMonitoring = useCallback(async (config: SyncConfig) => {
    const folderId = await backgroundSync.startMonitoring(config);
    setIsMonitoring(true);
    return folderId;
  }, []);

  const stopMonitoring = useCallback(async (folderId?: string) => {
    await backgroundSync.stopMonitoring(folderId);
    setIsMonitoring(false);
  }, []);

  const syncNow = useCallback(async () => {
    await backgroundSync.syncNow();
  }, []);

  return {
    status,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    syncNow,
  };
}
