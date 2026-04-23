import { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const API_BASE = API_BASE_URL.replace(/\/?$/, '').endsWith('/api/v1')
  ? API_BASE_URL
  : `${API_BASE_URL.replace(/\/?$/, '')}/api/v1`;

function getAuthToken(): string | null {
  return localStorage.getItem('cerebrum_auth_token_v1') || localStorage.getItem('auth_token');
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface GoogleDriveStatus {
  connected: boolean;
  account_email?: string;
  token_expires_at?: string;
  folders_indexed?: number;
  last_sync?: string;
}

export interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime?: string;
  size?: string;
}

export function useGoogleDrive() {
  const [status, setStatus] = useState<GoogleDriveStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/connectors/google-drive/status`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      } else if (res.status === 401) {
        setStatus({ connected: false });
      } else {
        setError('Failed to fetch Google Drive status');
      }
    } catch {
      setStatus({ connected: false });
    } finally {
      setLoading(false);
    }
  }, []);

  const getAuthUrl = useCallback(async (): Promise<string | null> => {
    try {
      const res = await fetch(`${API_BASE}/connectors/google-drive/auth/url`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        return data.auth_url || data.url || null;
      }
    } catch {
      // fall through
    }
    return null;
  }, []);

  const connect = useCallback(async () => {
    setError(null);
    const url = await getAuthUrl();
    if (url) {
      window.location.href = url;
    } else {
      setError('Could not get Google Drive authorization URL');
    }
  }, [getAuthUrl]);

  const disconnect = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/connectors/google-drive/disconnect`, {
        method: 'POST',
        headers: authHeaders(),
      });
      if (res.ok) {
        setStatus({ connected: false });
      } else {
        setError('Failed to disconnect Google Drive');
      }
    } catch {
      setError('Network error disconnecting Google Drive');
    } finally {
      setLoading(false);
    }
  }, []);

  const scanDrive = useCallback(async (folderId?: string): Promise<DriveFile[]> => {
    try {
      const body = folderId ? { folder_id: folderId } : {};
      const res = await fetch(`${API_BASE}/connectors/google-drive/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const data = await res.json();
        return data.files || [];
      }
    } catch {
      // fall through
    }
    return [];
  }, []);

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      fetchStatus();
    }
  }, [fetchStatus]);

  return { status, loading, error, fetchStatus, connect, disconnect, scanDrive };
}
