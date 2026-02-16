import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api';

interface DriveAuthStatus {
  authenticated: boolean;
}

interface AuthUrlResponse {
  auth_url: string;
  state: string;
}

interface SyncOptions {
  full_resync?: boolean;
  folder_id?: string;
}

interface SyncResult {
  task_id: string;
  status: string;
  message: string;
}

interface SyncStatus {
  status: 'pending' | 'running' | 'completed' | 'failed';
  error_message?: string;
}

interface DriveStats {
  total_syncs: number;
  successful_syncs: number;
  failed_syncs: number;
  total_files_synced: number;
  total_folders_synced: number;
  recent_tasks: Array<{
    task_id: string;
    status: string;
    started_at: string;
    completed_at?: string;
    files_synced: number;
    folders_synced: number;
    errors: string[];
  }>;
}

interface ConflictData {
  conflicts: Array<{
    conflict_id: string;
    conflict_type: string;
    local_version?: { name: string; modified_time: string };
    remote_version?: { name: string; modified_time: string };
    detected_at: string;
    resolved: boolean;
  }>;
}

interface DriveFile {
  id: string;
  name: string;
  mime_type: string;
  size?: number;
  modified_time?: string;
  is_folder: boolean;
  parents: string[];
  web_view_link?: string;
}

interface FolderTreeResponse {
  id: string;
  name: string;
  children: Array<Record<string, unknown>>;
  path: string[];
}

export const useDriveAPI = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const getAuthUrl = useCallback(async (): Promise<AuthUrlResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<AuthUrlResponse>('/drive/auth/url');
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to get auth URL');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const exchangeCode = useCallback(async (code: string, state: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      await apiClient.post('/drive/auth/callback', { code, state });
      setIsAuthenticated(true);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to exchange code');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const checkAuth = useCallback(async (): Promise<DriveAuthStatus> => {
    setIsLoading(true);
    try {
      const response = await apiClient.get<DriveAuthStatus>('/drive/health');
      setIsAuthenticated(response.authenticated);
      return response;
    } catch (err) {
      setIsAuthenticated(false);
      return { authenticated: false };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const revokeAuth = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      await apiClient.post('/drive/auth/revoke', {});
      setIsAuthenticated(false);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to revoke auth');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const startSync = useCallback(async (options: SyncOptions): Promise<SyncResult> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.post<SyncResult>('/drive/sync', {
        folder_id: options.folder_id,
        full_resync: options.full_resync || false,
        auto_resolve_conflicts: true,
      });
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to start sync');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getSyncStatus = useCallback(async (taskId: string): Promise<SyncStatus> => {
    try {
      const response = await apiClient.get<SyncStatus>(`/drive/sync/status/${taskId}`);
      return response;
    } catch (err) {
      return { status: 'failed', error_message: 'Failed to get sync status' };
    }
  }, []);

  const getUserStats = useCallback(async (): Promise<DriveStats> => {
    try {
      const response = await apiClient.get<DriveStats>('/drive/user/stats');
      return response;
    } catch (err) {
      return {
        total_syncs: 0,
        successful_syncs: 0,
        failed_syncs: 0,
        total_files_synced: 0,
        total_folders_synced: 0,
        recent_tasks: [],
      };
    }
  }, []);

  const getConflicts = useCallback(async (): Promise<ConflictData> => {
    try {
      const response = await apiClient.get<ConflictData>('/drive/conflicts');
      return response;
    } catch (err) {
      return { conflicts: [] };
    }
  }, []);

  const scheduleSync = useCallback(async (intervalMinutes: number): Promise<void> => {
    setIsLoading(true);
    try {
      await apiClient.post('/drive/sync/schedule', {}, { params: { interval_minutes: intervalMinutes } });
    } finally {
      setIsLoading(false);
    }
  }, []);

  const listFiles = useCallback(async (folderId?: string): Promise<DriveFile[]> => {
    try {
      const response = await apiClient.get<DriveFile[]>('/drive/files', {
        params: { folder_id: folderId || 'root' },
      });
      return response;
    } catch (err) {
      return [];
    }
  }, []);

  const searchFiles = useCallback(async (query: string): Promise<DriveFile[]> => {
    try {
      const response = await apiClient.get<DriveFile[]>('/drive/files', {
        params: { query },
      });
      return response;
    } catch (err) {
      return [];
    }
  }, []);

  const getFolderTree = useCallback(async (folderId: string): Promise<FolderTreeResponse> => {
    try {
      const response = await apiClient.get<FolderTreeResponse>('/drive/folders/tree', {
        params: { folder_id: folderId },
      });
      return response;
    } catch (err) {
      return { id: folderId, name: 'My Drive', children: [], path: ['My Drive'] };
    }
  }, []);

  return {
    getAuthUrl,
    exchangeCode,
    checkAuth,
    revokeAuth,
    startSync,
    getSyncStatus,
    getUserStats,
    getConflicts,
    scheduleSync,
    listFiles,
    searchFiles,
    getFolderTree,
    isLoading,
    isAuthenticated,
    error,
  };
};

export default useDriveAPI;
