import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  
  root: '.', // Vite serves from frontend/
  publicDir: 'static', // Legacy static assets
  
  build: {
    outDir: '../backend/staticfiles/vue', // Output to Django static collection area
    emptyOutDir: true,
    manifest: true, // Generate manifest.json for Django asset mapping
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
      },
    },
  },
  
  server: {
    port: 5173,
    proxy: {
      // Proxy API requests to Django during dev
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
});
