/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1')
  ? API_URL
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

// Tokens are stored only in httpOnly cookies set by the backend (C-3 fix).
// Only non-sensitive user profile data is kept in React state.
// On page load we restore session by calling /auth/me (cookie sent automatically).

// Clear legacy localStorage tokens on startup (one-time migration cleanup)
const LEGACY_TOKEN_KEYS = [
  'auth_token', 'refresh_token',
  'cerebrum_auth_token_v1', 'cerebrum_refresh_token_v1', 'cerebrum_token_expires_v1',
];
LEGACY_TOKEN_KEYS.forEach(k => localStorage.removeItem(k));

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuthToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearAuthData = useCallback(() => {
    setUser(null);
    // Remove any residual user profile stored in localStorage
    localStorage.removeItem('cerebrum_user_v1');
  }, []);

  // Refresh access token — backend reads httpOnly refresh cookie, issues new access cookie
  const refreshAuthToken = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',   // sends & receives httpOnly cookies
        body: JSON.stringify({}),  // refresh token comes from cookie on the backend
      });
      if (!response.ok) {
        clearAuthData();
        return false;
      }
      return true;
    } catch {
      clearAuthData();
      return false;
    }
  }, [clearAuthData]);

  // Restore session on mount by hitting /auth/me (cookie sent automatically)
  useEffect(() => {
    const initAuth = async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
          credentials: 'include',
        });
        if (response.ok) {
          const userData: User = await response.json();
          setUser(userData);
        } else if (response.status === 401) {
          // Try a silent token refresh, then retry /auth/me
          const refreshed = await refreshAuthToken();
          if (refreshed) {
            const retry = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' });
            if (retry.ok) setUser(await retry.json());
          }
        }
      } catch {
        // Network error — leave user as null
      } finally {
        setIsLoading(false);
      }
    };
    initAuth();
  }, [refreshAuthToken]);

  // Periodic silent refresh every 10 minutes while logged in
  useEffect(() => {
    if (!user) return;
    const interval = setInterval(() => refreshAuthToken(), 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, [user, refreshAuthToken]);

  const login = async (email: string, password: string) => {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',   // backend sets httpOnly cookies in response
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }

    // Tokens are now in httpOnly cookies — just fetch user profile
    const meResponse = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' });
    if (!meResponse.ok) throw new Error('Failed to fetch user profile');
    setUser(await meResponse.json());
  };

  const register = async (email: string, password: string, fullName: string) => {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(error.detail || 'Registration failed');
    }
    await login(email, password);
  };

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ all_devices: false }),
      });
    } catch {
      // Best-effort — clear client state regardless
    }
    clearAuthData();
  }, [clearAuthData]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshAuthToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}







