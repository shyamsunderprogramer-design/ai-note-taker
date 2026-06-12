/**
 * e2e/tests/job-tracker.spec.js
 *
 * Smoke test for the job-tracker page (/job-tracker).
 */

const { test, expect } = require('@playwright/test');

test.describe('Job Tracker page', () => {
  test('loads and renders expected DOM', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await page.goto('/job-tracker');
    const heading = await page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(50);
    expect(consoleErrors).toEqual([]);
  });

  test('deep-link resolves with HTTP 200', async ({ page }) => {
    const response = await page.goto('/job-tracker');
    expect(response.status()).toBe(200);
  });
});
