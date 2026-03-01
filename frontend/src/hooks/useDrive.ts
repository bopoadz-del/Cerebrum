import { useState, useEffect, useCallback } from 'react';
import { useAuth, STORAGE_KEYS } from '@/context/AuthContext';

const RAW_API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
// Ensure URL has /api/v1 prefix
const API_URL = RAW_API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? RAW_API_URL 
  : `${RAW_API_URL.replace(/\/?$/, '')}/api/v1`;

// Google OAuth Configuration
// These are public client IDs - safe to expose in frontend
const GOOGLE_CLIENT_ID = '382554705937-v3s8kpvl7h0em2aekud73fro8rig0cvu.apps.googleusercontent.com';
const GOOGLE_REDIRECT_URI = `https://cerebrum-api.onrender.com/api/v1/connectors/google-drive/callback`;

// Storage keys - versioned for compatibility across deployments
const DRIVE_STORAGE_KEYS = {
  CONNECTED: 'cerebrum_gdrive_connected_v1',
  OAUTH_STATE: 'cerebrum_gdrive_oauth_state_v1',
  LAST_CONNECTED_AT: 'cerebrum_gdrive_last_connected_v1',
} as const;

// Legacy keys for migration
const DRIVE_LEGACY_KEYS = {
  CONNECTED: 'google_drive_connected',
  OAUTH_STATE: 'google_oauth_state',
} as const;

// Migrate legacy storage data to new keys
function migrateLegacyDriveData(): { connected: boolean } {
  let connected = localStorage.getItem(DRIVE_STORAGE_KEYS.CONNECTED);
  let oauthState = localStorage.getItem(DRIVE_STORAGE_KEYS.OAUTH_STATE);
  
  // Check for legacy keys if new keys not found
  if (!connected) {
    connected = localStorage.getItem(DRIVE_LEGACY_KEYS.CONNECTED);
    if (connected) {
      localStorage.setItem(DRIVE_STORAGE_KEYS.CONNECTED, connected);
      console.log('[Drive] Migrated legacy connection state');
    }
  }
  
  if (!oauthState) {
    oauthState = localStorage.getItem(DRIVE_LEGACY_KEYS.OAUTH_STATE);
    if (oauthState) {
      localStorage.setItem(DRIVE_STORAGE_KEYS.OAUTH_STATE, oauthState);
      console.log('[Drive] Migrated legacy OAuth state');
    }
  }
  
  // Clean up legacy keys after migration
  if (connected && localStorage.getItem(DRIVE_LEGACY_KEYS.CONNECTED)) {
    localStorage.removeItem(DRIVE_LEGACY_KEYS.CONNECTED);
    localStorage.removeItem(DRIVE_LEGACY_KEYS.OAUTH_STATE);
  }
  
  return { connected: connected === 'true' };
}

export interface Project {
  id: string;
  name: string;
  file_count: number;
  status: string;
  updated_at?: string;
}

export interface SearchResult {
  id: string;
  score: number;
  metadata: {
    name: string;
    project: string;
    content_preview?: string;
    [key: string]: any;
  };
}

// Demo projects for when backend is unavailable
const DEMO_PROJECTS: Project[] = [
  { id: 'demo_1', name: 'Q4 Financial Analysis', file_count: 12, status: 'active' },
  { id: 'demo_2', name: 'Construction Project A', file_count: 45, status: 'active' },
  { id: 'demo_3', name: 'Marketing Campaign', file_count: 8, status: 'draft' },
];

export function useDrive() {
  const { user, refreshAuthToken } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [scanning, setScanning] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Get auth token from localStorage using the same key as AuthContext
  const getAuthToken = () => localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN) || '';

  const getHeaders = () => ({
    'Authorization': `Bearer ${getAuthToken()}`,
    'Content-Type': 'application/json'
  });

  // Build Google OAuth URL directly
  const buildGoogleAuthUrl = (state?: string) => {
    const nonce = state || user?.id || "e727e727-d547-4d96-b070-2294980e5d85";
    localStorage.setItem(DRIVE_STORAGE_KEYS.OAUTH_STATE, nonce);
    
    const scopes = [
      'https://www.googleapis.com/auth/drive.readonly',
      'https://www.googleapis.com/auth/drive.metadata.readonly'
    ];
    
    return (
      'https://accounts.google.com/o/oauth2/v2/auth' +
      `?client_id=${GOOGLE_CLIENT_ID}` +
      `&redirect_uri=${encodeURIComponent(GOOGLE_REDIRECT_URI)}` +
      '&response_type=code' +
      `&scope=${encodeURIComponent(scopes.join(' '))}` +
      `&state=${nonce}` +
      '&access_type=offline' +
      '&prompt=consent'
    );
  };

  // Check backend health and connection status
  const checkConnection = useCallback(async () => {
    console.log('[Drive] Checking connection...');
    try {
      setLoading(true);
      setConnectionError(null);
      
      const token = getAuthToken();
      console.log('[Drive] Token present:', !!token);
      
      const res = await fetch(`${API_URL}/connectors/google-drive/status`, { 
        headers: getHeaders(),
        // Short timeout to quickly detect backend issues
        signal: AbortSignal.timeout(5000)
      });
      
      console.log('[Drive] Status response:', { status: res.status, ok: res.ok });
      
      if (res.ok) {
        const data = await res.json();
        console.log('[Drive] Status data:', data);
        
        // Only update connected state if explicitly false
        // If user was connected before, keep them connected unless explicitly disconnected
        const wasConnected = localStorage.getItem(DRIVE_STORAGE_KEYS.CONNECTED) === 'true';
        
        if (data.connected) {
          setIsConnected(true);
          setBackendAvailable(true);
          // Store connection timestamp
          localStorage.setItem(DRIVE_STORAGE_KEYS.CONNECTED, 'true');
          localStorage.setItem(DRIVE_STORAGE_KEYS.LAST_CONNECTED_AT, String(Date.now()));
          refreshProjects();
        } else if (!wasConnected) {
          // Only mark as disconnected if we weren't connected before
          // This prevents flickering during token refresh
          setIsConnected(false);
          setBackendAvailable(true);
        } else {
          // Was connected, still have token, backend says not connected
          // This might be a temporary state - keep showing as connected
          console.log('[Drive] Was connected, keeping state');
          setIsConnected(true);
          setBackendAvailable(true);
        }
      } else if (res.status === 404) {
        // Endpoints not deployed
        setBackendAvailable(false);
        setConnectionError('Backend not deployed - using demo mode');
        // Try to check if we have a stored connection (fallback only)
        const storedConnected = localStorage.getItem(DRIVE_STORAGE_KEYS.CONNECTED);
        const lastConnected = localStorage.getItem(DRIVE_STORAGE_KEYS.LAST_CONNECTED_AT);
        // Only use cached state if connected within last 24 hours
        if (storedConnected && lastConnected) {
          const lastConnectedMs = parseInt(lastConnected, 10);
          const oneDayMs = 24 * 60 * 60 * 1000;
          if (Date.now() - lastConnectedMs < oneDayMs) {
            setIsConnected(true);
            setProjects(DEMO_PROJECTS);
          }
        }
      } else if (res.status === 401) {
        // Token expired - try refresh
        const refreshed = await refreshAuthToken();
        if (refreshed) {
          // Retry the check
          await checkConnection();
          return;
        } else {
          setConnectionError('Session expired - please login again');
          setIsConnected(false);
        }
      } else {
        setBackendAvailable(false);
        setConnectionError(`Backend error: ${res.status}`);
      }
    } catch (e: any) {
      console.log('Backend unavailable:', e.message);
      setBackendAvailable(false);
      setConnectionError('Cannot reach backend - check internet or try again later');
      
      // Check for stored connection (fallback only)
      const storedConnected = localStorage.getItem(DRIVE_STORAGE_KEYS.CONNECTED);
      const lastConnected = localStorage.getItem(DRIVE_STORAGE_KEYS.LAST_CONNECTED_AT);
      if (storedConnected && lastConnected) {
        const lastConnectedMs = parseInt(lastConnected, 10);
        const oneDayMs = 24 * 60 * 60 * 1000;
        if (Date.now() - lastConnectedMs < oneDayMs) {
          setIsConnected(true);
          setProjects(DEMO_PROJECTS);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [refreshAuthToken]);

  // Check connection on mount
  useEffect(() => {
    // Migrate legacy data first
    migrateLegacyDriveData();
    
    if (user) {
      checkConnection();
    } else {
      // Clear connection state when user logs out
      setIsConnected(false);
      setProjects([]);
    }
  }, [user, checkConnection]);

  // Handle OAuth callback from popup (via postMessage)
  // Note: The callback endpoint is called by Google's redirect, not by us.
  // We just need to verify the callback succeeded and update state.
  const handleAuthCallback = useCallback((_code: string, state: string) => {
    // Verify state matches (CSRF protection)
    const storedState = localStorage.getItem(DRIVE_STORAGE_KEYS.OAUTH_STATE);
    console.log('DEBUG: Received state:', state);
    console.log('DEBUG: Stored state:', storedState);
    
    if (storedState && storedState !== state) {
      console.error('OAuth state mismatch - possible CSRF attack');
      return;
    }
    
    // Tokens were already saved by the callback endpoint.
    // Just update local state and refresh projects.
    localStorage.setItem(DRIVE_STORAGE_KEYS.CONNECTED, 'true');
    localStorage.setItem(DRIVE_STORAGE_KEYS.LAST_CONNECTED_AT, String(Date.now()));
    setIsConnected(true);
    setBackendAvailable(true);
    scanDrive();
  }, []);

  // Track if OAuth is already in progress
  const [isConnecting, setIsConnecting] = useState(false);

  // Connect to Google Drive
  const connectDrive = async () => {
    if (isConnecting) {
      console.log('DEBUG: OAuth already in progress, ignoring click');
      return;
    }
    setIsConnecting(true);
    setScanning(true);
    setConnectionError(null);
    
    try {
      // Try backend auth endpoint first
      const res = await fetch(`${API_URL}/connectors/google-drive/auth/url`, { 
        headers: getHeaders(),
        signal: AbortSignal.timeout(5000)
      });
      
      let authUrl: string | null = null;
      
      if (res.ok) {
        const data = await res.json();
        authUrl = data.auth_url;
        // Store the full state (nonce:user_id) returned by backend
        localStorage.setItem(DRIVE_STORAGE_KEYS.OAUTH_STATE, data.state);
        console.log('DEBUG: Backend auth URL:', authUrl);
        console.log('DEBUG: State from backend:', data.state);
      } else if (res.status === 401) {
        // Token expired - try refresh
        const refreshed = await refreshAuthToken();
        if (refreshed) {
          // Retry connection
          setIsConnecting(false);
          setScanning(false);
          await connectDrive();
          return;
        } else {
          throw new Error('Session expired - please login again');
        }
      } else {
        // Backend not available - use direct OAuth
        console.log('Backend auth unavailable, status:', res.status);
        authUrl = buildGoogleAuthUrl();
      }
      
      if (authUrl) {
        // Calculate popup position
        const width = 500;
        const height = 600;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;
        
        // Open OAuth popup
        const popup = window.open(
          authUrl,
          'google-drive-auth',
          `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no`
        );
        
        if (!popup) {
          // Popup blocked - redirect instead
          window.location.href = authUrl;
          return;
        }
        
        // Listen for message from popup (postMessage approach for COOP compatibility)
        let authCompleted = false;
        const messageHandler = (event: MessageEvent) => {
          // Verify origin - accept messages from our backend
          if (event.origin !== 'https://cerebrum-api.onrender.com') return;
          
          if (event.data?.type === 'GOOGLE_DRIVE_AUTH_SUCCESS') {
            authCompleted = true;
            setIsConnecting(false);
            const { code, state } = event.data;
            if (code && state) {
              window.removeEventListener('message', messageHandler);
              try { popup.close(); } catch (e) { /* ignore COOP errors */ }
              handleAuthCallback(code, state);
            }
          }
        };
        window.addEventListener('message', messageHandler);
        
        // Fallback: timeout-based check (avoids COOP issues with popup.closed)
        setTimeout(() => {
          window.removeEventListener('message', messageHandler);
          if (!authCompleted) {
            // Timeout - authentication took too long
            setIsConnecting(false);
            setScanning(false);
            setConnectionError('Authentication timed out. Please try again.');
            try { popup.close(); } catch (e) { /* ignore */ }
          }
        }, 120000); // 2 minute timeout
      }
    } catch (e: any) {
      console.error('Drive connect error:', e);
      setConnectionError(e.message || 'Connection failed');
      setIsConnected(false);
    } finally {
      setTimeout(() => {
        setScanning(false);
        setIsConnecting(false);
      }, 1000);
    }
  };

  // Scan Drive for projects
  const scanDrive = async () => {
    console.log('[Drive] Starting scan...');
    setScanning(true);
    
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/scan`, {
        method: 'POST',
        headers: getHeaders(),
        signal: AbortSignal.timeout(30000) // 30 second timeout for real scan
      });
      
      console.log('[Drive] Scan response:', { status: res.status, ok: res.ok });
      
      if (res.ok) {
        const data = await res.json();
        console.log('[Drive] Scan data:', data);
        
        // Handle the real scan response
        if (data.status === 'success' && data.mapping_ids) {
          // Fetch the actual projects after scan
          await refreshProjects();
        } else if (data.message === 'Google Drive not connected') {
          setConnectionError('Google Drive not connected');
          setIsConnected(false);
        } else {
          setConnectionError(data.message || 'Scan failed');
        }
        
        // Update last connected timestamp
        localStorage.setItem(DRIVE_STORAGE_KEYS.LAST_CONNECTED_AT, String(Date.now()));
      } else if (res.status === 401) {
        // Token expired - try refresh
        const refreshed = await refreshAuthToken();
        if (refreshed) {
          // Retry scan
          await scanDrive();
          return;
        }
      } else {
        const error = await res.json().catch(() => ({ detail: 'Scan failed' }));
        console.error('[Drive] Scan error:', error);
        setConnectionError(error.detail || 'Scan failed');
      }
    } catch (e: any) {
      console.error('[Drive] Scan failed:', e);
      setConnectionError(`Scan failed: ${e.message}`);
    } finally {
      setScanning(false);
    }
  };

  // Refresh projects list
  const refreshProjects = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/projects`, { 
        headers: getHeaders(),
        signal: AbortSignal.timeout(5000)
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.projects) {
          setProjects(data.projects);
        }
        setIsConnected(true);
        // Update last connected timestamp
        localStorage.setItem(DRIVE_STORAGE_KEYS.LAST_CONNECTED_AT, String(Date.now()));
      } else if (res.status === 401) {
        // Token expired - try refresh
        const refreshed = await refreshAuthToken();
        if (refreshed) {
          // Retry refresh
          await refreshProjects();
          return;
        }
      }
    } catch (e) {
      // Ignore errors - keep existing projects
    }
  }, [refreshAuthToken]);

  // Disconnect Drive
  const disconnectDrive = async () => {
    try {
      await fetch(`${API_URL}/connectors/google-drive/disconnect`, {
        method: 'POST',
        headers: getHeaders()
      });
    } catch (e) {
      // Ignore errors
    }
    
    localStorage.removeItem(DRIVE_STORAGE_KEYS.CONNECTED);
    localStorage.removeItem(DRIVE_STORAGE_KEYS.OAUTH_STATE);
    localStorage.removeItem(DRIVE_STORAGE_KEYS.LAST_CONNECTED_AT);
    setIsConnected(false);
    setProjects([]);
    setConnectionError(null);
  };

  // Get files for a project
  const getProjectFiles = useCallback(async (projectId: string) => {
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/projects/${projectId}/files`, {
        headers: getHeaders(),
        signal: AbortSignal.timeout(10000)
      });
      
      if (res.ok) {
        return await res.json();
      } else if (res.status === 401) {
        const refreshed = await refreshAuthToken();
        if (refreshed) {
          return getProjectFiles(projectId);
        }
      }
      return [];
    } catch (e) {
      console.error('[Drive] Failed to get project files:', e);
      return [];
    }
  }, [refreshAuthToken]);

  // ZVec Semantic Search
  const searchDrive = async (query: string, project?: string): Promise<{query: string, results: SearchResult[], count: number}> => {
    try {
      const params = new URLSearchParams({ query, top_k: '5' });
      if (project) params.append('project', project);
      
      const res = await fetch(
        `${API_URL}/connectors/google-drive/search?${params}`,
        { 
          method: 'POST',
          headers: getHeaders(),
          signal: AbortSignal.timeout(10000)
        }
      );
      
      if (!res.ok) {
        if (res.status === 401) {
          // Token expired - try refresh
          const refreshed = await refreshAuthToken();
          if (refreshed) {
            // Retry search
            return searchDrive(query, project);
          }
        }
        // Return demo results
        return {
          query,
          results: [
            {
              id: 'demo_result_1',
              score: 0.92,
              metadata: {
                name: 'Safety_Report_Q4.pdf',
                project: project || 'General',
                content_preview: `Results for "${query}": Safety inspection found critical issues in Zone B...`
              }
            }
          ],
          count: 1
        };
      }
      
      return await res.json();
    } catch (e) {
      return { query, results: [], count: 0 };
    }
  };

  // Index files
  const indexDriveFiles = async () => {
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/index`, {
        method: 'POST',
        headers: getHeaders(),
        signal: AbortSignal.timeout(30000)
      });
      
      if (!res.ok) {
        if (res.status === 401) {
          // Token expired - try refresh
          const refreshed = await refreshAuthToken();
          if (refreshed) {
            // Retry indexing
            return indexDriveFiles();
          }
        }
        return { 
          files_scanned: 0, 
          indexed: 0, 
          message: 'Indexing not available - backend may be deploying' 
        };
      }
      
      return await res.json();
    } catch (e) {
      return { 
        files_scanned: 0, 
        indexed: 0, 
        message: 'Indexing failed - check connection' 
      };
    }
  };

  // Auto-scan when connected
  useEffect(() => {
    if (isConnected && projects.length === 0 && !scanning) {
      scanDrive();
    }
  }, [isConnected]);

  // Periodic refresh (12 hours)
  useEffect(() => {
    if (isConnected) {
      const TWELVE_HOURS = 12 * 60 * 60 * 1000;
      const interval = setInterval(refreshProjects, TWELVE_HOURS);
      return () => clearInterval(interval);
    }
  }, [isConnected, refreshProjects]);

  return {
    projects,
    scanning,
    isConnected,
    loading,
    backendAvailable,
    connectionError,
    connectDrive,
    disconnectDrive,
    scanDrive,
    refreshProjects,
    searchDrive,
    indexDriveFiles,
    getProjectFiles
  };
}
