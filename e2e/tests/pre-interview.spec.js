/**
 * e2e/tests/pre-interview.spec.js
 *
 * Smoke test for the pre-interview prep page (/pre-interview).
 */

const { test, expect } = require('@playwright/test');

test.describe('Pre-Interview page', () => {
  test('loads and renders expected DOM', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await page.goto('/pre-interview');
    const heading = await page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(50);
    expect(consoleErrors).toEqual([]);
  });

  test('deep-link resolves with HTTP 200', async ({ page }) => {
    const response = await page.goto('/pre-interview');
    expect(response.status()).toBe(200);
  });
});
