/**
 * e2e/tests/analytics-dashboard.spec.js
 *
 * Smoke test for the analytics-dashboard page (/analytics-dashboard).
 */

const { test, expect } = require('@playwright/test');

test.describe('Analytics Dashboard page', () => {
  test('loads and renders expected DOM', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    const response = await page.goto('/analytics-dashboard');
    expect(response.status()).toBe(200);
    await expect(page).not.toHaveTitle(/Error response/i);
    const heading = await page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(50);
    await expect(page.locator('#loadingState')).toContainText('Analytics is unavailable');
    await expect(page.getByRole('button', { name: 'Check again' })).toBeVisible();
    await expect(page.locator('#dashboardContent')).toBeHidden();
    expect(consoleErrors).toEqual([]);
  });

  test('deep-link resolves with HTTP 200', async ({ page }) => {
    const response = await page.goto('/analytics-dashboard');
    expect(response.status()).toBe(200);
  });
});
