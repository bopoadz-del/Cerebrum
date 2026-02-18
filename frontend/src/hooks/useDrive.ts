import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com/api/v1';

export interface Project {
  id: string;
  name: string;
  file_count: number;
  status: string;
  updated_at?: string;
}

export function useDrive() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [scanning, setScanning] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  const getToken = () => localStorage.getItem('auth_token') || '';

  const getHeaders = () => ({
    'Authorization': `Bearer ${getToken()}`,
    'Content-Type': 'application/json'
  });

  const checkConnection = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/connectors/google-drive/status`, { 
        headers: getHeaders() 
      });
      const data = await res.json();
      setIsConnected(data.connected);
      if (data.connected) {
        refreshProjects();
      }
    } catch (e) {
      console.error('Check connection failed:', e);
      setIsConnected(false);
    } finally {
      setLoading(false);
    }
  }, []);

  // Check if Drive is connected on mount
  useEffect(() => {
    if (user) {
      checkConnection();
    }
  }, [user, checkConnection]);

  const connectDrive = async () => {
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/auth`, { 
        headers: getHeaders() 
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        console.error('Auth request failed:', errorData);
        alert('Failed to get Google Drive auth URL. Please try again.');
        return;
      }
      
      const data = await res.json();
      
      if (data.auth_url) {
        // Try to open popup
        const width = 600;
        const height = 700;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;
        
        const popup = window.open(
          data.auth_url,
          'drive-auth',
          `width=${width},height=${height},left=${left},top=${top},popup=true`
        );
        
        if (!popup || popup.closed || typeof popup.closed === 'undefined') {
          // Popup was blocked, redirect instead
          console.log('Popup blocked, redirecting...');
          window.location.href = data.auth_url;
          return;
        }
        
        // Listen for callback
        const checkPopup = setInterval(() => {
          try {
            // Check if popup redirected to our callback
            if (popup.location.href.includes('/connectors/google-drive/callback')) {
              clearInterval(checkPopup);
              popup.close();
              checkConnection(); // Re-check after auth
            }
          } catch (e) {
            // Cross-origin error, popup still on Google
          }
          
          if (popup.closed) {
            clearInterval(checkPopup);
            checkConnection(); // Re-check after popup closes
          }
        }, 1000);
      } else if (data.error) {
        console.error('Auth error:', data.error);
        alert(`Google Drive auth error: ${data.error}`);
      }
    } catch (e) {
      console.error('Drive connect failed:', e);
      alert('Failed to connect Google Drive. Please check your internet connection and try again.');
    }
  };

  const scanDrive = async () => {
    setScanning(true);
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/scan`, {
        method: 'POST',
        headers: getHeaders()
      });
      
      if (!res.ok) {
        if (res.status === 401) {
          setIsConnected(false);
          alert('Google Drive not connected. Please connect first.');
          return;
        }
        throw new Error(`Scan failed: ${res.status}`);
      }
      
      const data = await res.json();
      
      if (data.projects) {
        setProjects(data.projects);
      }
      setIsConnected(true);
      return data;
    } catch (e) {
      console.error('Scan failed:', e);
    } finally {
      setScanning(false);
    }
  };

  const refreshProjects = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/projects`, { 
        headers: getHeaders() 
      });
      
      if (!res.ok) {
        if (res.status === 401) {
          setIsConnected(false);
        }
        return;
      }
      
      const data = await res.json();
      if (data.projects) {
        setProjects(data.projects);
        setIsConnected(true);
      }
    } catch (e) {
      console.error('Refresh failed:', e);
    }
  }, []);

  // Auto-scan when connected changes
  useEffect(() => {
    if (isConnected && projects.length === 0 && !scanning) {
      scanDrive();
    }
  }, [isConnected]);

  // Refresh projects periodically (every 12 hours)
  useEffect(() => {
    if (isConnected) {
      const TWELVE_HOURS = 12 * 60 * 60 * 1000; // 43,200,000 ms
      const interval = setInterval(refreshProjects, TWELVE_HOURS);
      return () => clearInterval(interval);
    }
  }, [isConnected, refreshProjects]);

  return {
    projects,
    scanning,
    isConnected,
    loading,
    connectDrive,
    scanDrive,
    refreshProjects
  };
}
