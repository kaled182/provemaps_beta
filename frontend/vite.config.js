import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],

  root: '.', // Vite serves from frontend/
  publicDir: 'static', // Legacy static assets
  base: '/static/vue-spa/', // Ensure built assets resolve from Django static URL
  
  build: {
    outDir: '../backend/staticfiles/vue-spa', // Output to Django static collection area for SPA (Phase 11)
    emptyOutDir: true,
    manifest: true, // Generate manifest.json for Django asset mapping
    minify: false, // Disable minification to keep console.log for debugging
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
      },
      output: {
        // Deterministic file names so spa.html can reference index.js directly (initial MVP)
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name][extname]',
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
