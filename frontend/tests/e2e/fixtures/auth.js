/**
 * Authentication fixture for Playwright E2E tests
 * Uses dedicated playwright_test user for E2E testing
 * 
 * Security: Separate test user from admin account
 * Isolation: Test data won't interfere with production data
 */

/**
 * Authenticate user and establish session
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {Object} credentials - Login credentials
 * @param {string} credentials.username - Username (default: 'playwright_test')
 * @param {string} credentials.password - Password (default: 'TestPlaywright123!')
 * @returns {Promise<void>}
 */
export async function authenticate(page, credentials = {}) {
  const username = credentials.username || 'playwright_test';
  const password = credentials.password || 'TestPlaywright123!';

  console.log(`🔐 Authenticating as: ${username}`);

  // Navigate to login page
  await page.goto('http://localhost:8000/accounts/login/');

  // Wait for login form to be visible
  await page.waitForSelector('#id_username', { state: 'visible', timeout: 5000 });

  // Fill credentials
  await page.fill('#id_username', username);
  await page.fill('#id_password', password);

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for redirect after successful login (should NOT be on login page)
  await page.waitForURL(url => !url.pathname.includes('/accounts/login/'), { 
    timeout: 10000,
    waitUntil: 'networkidle'
  });

  console.log('✅ Authentication successful');
}

/**
 * Check if user is authenticated
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<boolean>}
 */
export async function isAuthenticated(page) {
  try {
    const response = await page.goto('http://localhost:8000/api/config/');
    // If we get 200, we're authenticated; if 302 redirect to login, we're not
    return response.status() === 200;
  } catch (error) {
    return false;
  }
}

/**
 * Logout user
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @returns {Promise<void>}
 */
export async function logout(page) {
  await page.goto('http://localhost:8000/accounts/logout/');
  await page.waitForURL('**/accounts/login/', { timeout: 5000 });
  console.log('🚪 Logged out');
}
