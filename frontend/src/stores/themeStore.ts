import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';
type ResolvedTheme = 'light' | 'dark';

interface ThemeState {
  // State
  theme: Theme;
  resolvedTheme: ResolvedTheme;

  // Actions
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  resolveTheme: () => ResolvedTheme;
}

// Helper to resolve system theme
const getSystemTheme = (): ResolvedTheme => {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

// Helper to apply theme to document
const applyTheme = (theme: ResolvedTheme): void => {
  if (typeof document === 'undefined') return;
  
  const root = document.documentElement;
  root.classList.remove('light', 'dark');
  root.classList.add(theme);

  // Update meta theme-color
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute(
      'content',
      theme === 'dark' ? '#0f172a' : '#ffffff'
    );
  }
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: 'system',
      resolvedTheme: 'light',

      // Set theme
      setTheme: (theme) => {
        const resolvedTheme = theme === 'system' ? getSystemTheme() : theme;
        
        set({ theme, resolvedTheme });
        applyTheme(resolvedTheme);

        // Listen for system theme changes if using system theme
        if (theme === 'system' && typeof window !== 'undefined') {
          const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
          mediaQuery.addEventListener('change', (e) => {
            const newResolvedTheme = e.matches ? 'dark' : 'light';
            set({ resolvedTheme: newResolvedTheme });
            applyTheme(newResolvedTheme);
          });
        }
      },

      // Toggle between light and dark
      toggleTheme: () => {
        const { resolvedTheme } = get();
        const newTheme = resolvedTheme === 'light' ? 'dark' : 'light';
        
        set({ theme: newTheme, resolvedTheme: newTheme });
        applyTheme(newTheme);
      },

      // Resolve current theme
      resolveTheme: () => {
        const { theme } = get();
        return theme === 'system' ? getSystemTheme() : theme;
      },
    }),
    {
      name: 'theme-storage',
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        // Apply theme after rehydration
        if (state) {
          const resolvedTheme = state.theme === 'system' ? getSystemTheme() : state.theme;
          state.resolvedTheme = resolvedTheme;
          applyTheme(resolvedTheme);
        }
      },
    }
  )
);

// Selector hooks
export const useTheme = () => useThemeStore((state) => state.theme);
export const useResolvedTheme = () => useThemeStore((state) => state.resolvedTheme);
export const useSetTheme = () => useThemeStore((state) => state.setTheme);
export const useToggleTheme = () => useThemeStore((state) => state.toggleTheme);

export default useThemeStore;
