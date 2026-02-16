/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // Custom colors
      colors: {
        // Primary brand colors
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // Secondary accent colors
        secondary: {
          50: '#fdf4ff',
          100: '#fae8ff',
          200: '#f5d0fe',
          300: '#f0abfc',
          400: '#e879f9',
          500: '#d946ef',
          600: '#c026d3',
          700: '#a21caf',
          800: '#86198f',
          900: '#701a75',
          950: '#4a044e',
        },
        // Semantic colors
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        danger: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
        // Dark mode specific
        dark: {
          bg: '#0f172a',
          surface: '#1e293b',
          border: '#334155',
        },
      },

      // Custom font family
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'Fira Code',
          'Menlo',
          'Monaco',
          'Consolas',
          'Liberation Mono',
          'Courier New',
          'monospace',
        ],
      },

      // Custom font sizes
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },

      // Custom spacing
      spacing: {
        '4.5': '1.125rem',
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },

      // Custom border radius
      borderRadius: {
        '4xl': '2rem',
      },

      // Custom animations
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'fade-out': 'fadeOut 0.2s ease-out',
        'slide-in': 'slideIn 0.2s ease-out',
        'slide-out': 'slideOut 0.2s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'spin-slow': 'spin 3s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideOut: {
          '0%': { transform: 'translateY(0)', opacity: '1' },
          '100%': { transform: 'translateY(-10px)', opacity: '0' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },

      // Custom box shadows
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'soft-lg': '0 10px 40px -10px rgba(0, 0, 0, 0.1)',
        'glow': '0 0 20px rgba(59, 130, 246, 0.5)',
        'glow-lg': '0 0 40px rgba(59, 130, 246, 0.5)',
      },

      // Custom transitions
      transitionTimingFunction: {
        'bounce-out': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },

      // Custom z-index scale
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      },

      // Custom backdrop blur
      backdropBlur: {
        xs: '2px',
      },

      // Custom screens
      screens: {
        'xs': '475px',
        '3xl': '1920px',
        '4xl': '2560px',
      },

      // Custom max widths
      maxWidth: {
        '8xl': '88rem',
        '9xl': '96rem',
      },

      // Custom min heights
      minHeight: {
        'screen-safe': 'calc(100vh - env(safe-area-inset-bottom))',
      },
    },
  },

  // Plugins
  plugins: [
    // Custom plugin for additional utilities
    function({ addUtilities, addComponents, theme }) {
      // Custom utilities
      addUtilities({
        '.text-balance': {
          'text-wrap': 'balance',
        },
        '.scrollbar-hide': {
          '-ms-overflow-style': 'none',
          'scrollbar-width': 'none',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        },
        '.tap-highlight-transparent': {
          '-webkit-tap-highlight-color': 'transparent',
        },
        '.gpu-accelerate': {
          'transform': 'translateZ(0)',
          'will-change': 'transform',
        },
      });

      // Custom components
      addComponents({
        '.btn': {
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: `${theme('spacing.2')} ${theme('spacing.4')}`,
          borderRadius: theme('borderRadius.lg'),
          fontWeight: theme('fontWeight.medium'),
          transition: 'all 150ms ease-in-out',
          '&:focus': {
            outline: 'none',
            ring: '2px',
            ringOffset: '2px',
          },
          '&:disabled': {
            opacity: '0.5',
            cursor: 'not-allowed',
          },
        },
        '.input': {
          display: 'block',
          width: '100%',
          padding: `${theme('spacing.2')} ${theme('spacing.3')}`,
          borderRadius: theme('borderRadius.lg'),
          borderWidth: '1px',
          borderColor: theme('colors.gray.300'),
          backgroundColor: theme('colors.white'),
          color: theme('colors.gray.900'),
          '&:focus': {
            outline: 'none',
            borderColor: theme('colors.primary.500'),
            ring: '2px',
            ringColor: theme('colors.primary.200'),
          },
          '&::placeholder': {
            color: theme('colors.gray.400'),
          },
        },
        '.card': {
          backgroundColor: theme('colors.white'),
          borderRadius: theme('borderRadius.xl'),
          borderWidth: '1px',
          borderColor: theme('colors.gray.200'),
          boxShadow: theme('boxShadow.soft'),
          overflow: 'hidden',
        },
      });
    },
  ],

  // Safelist for dynamic classes
  safelist: [
    'bg-primary-50',
    'bg-primary-100',
    'bg-primary-500',
    'bg-primary-600',
    'text-primary-500',
    'text-primary-600',
    'border-primary-500',
    'ring-primary-200',
    'bg-success-50',
    'bg-success-100',
    'bg-success-500',
    'text-success-500',
    'bg-warning-50',
    'bg-warning-100',
    'bg-warning-500',
    'text-warning-500',
    'bg-danger-50',
    'bg-danger-100',
    'bg-danger-500',
    'text-danger-500',
  ],
};
