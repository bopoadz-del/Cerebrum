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

  const headers = {
    'Authorization': `Bearer ${getToken()}`,
    'Content-Type': 'application/json'
  };

  // Check if Drive is connected on mount
  useEffect(() => {
    if (user) {
      checkConnection();
    }
  }, [user]);

  const checkConnection = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_URL}/connectors/google-drive/status`, { headers });
      const data = await res.json();
      setIsConnected(data.connected);
      if (data.connected) {
        refreshProjects();
      }
    } catch (e) {
      setIsConnected(false);
    } finally {
      setLoading(false);
    }
  };

  const connectDrive = async () => {
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/auth`, { headers });
      const data = await res.json();
      
      if (data.auth_url) {
        // Open OAuth in popup
        const width = 600;
        const height = 700;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;
        
        const popup = window.open(
          data.auth_url,
          'drive-auth',
          `width=${width},height=${height},left=${left},top=${top}`
        );
        
        // Listen for callback
        const checkPopup = setInterval(() => {
          if (popup?.closed) {
            clearInterval(checkPopup);
            checkConnection(); // Re-check after popup closes
          }
        }, 1000);
      }
    } catch (e) {
      console.error('Drive connect failed:', e);
    }
  };

  const scanDrive = async () => {
    setScanning(true);
    try {
      const res = await fetch(`${API_URL}/connectors/google-drive/scan`, {
        method: 'POST',
        headers
      });
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
      const res = await fetch(`${API_URL}/connectors/google-drive/projects`, { headers });
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

  // Refresh projects periodically
  useEffect(() => {
    if (isConnected) {
      const interval = setInterval(refreshProjects, 30000);
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
