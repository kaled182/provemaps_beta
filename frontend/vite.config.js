import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig(({ mode }) => ({
  plugins: [vue()],

  root: '.', // Vite serves from frontend/
  publicDir: 'static', // Legacy static assets
  base: '/static/vue-spa/', // Ensure built assets resolve from Django static URL
  
  build: {
    outDir: '../backend/staticfiles/vue-spa', // Output to Django static collection area for SPA (Phase 11)
    emptyOutDir: true,
    manifest: true, // Generate manifest.json for Django asset mapping
    // EV-0019: minificação ligada (esbuild). O build anterior saía sem minify
    // «para manter console.log» — em produção o log de depuração sai no
    // `esbuild.pure` abaixo; warn/error ficam.
    minify: 'esbuild',
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
      },
      output: {
        // Hashed filenames so rebuilds always bust browser cache
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
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

  // Só no build de produção: remove console.log/debug/info/trace e `debugger`.
  // console.warn/console.error ficam (são o sinal de «Zabbix fora» etc.).
  esbuild:
    mode === 'production'
      ? {
          pure: ['console.log', 'console.debug', 'console.info', 'console.trace'],
          drop: ['debugger'],
        }
      : {},
}));
