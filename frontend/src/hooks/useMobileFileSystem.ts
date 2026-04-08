/**
 * useMobileFileSystem Hook
 * 
 * React hook for accessing mobile file system functionality
 * with proper state management and error handling.
 */

import { useState, useEffect, useCallback } from 'react';
import { Filesystem, Directory } from '@capacitor/filesystem';
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

interface FileEntry {
  name: string;
  path: string;
  isDirectory: boolean;
  size: number;
  modified?: string;
  mimeType?: string;
}

interface UseFileSystemReturn {
  files: FileMetadata[];
  currentPath: string;
  entries: FileEntry[];
  isLoading: boolean;
  error: string | null;
  permissions: boolean;
  freeSpace: number;
  totalSpace: number;
  navigateTo: (path: string) => Promise<void>;
  navigateUp: () => void;
  loadFiles: (subPath?: string) => Promise<void>;
  refresh: () => Promise<void>;
  requestPermissions: () => Promise<boolean>;
  readFile: (path: string) => Promise<string | Blob>;
  writeFile: (path: string, data: string) => Promise<void>;
  deleteItem: (path: string, isDirectory: boolean) => Promise<void>;
  createFolder: (path: string) => Promise<void>;
}

// Detect MIME type from filename
function getMimeType(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const mimeTypes: Record<string, string> = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp',
    'mp4': 'video/mp4', 'webm': 'video/webm', 'mov': 'video/quicktime',
    'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'ogg': 'audio/ogg',
    'pdf': 'application/pdf',
    'txt': 'text/plain', 'md': 'text/markdown',
    'json': 'application/json', 'csv': 'text/csv',
    'doc': 'application/msword', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel', 'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  };
  return mimeTypes[ext] || 'application/octet-stream';
}

export function useMobileFileSystem(
  options: UseFileSystemOptions = {}
): UseFileSystemReturn {
  const { folder = 'DOCUMENTS', autoLoad = true } = options;
  
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [currentPath, setCurrentPath] = useState<string>('/');
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState(false);
  const [freeSpace, setFreeSpace] = useState(0);
  const [totalSpace, setTotalSpace] = useState(0);

  // Check permissions on mount
  useEffect(() => {
    checkPermissions();
    loadStorageInfo();
  }, []);

  // Auto-load files if enabled
  useEffect(() => {
    if (autoLoad && permissions) {
      loadFiles();
    }
  }, [folder, permissions, autoLoad]);

  const loadStorageInfo = useCallback(async () => {
    try {
      // Try to get storage info from device
      // This is a best-effort - not all platforms support this
      await Filesystem.getUri({
        directory: Directory.Documents,
        path: ''
      });
      
      // For Android, we can try to get stat of root
      try {
        const stat = await Filesystem.stat({
          directory: Directory.ExternalStorage,
          path: ''
        });
        // These are approximate - actual implementation varies by platform
        setTotalSpace(stat.size || 0);
        setFreeSpace(stat.mtime || 0); // Placeholder - actual free space needs native plugin
      } catch {
        // Fallback: use placeholder values
        setTotalSpace(0);
        setFreeSpace(0);
      }
    } catch {
      setTotalSpace(0);
      setFreeSpace(0);
    }
  }, []);

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

  const navigateTo = useCallback(async (path: string) => {
    setCurrentPath(path);
    await loadDirectory(path);
  }, []);

  const navigateUp = useCallback(() => {
    if (currentPath === '/') return;
    const parent = currentPath.split('/').slice(0, -1).join('/') || '/';
    setCurrentPath(parent);
    loadDirectory(parent);
  }, [currentPath]);

  const loadDirectory = useCallback(async (path: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Convert path to folder/subPath format
      const parts = path.split('/').filter(Boolean);
      const folderName = parts[0] || folder;
      const subPath = parts.slice(1).join('/');
      
      const fileList = await fileSystem.listFiles(folderName as SpecialFolder, subPath || undefined);
      
      // Convert to FileEntry format
      const mappedEntries: FileEntry[] = fileList.map(f => ({
        name: f.name,
        path: `${path === '/' ? '' : path}/${f.name}`,
        isDirectory: f.isDirectory || false,
        size: f.size || 0,
        modified: (f as any).modified?.toISOString?.() || (f as any).mtime?.toISOString?.() || new Date().toISOString(),
        mimeType: f.isDirectory ? undefined : getMimeType(f.name),
      }));
      
      setEntries(mappedEntries);
      setFiles(fileList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files');
      setEntries([]);
      setFiles([]);
    } finally {
      setIsLoading(false);
    }
  }, [folder]);

  const loadFiles = useCallback(async (subPath?: string) => {
    await loadDirectory(subPath || currentPath);
  }, [currentPath, loadDirectory]);

  const refresh = useCallback(async () => {
    await loadDirectory(currentPath);
    await loadStorageInfo();
  }, [currentPath, loadDirectory]);

  const readFile = useCallback(async (path: string) => {
    return fileSystem.readFile(path, folder);
  }, [folder]);

  const writeFile = useCallback(async (path: string, data: string) => {
    await fileSystem.writeFile(path, data, folder);
    await refresh();
  }, [folder, refresh]);

  const deleteItem = useCallback(async (path: string, isDirectory: boolean) => {
    if (isDirectory) {
      if (fileSystem.deleteDirectory) {
        await fileSystem.deleteDirectory(path, folder);
      } else {
        await Filesystem.rmdir({
          directory: Directory.Documents,
          path,
          recursive: true
        });
      }
    } else {
      await fileSystem.deleteFile(path, folder);
    }
    await refresh();
  }, [folder, refresh]);

  const createFolder = useCallback(async (path: string) => {
    await fileSystem.createDirectory(path, folder);
    await refresh();
  }, [folder, refresh]);

  return {
    files,
    currentPath,
    entries,
    isLoading,
    error,
    permissions,
    freeSpace,
    totalSpace,
    navigateTo,
    navigateUp,
    loadFiles,
    refresh,
    requestPermissions,
    readFile,
    writeFile,
    deleteItem,
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
