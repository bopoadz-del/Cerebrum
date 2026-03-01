import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const API_BASE = API_URL.replace(/\/?$/, '').endsWith('/api/v1') 
  ? API_URL 
  : `${API_URL.replace(/\/?$/, '')}/api/v1`;

// Storage keys - versioned for compatibility across deployments
const STORAGE_KEYS = {
  AUTH_TOKEN: 'cerebrum_auth_token_v1',
  REFRESH_TOKEN: 'cerebrum_refresh_token_v1',
  USER: 'cerebrum_user_v1',
  TOKEN_EXPIRES_AT: 'cerebrum_token_expires_v1',
} as const;

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  refreshAuthToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Clear all auth data from storage
  const clearAuthData = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER);
    localStorage.removeItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
    setUser(null);
  }, []);

  // Validate token with backend
  const validateToken = useCallback(async (token: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return response.ok;
    } catch {
      return false;
    }
  }, []);

  // Refresh access token
  const refreshAuthToken = useCallback(async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
    if (!refreshToken) {
      return false;
    }

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        // Refresh failed - clear auth data
        clearAuthData();
        return false;
      }

      const data: TokenResponse = await response.json();
      
      // Update stored tokens
      localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, data.access_token);
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
      localStorage.setItem(
        STORAGE_KEYS.TOKEN_EXPIRES_AT, 
        String(Date.now() + data.expires_in * 1000)
      );
      
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      clearAuthData();
      return false;
    }
  }, [clearAuthData]);

  // Check auth status on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      const storedUser = localStorage.getItem(STORAGE_KEYS.USER);
      const expiresAt = localStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
      
      if (token && storedUser) {
        // Check if token is expired or about to expire (within 5 minutes)
        const expiresAtMs = expiresAt ? parseInt(expiresAt, 10) : 0;
        const isExpired = Date.now() >= expiresAtMs - 5 * 60 * 1000;
        
        if (isExpired) {
          // Try to refresh the token
          const refreshed = await refreshAuthToken();
          if (refreshed) {
            // Re-fetch user data with new token
            const newToken = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
            if (newToken) {
              try {
                const userResponse = await fetch(`${API_BASE}/auth/me`, {
                  headers: { 'Authorization': `Bearer ${newToken}` },
                });
                if (userResponse.ok) {
                  const userData = await userResponse.json();
                  localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(userData));
                  setUser(userData);
                } else {
                  clearAuthData();
                }
              } catch {
                clearAuthData();
              }
            }
          }
        } else {
          // Token still valid, verify with backend
          const isValid = await validateToken(token);
          if (isValid) {
            setUser(JSON.parse(storedUser));
          } else {
            // Token invalid, try refresh
            const refreshed = await refreshAuthToken();
            if (!refreshed) {
              clearAuthData();
            } else {
              setUser(JSON.parse(storedUser));
            }
          }
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, [clearAuthData, refreshAuthToken, validateToken]);

  // Setup periodic token refresh (every 10 minutes)
  useEffect(() => {
    if (!user) return;

    const interval = setInterval(() => {
      const expiresAt = localStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRES_AT);
      if (expiresAt) {
        const expiresAtMs = parseInt(expiresAt, 10);
        // Refresh if token expires in less than 10 minutes
        if (Date.now() >= expiresAtMs - 10 * 60 * 1000) {
          refreshAuthToken();
        }
      }
    }, 10 * 60 * 1000); // Check every 10 minutes

    return () => clearInterval(interval);
  }, [user, refreshAuthToken]);

  const login = async (email: string, password: string) => {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }

    const data: TokenResponse = await response.json();
    
    // Fetch user profile
    const userResponse = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${data.access_token}`,
      },
    });

    if (!userResponse.ok) {
      throw new Error('Failed to fetch user profile');
    }

    const userData = await userResponse.json();
    
    // Store all auth data
    localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, data.access_token);
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refresh_token);
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(userData));
    localStorage.setItem(
      STORAGE_KEYS.TOKEN_EXPIRES_AT, 
      String(Date.now() + data.expires_in * 1000)
    );
    
    setUser(userData);
  };

  const register = async (email: string, password: string, fullName: string) => {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(error.detail || 'Registration failed');
    }

    // After registration, log the user in
    await login(email, password);
  };

  const logout = useCallback(() => {
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

// Export storage keys for use in other components
export { STORAGE_KEYS };
