/**
 * radius-search.spec.js - E2E Tests with Playwright
 * Phase 7 Day 4
 * 
 * End-to-end tests for RadiusSearchTool component
 */

import { test, expect } from '@playwright/test';

test.describe('RadiusSearchTool E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to map view with radius search enabled
    await page.goto('/maps?enableRadiusSearch=true');
    
    // Wait for Google Maps to load
    await page.waitForSelector('.map-wrapper', { timeout: 10000 });
    await page.waitForTimeout(2000); // Allow map to fully initialize
  });

  test('should display radius search panel', async ({ page }) => {
    // Check panel visibility
    await expect(page.locator('.search-panel')).toBeVisible();
    await expect(page.locator('.panel-header h3')).toHaveText('🔍 Busca por Raio');
    
    // Check instructions are visible
    await expect(page.locator('.instructions')).toBeVisible();
    await expect(page.locator('.instructions p')).toContainText('Clique no mapa');
  });

  test('should toggle panel collapse', async ({ page }) => {
    const toggleButton = page.locator('.toggle-button');
    const panelContent = page.locator('.panel-content');

    // Initially expanded
    await expect(panelContent).toBeVisible();

    // Collapse
    await toggleButton.click();
    await expect(panelContent).not.toBeVisible();
    await expect(page.locator('.search-panel')).toHaveClass(/collapsed/);

    // Expand
    await toggleButton.click();
    await expect(panelContent).toBeVisible();
  });

  test('should set search center on map click', async ({ page }) => {
    // Click on map (center of visible area)
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(500);

      // Check center info is displayed
      await expect(page.locator('.center-info')).toBeVisible();
      await expect(page.locator('.center-info .value')).toContainText(',');
      
      // Check radius slider is visible
      await expect(page.locator('.radius-slider')).toBeVisible();
      
      // Check search button is visible
      await expect(page.locator('.search-button')).toBeVisible();
    }
  });

  test('should execute search and display results', async ({ page }) => {
    // Mock API response
    await page.route('**/api/v1/inventory/sites/radius*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 3,
          center: { lat: -15.7801, lng: -47.9292 },
          radius_km: 10,
          sites: [
            {
              id: 1,
              display_name: 'Brasília Center',
              latitude: -15.7801,
              longitude: -47.9292,
              distance_km: 0.0
            },
            {
              id: 2,
              display_name: 'Brasília North',
              latitude: -15.7350,
              longitude: -47.9292,
              distance_km: 5.01
            },
            {
              id: 3,
              display_name: 'Asa Sul',
              latitude: -15.8200,
              longitude: -47.9100,
              distance_km: 7.45
            }
          ]
        })
      });
    });

    // Click map to set center
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(1000); // Wait for auto-search
      
      // Check results summary
      await expect(page.locator('.results-summary')).toBeVisible();
      await expect(page.locator('.result-count')).toHaveText('3 site(s) encontrado(s)');
      
      // Check result items
      const resultItems = page.locator('.result-item');
      await expect(resultItems).toHaveCount(3);
      
      await expect(resultItems.nth(0).locator('.site-name')).toHaveText('Brasília Center');
      await expect(resultItems.nth(0).locator('.site-distance')).toContainText('0 km');
      
      await expect(resultItems.nth(1).locator('.site-name')).toHaveText('Brasília North');
      await expect(resultItems.nth(1).locator('.site-distance')).toContainText('5.01 km');
      
      await expect(resultItems.nth(2).locator('.site-name')).toHaveText('Asa Sul');
      await expect(resultItems.nth(2).locator('.site-distance')).toContainText('7.45 km');
    }
  });

  test('should adjust radius with slider', async ({ page }) => {
    // Set search center
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(500);
      
      const slider = page.locator('.radius-slider');
      await expect(slider).toBeVisible();
      
      // Get initial value
      const initialValue = await slider.inputValue();
      expect(parseInt(initialValue)).toBe(10); // Default
      
      // Change slider value
      await slider.fill('50');
      await page.waitForTimeout(100);
      
      // Check label updates
      await expect(page.locator('.slider-label strong')).toHaveText('50');
    }
  });

  test('should handle no results scenario', async ({ page }) => {
    // Mock empty response
    await page.route('**/api/v1/inventory/sites/radius*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 0,
          center: { lat: 0, lng: 0 },
          radius_km: 10,
          sites: []
        })
      });
    });

    // Click map
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(1000);
      
      // Check no results message
      await expect(page.locator('.results-summary')).toBeVisible();
      await expect(page.locator('.result-count')).toHaveText('0 site(s) encontrado(s)');
      await expect(page.locator('.no-results')).toBeVisible();
      await expect(page.locator('.no-results')).toContainText('Nenhum site encontrado');
    }
  });

  test('should display error message on API failure', async ({ page }) => {
    // Mock error response
    await page.route('**/api/v1/inventory/sites/radius*', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Latitude must be between -90 and 90'
        })
      });
    });

    // Click map
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(1000);
      
      // Check error message
      await expect(page.locator('.error-message')).toBeVisible();
      await expect(page.locator('.error-message')).toContainText('Latitude must be between');
    }
  });

  test('should clear search state', async ({ page }) => {
    // Mock API response
    await page.route('**/api/v1/inventory/sites/radius*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 1,
          center: { lat: -15.7801, lng: -47.9292 },
          radius_km: 10,
          sites: [
            {
              id: 1,
              display_name: 'Test Site',
              latitude: -15.7801,
              longitude: -47.9292,
              distance_km: 0.0
            }
          ]
        })
      });
    });

    // Set search center and execute
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(1000);
      
      // Verify results are visible
      await expect(page.locator('.results-summary')).toBeVisible();
      await expect(page.locator('.center-info')).toBeVisible();
      
      // Click clear button
      await page.locator('.clear-button').click();
      await page.waitForTimeout(300);
      
      // Verify state is cleared
      await expect(page.locator('.center-info')).not.toBeVisible();
      await expect(page.locator('.results-summary')).not.toBeVisible();
      await expect(page.locator('.instructions')).toBeVisible();
    }
  });

  test('should highlight result on hover', async ({ page }) => {
    // Mock API response
    await page.route('**/api/v1/inventory/sites/radius*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 2,
          center: { lat: -15.7801, lng: -47.9292 },
          radius_km: 10,
          sites: [
            {
              id: 1,
              display_name: 'Site A',
              latitude: -15.7801,
              longitude: -47.9292,
              distance_km: 0.0
            },
            {
              id: 2,
              display_name: 'Site B',
              latitude: -15.7350,
              longitude: -47.9292,
              distance_km: 5.01
            }
          ]
        })
      });
    });

    // Execute search
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(1000);
      
      const firstResult = page.locator('.result-item').first();
      
      // Hover over first result
      await firstResult.hover();
      await page.waitForTimeout(200);
      
      // Check hover styles applied (background color change)
      const backgroundColor = await firstResult.evaluate((el) => 
        window.getComputedStyle(el).backgroundColor
      );
      
      // Should have hover background color (light blue)
      expect(backgroundColor).toBeTruthy();
    }
  });

  test('should send correct API request parameters', async ({ page }) => {
    let requestUrl = '';

    // Intercept API request
    await page.route('**/api/v1/inventory/sites/radius*', async (route, request) => {
      requestUrl = request.url();
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 0,
          center: { lat: -15.7801, lng: -47.9292 },
          radius_km: 10,
          sites: []
        })
      });
    });

    // Click map and execute search
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(1000);
      
      // Verify request URL contains correct parameters
      expect(requestUrl).toContain('lat=');
      expect(requestUrl).toContain('lng=');
      expect(requestUrl).toContain('radius_km=10');
      expect(requestUrl).toContain('limit=100');
    }
  });

  test('should show loading state during search', async ({ page }) => {
    // Delay API response
    await page.route('**/api/v1/inventory/sites/radius*', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 0,
          sites: []
        })
      });
    });

    // Execute search
    const mapCanvas = page.locator('.map-wrapper');
    const box = await mapCanvas.boundingBox();
    
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      
      // Check loading state
      const searchButton = page.locator('.search-button');
      await expect(searchButton).toContainText('Buscando...');
      await expect(searchButton).toBeDisabled();
      await expect(page.locator('.spinner-small')).toBeVisible();
      
      // Wait for completion
      await page.waitForTimeout(1200);
      
      // Check loading state cleared
      await expect(searchButton).toContainText('Buscar Sites');
      await expect(searchButton).not.toBeDisabled();
    }
  });
});

test.describe('RadiusSearchTool Accessibility', () => {
  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/maps?enableRadiusSearch=true');
    await page.waitForSelector('.search-panel');

    // Check slider label
    const sliderLabel = page.locator('label[for="radius-slider"]');
    await expect(sliderLabel).toBeVisible();

    // Check buttons have titles/labels
    const toggleButton = page.locator('.toggle-button');
    await expect(toggleButton).toHaveAttribute('title');
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/maps?enableRadiusSearch=true');
    await page.waitForSelector('.search-panel');

    // Tab to toggle button
    await page.keyboard.press('Tab');
    let focused = await page.evaluate(() => document.activeElement?.className);
    expect(focused).toContain('toggle');

    // Press Enter to toggle
    await page.keyboard.press('Enter');
    await page.waitForTimeout(300);
    
    const panelContent = page.locator('.panel-content');
    await expect(panelContent).not.toBeVisible();
  });
});
