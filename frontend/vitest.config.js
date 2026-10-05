import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    // EV-0009: antes só `tests/unit/**` corria — 121 testes em
    // `src/composables/__tests__` e `tests/components` ficavam de fora.
    include: [
      'tests/unit/**/*.spec.js',
      'tests/components/**/*.{spec,test}.js',
      'src/**/__tests__/**/*.spec.js',
      'src/**/*.test.js',
    ],
    exclude: ['node_modules/**', 'dist/**', 'tests/e2e/**'],
  },
});
