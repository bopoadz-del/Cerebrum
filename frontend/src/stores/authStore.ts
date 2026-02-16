import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/lib/api';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  avatar?: string;
  tenantId?: string;
  permissions: string[];
}

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  token: string | null;
  refreshToken: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
  clearError: () => void;
  setToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      token: null,
      refreshToken: null,

      // Login action
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
          // TODO: Replace with actual API call
          // const response = await api.post('/auth/login', { email, password });
          
          // Mock response for development
          await new Promise((resolve) => setTimeout(resolve, 1000));
          
          const mockUser: User = {
            id: '1',
            email,
            name: 'John Doe',
            role: 'admin',
            avatar: undefined,
            tenantId: 'tenant-1',
            permissions: ['read', 'write', 'delete', 'admin'],
          };

          const mockToken = 'mock-jwt-token';
          const mockRefreshToken = 'mock-refresh-token';

          set({
            user: mockUser,
            isAuthenticated: true,
            token: mockToken,
            refreshToken: mockRefreshToken,
            isLoading: false,
            error: null,
          });

          // Set auth header for subsequent requests
          api.defaults.headers.common['Authorization'] = `Bearer ${mockToken}`;
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : 'Login failed';
          set({
            isLoading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
          });
          throw error;
        }
      },

      // Logout action
      logout: async () => {
        set({ isLoading: true });

        try {
          // TODO: Replace with actual API call
          // await api.post('/auth/logout');
          
          await new Promise((resolve) => setTimeout(resolve, 500));
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          // Clear auth state regardless of API success
          set({
            user: null,
            isAuthenticated: false,
            token: null,
            refreshToken: null,
            isLoading: false,
            error: null,
          });

          // Remove auth header
          delete api.defaults.headers.common['Authorization'];
        }
      },

      // Refresh session
      refreshSession: async () => {
        const { refreshToken } = get();

        if (!refreshToken) {
          set({ isAuthenticated: false, user: null });
          return;
        }

        try {
          // TODO: Replace with actual API call
          // const response = await api.post('/auth/refresh', { refreshToken });
          
          // Mock refresh for development
          await new Promise((resolve) => setTimeout(resolve, 500));
          
          const newToken = 'new-mock-jwt-token';
          
          set({ token: newToken });
          api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
        } catch (error) {
          // Refresh failed, logout user
          get().logout();
        }
      },

      // Update user
      updateUser: (userData) => {
        const { user } = get();
        if (user) {
          set({ user: { ...user, ...userData } });
        }
      },

      // Clear error
      clearError: () => set({ error: null }),

      // Set token
      setToken: (token) => {
        set({ token });
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        token: state.token,
        refreshToken: state.refreshToken,
      }),
    }
  )
);

// Selector hooks for better performance
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);

export default useAuthStore;
