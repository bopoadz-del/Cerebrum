import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  base: '/',
  plugins: [react()],
  build: {
    rollupOptions: {
      external: [
        'react-syntax-highlighter', 
        'react-markdown',
        'react-syntax-highlighter/dist/esm/styles/prism'
      ]
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
