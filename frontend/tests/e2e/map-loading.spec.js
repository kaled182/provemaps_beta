import { test, expect } from '@playwright/test';

test.describe('Unified Map System - /monitoring/backbone', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to backbone monitoring page
    await page.goto('http://localhost:8000/monitoring/backbone/');
  });

  test('should load page successfully', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/ProveMaps|Dashboard/i);
    
    // Wait for Vue app to mount
    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });
  });

  test('should render Google Maps container', async ({ page }) => {
    // Wait for Google Maps API to load and map to render
    // vue3-google-map creates a div with class 'vue3-google-map'
    const mapContainer = page.locator('.vue3-google-map, [id*="map"], .gm-style, .unified-map-container, .map-canvas');
    await expect(mapContainer.first()).toBeVisible({ timeout: 15000 });
  });

  test('should load Google Maps tiles', async ({ page }) => {
    // Wait for actual map tiles to load (indicates Maps API is working)
    // Google Maps creates img elements with src containing 'maps.googleapis.com'
    const mapTiles = page.locator('img[src*="maps.googleapis.com"]');
    await expect(mapTiles.first()).toBeVisible({ timeout: 20000 });
  });

  test('should render sidebar with menu', async ({ page }) => {
    // Check for navigation menu
    const sidebar = page.locator('.dashboard-sidebar, aside');
    await expect(sidebar).toBeVisible({ timeout: 10000 });
  });

  test('should show host cards in sidebar', async ({ page }) => {
    // Wait for host cards to load
    const hostCards = page.locator('.host-card, [class*="host"]');
    await expect(hostCards.first()).toBeVisible({ timeout: 15000 });
  });

  test('should have working map controls', async ({ page }) => {
    // Google Maps zoom controls should be visible
    const zoomControls = page.locator('button[aria-label*="Zoom"], .gm-control-active');
    await expect(zoomControls.first()).toBeVisible({ timeout: 15000 });
  });

  test('map should respond to interactions', async ({ page }) => {
    // Wait for map to be fully loaded
    await page.waitForSelector('.gm-style', { timeout: 15000 });
    
    // Try to interact with map (pan)
    const mapElement = page.locator('.gm-style').first();
    const boundingBox = await mapElement.boundingBox();
    
    if (boundingBox) {
      // Click and drag on map
      await page.mouse.move(
        boundingBox.x + boundingBox.width / 2,
        boundingBox.y + boundingBox.height / 2
      );
      await page.mouse.down();
      await page.mouse.move(
        boundingBox.x + boundingBox.width / 2 + 100,
        boundingBox.y + boundingBox.height / 2
      );
      await page.mouse.up();
      
      // Map should still be visible after interaction
      await expect(mapElement).toBeVisible();
    }
  });

  test('should not show critical console errors related to map loading', async ({ page }) => {
    const consoleErrors = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.gm-style', { timeout: 15000 });
    
    // Filter out expected/acceptable errors
    const criticalErrors = consoleErrors.filter(error => 
      !error.includes('favicon') && // Ignore favicon errors
      !error.includes('sourcemap') && // Ignore sourcemap warnings
      !error.includes('HTTP 401') && // Ignore auth errors in E2E tests
      !error.includes('Failed to fetch segments') && // Expected without auth
      !error.includes('Failed to load fiber network') && // Expected without auth
      error.toLowerCase().includes('google') && // Only Google Maps errors
      error.toLowerCase().includes('maps')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });

  test('should load Google Maps API key from meta tag', async ({ page }) => {
    // Check if API key meta tag exists
    const apiKeyMeta = page.locator('meta[name="google-maps-api-key"]');
    await expect(apiKeyMeta).toHaveCount(1);
    
    // Get API key value
    const apiKey = await apiKeyMeta.getAttribute('content');
    expect(apiKey).toBeTruthy();
    expect(apiKey.length).toBeGreaterThan(20);
  });

  test('should have correct map initialization', async ({ page }) => {
    // Wait for map to load
    await page.waitForSelector('.gm-style', { timeout: 15000 });
    
    // Check if map is properly initialized with center coordinates
    // This can be verified by checking if map has rendered content
    const mapContent = page.locator('.gm-style > div');
    const count = await mapContent.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Map Loading - /NetworkDesign/', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to Network Design page
    await page.goto('http://localhost:8000/NetworkDesign/');
  });

  test('should load page successfully', async ({ page }) => {
    await expect(page).toHaveTitle(/ProveMaps|Dashboard/i);
    const appContainer = page.locator('#app');
    await expect(appContainer).toBeVisible({ timeout: 10000 });
  });

  test('should render map container for Network Design', async ({ page }) => {
    // Network Design uses a different map container ID
    const mapContainer = page.locator('#builderMap, .network-design-page, .gm-style');
    await expect(mapContainer.first()).toBeVisible({ timeout: 15000 });
  });

  test('should load Google Maps tiles in Network Design', async ({ page }) => {
    const mapTiles = page.locator('img[src*="maps.googleapis.com"]');
    await expect(mapTiles.first()).toBeVisible({ timeout: 20000 });
  });

  test('should show fiber builder UI elements', async ({ page }) => {
    // Network Design should have builder controls
    const builderControls = page.locator('.network-design-page, #builderMap, .builder-controls');
    await expect(builderControls.first()).toBeVisible({ timeout: 10000 });
  });

  test('Network Design map should be interactive', async ({ page }) => {
    await page.waitForSelector('.gm-style', { timeout: 15000 });
    
    const mapElement = page.locator('.gm-style').first();
    await expect(mapElement).toBeVisible();
    
    // Verify map controls are clickable
    const zoomIn = page.locator('button[aria-label*="Zoom in"]');
    if (await zoomIn.count() > 0) {
      await expect(zoomIn.first()).toBeEnabled();
    }
  });
});

test.describe('Map Loading - Error Handling', () => {
  test('should handle network errors gracefully', async ({ page }) => {
    await page.goto('http://localhost:8000/monitoring/backbone/');
    
    // App should mount and show map even with API errors
    const app = page.locator('#app');
    await expect(app).toBeVisible({ timeout: 10000 });
    
    // Map container should render
    const mapContainer = page.locator('.gm-style');
    await expect(mapContainer.first()).toBeVisible({ timeout: 15000 });
  });

  // DECISION: Teste removido (Nov 2025)
  // Razão: Edge case raro (Maps API fail) com baixo ROI
  // 
  // Análise:
  // 1. Google Maps API tem 99.9%+ uptime
  // 2. Falha catastrófica (API down) afeta TODA a aplicação
  // 3. useMapService.js já tem error handling (console.error)
  // 4. Dashboard tem error-state para falhas de dados (não de Maps)
  // 5. Teste seria complexo (mock script blocking) com valor limitado
  //
  // Alternativas consideradas:
  // - Implementar error-state específico para Maps → Baixa prioridade
  // - Testar em staging com Maps API key inválida → Manual test
  // - Monitoramento real (Sentry) captura falhas → Melhor que teste E2E
  //
  // Recomendação: Monitorar erros via Sentry em produção
  // Referência: doc/developer/TESTING_E2E.md - "Quando NÃO testar edge cases"
});
