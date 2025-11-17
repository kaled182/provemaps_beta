// Playwright E2E test configuration for MapsProveFiber Vue 3 dashboard
// Phase 11 Sprint 1
import { defineConfig } from '@playwright/test';

export default defineConfig({
  // Adjusted testDir to include all tests under ./tests
  testDir: './tests',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  reporter: 'html',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { 
        viewport: { width: 1280, height: 720 },
      },
    },
  ],
});
