# Playwright Test Improvements - Map Testing Guide

## 🎯 Problem
Current E2E tests fail intermittently with timeouts because they use fixed delays instead of waiting for actual DOM/network events.

## 🔍 Common Anti-Patterns

### ❌ BAD: Fixed Timeouts
```javascript
// playwright/tests/map.spec.js (BEFORE)
test('should load fiber map', async ({ page }) => {
  await page.goto('/map');
  await page.waitForTimeout(5000);  // ❌ Fragile - may be too short or too long
  
  const markers = await page.locator('.leaflet-marker').count();
  expect(markers).toBeGreaterThan(0);
});
```

**Problems**:
- If API is slow, 5s might not be enough → test fails
- If API is fast, we waste 4s waiting → tests are slow
- No clear indication of *what* we're waiting for

---

## ✅ GOOD: Event-Based Waiting

### Pattern 1: Wait for Network Response

```javascript
test('should load fiber map', async ({ page }) => {
  // Start navigation
  const responsePromise = page.waitForResponse(
    response => 
      response.url().includes('/api/v1/fibers/') && 
      response.status() === 200,
    { timeout: 10000 }  // Explicit timeout with reason
  );
  
  await page.goto('/map');
  
  // Wait for API to return
  const response = await responsePromise;
  const data = await response.json();
  
  // Now we KNOW data is loaded, safe to check DOM
  await expect(page.locator('.leaflet-marker')).toHaveCount(data.count);
});
```

### Pattern 2: Wait for DOM Element

```javascript
test('should render map controls', async ({ page }) => {
  await page.goto('/map');
  
  // Wait for map library to initialize
  await expect(page.locator('.leaflet-container')).toBeVisible();
  
  // Wait for zoom controls specifically
  await expect(page.locator('.leaflet-control-zoom')).toBeVisible();
  
  // Now safe to interact
  await page.click('.leaflet-control-zoom-in');
});
```

### Pattern 3: Wait for Multiple Conditions

```javascript
test('should load map with all layers', async ({ page }) => {
  await page.goto('/map');
  
  // Wait for ALL conditions in parallel
  await Promise.all([
    // API responses
    page.waitForResponse(r => r.url().includes('/api/v1/fibers/')),
    page.waitForResponse(r => r.url().includes('/api/v1/sites/')),
    
    // DOM elements
    page.locator('.leaflet-container').waitFor(),
    page.locator('.layer-control').waitFor(),
  ]);
  
  // Now everything is loaded
  const fiberCount = await page.locator('.fiber-marker').count();
  const siteCount = await page.locator('.site-marker').count();
  
  expect(fiberCount).toBeGreaterThan(0);
  expect(siteCount).toBeGreaterThan(0);
});
```

---

## 🗺️ Map-Specific Patterns

### Google Maps / Leaflet / OpenLayers

These libraries load asynchronously. Wait for their global objects:

```javascript
test('should initialize Google Maps', async ({ page }) => {
  await page.goto('/map');
  
  // Wait for Google Maps API to load
  await page.waitForFunction(() => {
    return typeof window.google !== 'undefined' && 
           typeof window.google.maps !== 'undefined';
  }, { timeout: 15000 });
  
  // Wait for map instance to be created
  await page.waitForFunction(() => {
    return window.mapInstance && window.mapInstance.getZoom() > 0;
  });
  
  // Now safe to interact with map
  const zoom = await page.evaluate(() => window.mapInstance.getZoom());
  expect(zoom).toBeGreaterThan(0);
});
```

### Leaflet Specific

```javascript
test('should load Leaflet map with tiles', async ({ page }) => {
  await page.goto('/map');
  
  // Wait for Leaflet to be ready
  await page.waitForFunction(() => window.L !== undefined);
  
  // Wait for map container
  await expect(page.locator('.leaflet-container')).toBeVisible();
  
  // Wait for tiles to load (no more "Loading..." overlay)
  await page.waitForFunction(() => {
    const loadingPanes = document.querySelectorAll('.leaflet-tile-pane img.leaflet-tile-loading');
    return loadingPanes.length === 0;
  }, { timeout: 20000 });
  
  // Map is fully loaded, can take screenshot
  await page.screenshot({ path: 'test-results/map-loaded.png' });
});
```

---

## 🎨 Fiber Route Drawing Tests

### Testing Interactive Drawing

```javascript
test('should draw fiber route between sites', async ({ page }) => {
  await page.goto('/network/design');
  
  // Wait for drawing tools
  await expect(page.locator('.draw-controls')).toBeVisible();
  
  // Click "Draw Route" button
  await page.click('button:has-text("Draw Route")');
  
  // Wait for map to enter drawing mode
  await expect(page.locator('.leaflet-container')).toHaveClass(/drawing-mode/);
  
  // Click first point
  await page.locator('.leaflet-container').click({ position: { x: 200, y: 200 } });
  
  // Wait for first marker to appear
  await expect(page.locator('.temp-route-marker')).toHaveCount(1);
  
  // Click second point
  await page.locator('.leaflet-container').click({ position: { x: 400, y: 400 } });
  
  // Wait for route line to be drawn
  await expect(page.locator('.route-polyline')).toBeVisible();
  
  // Finish drawing
  await page.click('button:has-text("Finish")');
  
  // Wait for save API call
  await page.waitForResponse(
    response => 
      response.url().includes('/api/v1/routes/') && 
      response.status() === 201
  );
  
  // Verify route was saved
  await expect(page.locator('.route-saved-toast')).toBeVisible();
});
```

---

## 📸 Visual Regression Testing

### Capture Map State for Comparison

```javascript
test('map visual regression', async ({ page }) => {
  await page.goto('/map');
  
  // Wait for everything to load
  await page.waitForResponse(r => r.url().includes('/api/v1/fibers/'));
  await page.waitForFunction(() => {
    return document.querySelectorAll('.leaflet-tile-loading').length === 0;
  });
  
  // Hide dynamic elements (timestamps, etc)
  await page.addStyleTag({
    content: '.timestamp, .last-update { display: none !important; }'
  });
  
  // Take screenshot
  await expect(page).toHaveScreenshot('map-baseline.png', {
    fullPage: false,
    clip: { x: 0, y: 0, width: 1280, height: 720 },
  });
});
```

---

## 🐛 Debugging Failed Tests

### Save Context on Failure

```javascript
// playwright.config.js
export default {
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },
};
```

### Add Debug Logging

```javascript
test('should load fibers', async ({ page }) => {
  // Log network activity
  page.on('response', response => {
    if (response.url().includes('/api/')) {
      console.log(`API: ${response.status()} ${response.url()}`);
    }
  });
  
  // Log console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.error(`Browser error: ${msg.text()}`);
    }
  });
  
  await page.goto('/map');
  // ... rest of test
});
```

---

## 📋 Complete Example: Before & After

### ❌ BEFORE (Fragile Test)
```javascript
test('fiber map loads', async ({ page }) => {
  await page.goto('/map');
  await page.waitForTimeout(8000);  // Hope everything loads
  
  const count = await page.locator('.fiber').count();
  expect(count).toBeGreaterThan(0);  // Flaky - might be 0 if slow
});
```

### ✅ AFTER (Robust Test)
```javascript
test('fiber map loads with all data', async ({ page }) => {
  // 1. Setup response interceptor
  const fibersPromise = page.waitForResponse(
    r => r.url().includes('/api/v1/fibers/') && r.status() === 200
  );
  
  // 2. Navigate
  await page.goto('/map');
  
  // 3. Wait for API
  const fibersResponse = await fibersPromise;
  const fibersData = await fibersResponse.json();
  
  // 4. Wait for DOM to reflect API data
  await expect(page.locator('.fiber-marker')).toHaveCount(fibersData.count, {
    timeout: 10000
  });
  
  // 5. Wait for map tiles
  await page.waitForFunction(() => {
    return document.querySelectorAll('.leaflet-tile-loading').length === 0;
  });
  
  // 6. Now verify UI matches data
  const visibleFibers = await page.locator('.fiber-marker:visible').count();
  expect(visibleFibers).toBe(fibersData.count);
  
  // 7. Take screenshot for visual verification
  await page.screenshot({ path: 'test-results/fiber-map.png' });
});
```

---

## 🎯 Best Practices Summary

| Do This ✅ | Not This ❌ |
|-----------|------------|
| `await page.waitForResponse(...)` | `await page.waitForTimeout(5000)` |
| `await expect(element).toBeVisible()` | `await page.waitForTimeout(1000)` |
| `await page.waitForFunction(...)` | Assume things loaded |
| `timeout: 10000` with reason | Magic numbers |
| Check actual data count | Assume "some" data |

---

## 🚀 Run Tests

```bash
# Run all tests
npm run test:e2e

# Run only map tests
npx playwright test map.spec.js

# Debug mode (opens browser)
npx playwright test --debug

# Update screenshots (visual regression)
npx playwright test --update-snapshots
```

---

**Last Updated**: November 18, 2025  
**Status**: 🎯 Ready to implement  
**Next Action**: Update existing tests in `frontend/tests/e2e/`
