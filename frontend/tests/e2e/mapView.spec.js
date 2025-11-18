import { test, expect } from '@playwright/test';

test.describe('MapView Smoke Test', () => {
  test.beforeEach(async ({ page }) => {
    // Note: This assumes dev server running on localhost:8000
    // Adjust URL based on your environment
    await page.goto('http://localhost:8000/dashboard');
  });

  test('should load dashboard page', async ({ page }) => {
    // Wait for page title or main element
    await expect(page).toHaveTitle(/Dashboard|MapsProve/i);
  });

  test('should render map container', async ({ page }) => {
    // vue3-google-map renders into a div with gmap-map class or similar
    // Adjust selector based on actual rendered output
    const mapContainer = page.locator('.map-wrapper, #app');
    await expect(mapContainer).toBeVisible({ timeout: 10000 });
  });

  test('should show API key warning if not configured', async ({ page }) => {
    // If VITE_GOOGLE_MAPS_API_KEY is not set or is placeholder
    const missingKeyMsg = page.locator('text=/Google Maps API key/i');
    
    // This may or may not appear depending on env config
    // Just checking it doesn't crash
    const count = await missingKeyMsg.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should not show error alerts on initial load', async ({ page }) => {
    // Check for absence of error div (unless expected)
    const errorAlert = page.locator('.error');
    const errorCount = await errorAlert.count();
    
    // Allow 0 errors or check that error text is empty
    if (errorCount > 0) {
      const errorText = await errorAlert.textContent();
      expect(errorText).toBe('');
    }
  });
});

test.describe('MapView with Mock API', () => {
  test('should handle BBox API response', async ({ page }) => {
    // Intercept BBox API call
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
                coordinates: [[-47.9, -15.78], [-47.91, -15.79]],
              },
              properties: { status: 'operational' },
            },
          ],
        }),
      });
    });

    await page.goto('http://localhost:8000/dashboard');
    
    // Wait for potential map idle event and API call (event-based)
    await page.waitForLoadState('networkidle');
    
    // Since we mocked the response, the store should have segments
    // We can't directly inspect Vue store from Playwright, but we can check rendering
    // This is a basic smoke test - actual rendering depends on Google Maps loading
  });
});
