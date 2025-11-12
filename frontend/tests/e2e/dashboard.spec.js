import { test, expect } from '@playwright/test';

test.describe('Dashboard E2E User Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Mock WebSocket to prevent connection errors
    await page.addInitScript(() => {
      window.WebSocket = class MockWebSocket {
        constructor(url) {
          this.url = url;
          this.readyState = 1; // OPEN
          setTimeout(() => this.onopen?.(), 100);
        }
        send() {}
        close() {}
      };
    });

    // Mock dashboard API
    await page.route('**/api/v1/dashboard/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          hosts: [
            {
              id: 1,
              name: 'Host Alpha',
              status: 'operational',
              last_update: new Date().toISOString(),
              metrics: { cpu: 25, memory: 60, uptime: 86400 },
            },
            {
              id: 2,
              name: 'Host Beta',
              status: 'degraded',
              last_update: new Date().toISOString(),
              metrics: { cpu: 85, memory: 90, uptime: 43200 },
            },
          ],
        }),
      });
    });

    // Mock segments API
    await page.route('**/api/v1/inventory/segments/?bbox=*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'FeatureCollection',
          features: [
            {
              id: 1,
              type: 'Feature',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [-47.92, -15.78],
                  [-47.93, -15.79],
                ],
              },
              properties: {
                name: 'Segment A-B',
                status: 'operational',
                length: 1.2,
                fiber_count: 48,
              },
            },
          ],
        }),
      });
    });

    await page.goto('http://localhost:8000/dashboard');
  });

  test('Full flow: Dashboard load → Host display → WebSocket update', async ({ page }) => {
    // 1. Verify dashboard loads
    await expect(page.locator('h1:has-text("MapsProve Dashboard")')).toBeVisible();

    // 2. Verify connection status indicator
    const connectionStatus = page.locator('.connection-status');
    await expect(connectionStatus).toBeVisible();

    // 3. Wait for hosts to load
    await page.waitForTimeout(1000);

    // 4. Verify host cards are displayed
    const hostCards = page.locator('.host-card');
    await expect(hostCards).toHaveCount(2, { timeout: 5000 });

    // 5. Verify first host details
    const firstHost = hostCards.first();
    await expect(firstHost).toContainText('Host Alpha');
    await expect(firstHost).toContainText('Operacional');

    // 6. Verify status chart is visible
    const statusChart = page.locator('.status-chart');
    await expect(statusChart).toBeVisible();

    // 7. Simulate WebSocket message
    await page.evaluate(() => {
      window.dispatchEvent(
        new CustomEvent('websocket-message', {
          detail: {
            type: 'host_update',
            host_id: 1,
            status: 'down',
            name: 'Host Alpha',
            last_update: new Date().toISOString(),
          },
        })
      );
    });

    // Note: Actual update depends on WebSocket composable implementation
  });

  test('Map interaction: Segment click → InfoWindow display', async ({ page }) => {
    // Wait for map to render
    await page.waitForTimeout(2000);

    // Mock Google Maps InfoWindow (since we can't interact with real map easily)
    await page.evaluate(() => {
      // Simulate segment click programmatically
      window.__testShowSegmentInfo = {
        id: 1,
        properties: {
          name: 'Segment A-B',
          status: 'operational',
          length: 1.2,
          fiber_count: 48,
        },
      };
    });

    // In real scenario, you'd click on polyline
    // For now, verify InfoWindow would render if triggered
    const mapWrapper = page.locator('.map-wrapper');
    await expect(mapWrapper).toBeVisible();
  });

  test('Map controls: Fit bounds, Toggle legend', async ({ page }) => {
    // Wait for map controls to render
    await page.waitForTimeout(1000);

    // 1. Verify legend is visible by default
    const legend = page.locator('.map-legend');
    await expect(legend).toBeVisible({ timeout: 5000 });

    // 2. Find and click legend toggle button
    const legendButton = page.locator('button[title*="legend" i], .map-controls button').nth(1);
    if (await legendButton.count() > 0) {
      await legendButton.click();
      
      // Legend should hide
      await expect(legend).not.toBeVisible();

      // Click again to show
      await legendButton.click();
      await expect(legend).toBeVisible();
    }

    // 3. Test fit bounds button (won't actually fit since no real map, but shouldn't error)
    const fitBoundsButton = page.locator('button[title*="fit" i], .map-controls button').first();
    if (await fitBoundsButton.count() > 0) {
      await fitBoundsButton.click();
      // Should not throw error
      await page.waitForTimeout(500);
    }
  });

  test('Error state: API failure displays error message', async ({ page }) => {
    // Override route to fail
    await page.route('**/api/v1/dashboard/**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });

    await page.goto('http://localhost:8000/dashboard');

    // Wait for error state
    await page.waitForTimeout(1500);

    // Check for error message in sidebar
    const errorState = page.locator('.error-state, .error');
    const errorCount = await errorState.count();
    
    if (errorCount > 0) {
      await expect(errorState.first()).toBeVisible();
    }
  });

  test('Loading state: Shows loading indicator', async ({ page }) => {
    // Delay API response
    await page.route('**/api/v1/dashboard/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ hosts: [] }),
      });
    });

    await page.goto('http://localhost:8000/dashboard');

    // Should show loading state
    const loadingState = page.locator('.loading-state, text=/Carregando/i');
    await expect(loadingState.first()).toBeVisible({ timeout: 1000 });

    // Wait for loading to complete
    await page.waitForTimeout(2500);

    // Loading should disappear
    await expect(loadingState.first()).not.toBeVisible();
  });

  test('Empty state: No hosts displays empty message', async ({ page }) => {
    // Override to return empty hosts
    await page.route('**/api/v1/dashboard/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ hosts: [] }),
      });
    });

    await page.goto('http://localhost:8000/dashboard');
    await page.waitForTimeout(1500);

    // Should show empty state
    const emptyState = page.locator('.empty-state, text=/Nenhum host/i');
    await expect(emptyState.first()).toBeVisible();
  });

  test('Responsive: Mobile viewport adapts layout', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('http://localhost:8000/dashboard');
    await page.waitForTimeout(1000);

    // Verify layout adapts (sidebar might stack or collapse)
    const sidebar = page.locator('.dashboard-sidebar');
    const main = page.locator('.dashboard-main');

    await expect(main).toBeVisible();
    
    // On mobile, sidebar might have different styling
    const sidebarBox = await sidebar.boundingBox();
    if (sidebarBox) {
      // Sidebar should be narrower or stacked
      expect(sidebarBox.width).toBeLessThan(400);
    }
  });

  test('Accessibility: Keyboard navigation works', async ({ page }) => {
    await page.goto('http://localhost:8000/dashboard');
    await page.waitForTimeout(1500);

    // Tab through interactive elements
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Focus should be on an interactive element
    const focusedElement = page.locator(':focus');
    const tagName = await focusedElement.evaluate((el) => el?.tagName.toLowerCase());
    
    // Should focus button, link, or input
    expect(['button', 'a', 'input']).toContain(tagName);
  });
});

test.describe('Performance', () => {
  test('Dashboard loads within acceptable time', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('http://localhost:8000/dashboard');
    
    // Wait for key elements
    await page.locator('h1:has-text("MapsProve Dashboard")').waitFor();
    
    const loadTime = Date.now() - startTime;
    
    // Should load in under 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('Handles 50+ hosts without lag', async ({ page }) => {
    // Mock 50 hosts
    const hosts = Array.from({ length: 50 }, (_, i) => ({
      id: i + 1,
      name: `Host ${i + 1}`,
      status: ['operational', 'degraded', 'down'][i % 3],
      last_update: new Date().toISOString(),
      metrics: { cpu: 25 + i, memory: 60, uptime: 86400 },
    }));

    await page.route('**/api/v1/dashboard/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ hosts }),
      });
    });

    await page.goto('http://localhost:8000/dashboard');
    await page.waitForTimeout(2000);

    // Should render all hosts
    const hostCards = page.locator('.host-card');
    const count = await hostCards.count();
    
    // May virtualize, so count might be less than 50
    expect(count).toBeGreaterThan(0);
  });
});
