import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import { resolve } from 'path';
import { visualizer } from 'rollup-plugin-visualizer';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const isProduction = mode === 'production';

  return {
    plugins: [
      react({
        // Enable Fast Refresh
        jsxImportSource: 'react',
        // Enable development features
        devTarget: 'es2020',
      }),
      // Bundle analyzer (only in analyze mode)
      process.env.ANALYZE === 'true' &&
        visualizer({
          open: true,
          gzipSize: true,
          brotliSize: true,
          filename: 'dist/stats.html',
        }),
    ],

    // Resolve aliases
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '@components': resolve(__dirname, 'src/components'),
        '@hooks': resolve(__dirname, 'src/hooks'),
        '@lib': resolve(__dirname, 'src/lib'),
        '@pages': resolve(__dirname, 'src/pages'),
        '@stores': resolve(__dirname, 'src/stores'),
        '@contexts': resolve(__dirname, 'src/contexts'),
        '@types': resolve(__dirname, 'src/types'),
        '@assets': resolve(__dirname, 'src/assets'),
        '@utils': resolve(__dirname, 'src/utils'),
      },
    },

    // CSS configuration
    css: {
      devSourcemap: true,
      modules: {
        localsConvention: 'camelCase',
      },
    },

    // Build configuration
    build: {
      target: 'es2020',
      outDir: 'dist',
      sourcemap: !isProduction,
      minify: isProduction ? 'esbuild' : false,
      cssMinify: isProduction,
      
      // Rollup options
      rollupOptions: {
        output: {
          // Manual chunk splitting for optimal caching
          manualChunks: {
            // Core React libraries
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            
            // UI and styling
            'ui-vendor': [
              'lucide-react',
              'react-hot-toast',
              'react-window',
            ],
            
            // State management
            'state-vendor': ['zustand', '@tanstack/react-query'],
            
            // Data visualization
            'viz-vendor': ['three', '@react-three/fiber'],
            
            // Form handling
            'form-vendor': ['zod'],
          },
          
          // Chunk naming
          chunkFileNames: (chunkInfo) => {
            const facadeModuleId = chunkInfo.facadeModuleId
              ? chunkInfo.facadeModuleId.split('/')
              : [];
            const name = facadeModuleId[facadeModuleId.length - 1] || chunkInfo.name;
            return `js/${name.replace(/\.[^/.]+$/, '')}-[hash].js`;
          },
          
          // Entry file naming
          entryFileNames: 'js/[name]-[hash].js',
          
          // Asset file naming
          assetFileNames: (assetInfo) => {
            const info = assetInfo.name ? assetInfo.name.split('.') : [];
            const ext = info[info.length - 1];
            
            if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name || '')) {
              return 'images/[name]-[hash][extname]';
            }
            
            if (/\.(woff2?|ttf|otf|eot)$/i.test(assetInfo.name || '')) {
              return 'fonts/[name]-[hash][extname]';
            }
            
            if (ext === 'css') {
              return 'css/[name]-[hash][extname]';
            }
            
            return 'assets/[name]-[hash][extname]';
          },
        },
      },
      
      // Chunk size warning
      chunkSizeWarningLimit: 500,
      
      // Asset inline limit
      assetsInlineLimit: 4096,
    },

    // Development server
    server: {
      port: 3000,
      strictPort: false,
      open: true,
      cors: true,
      
      // Proxy API requests
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          ws: true,
        },
      },
      
      // HMR configuration
      hmr: {
        overlay: true,
      },
    },

    // Preview server (for production build testing)
    preview: {
      port: 4173,
      strictPort: false,
      open: true,
    },

    // Environment variables
    envPrefix: 'VITE_',

    // Optimize dependencies
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        'zustand',
        '@tanstack/react-query',
        'lucide-react',
        'three',
        'reactflow',
      ],
      exclude: [],
    },

    // ESBuild options
    esbuild: {
      target: 'es2020',
      jsx: 'automatic',
      logOverride: { 'this-is-undefined-in-esm': 'silent' },
    },

    // Define global constants
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    },
  };
});
