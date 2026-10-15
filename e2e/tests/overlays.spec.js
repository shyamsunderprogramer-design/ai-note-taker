/**
 * e2e/tests/overlays.spec.js
 *
 * Smoke test for the floating-overlay pages used during meetings:
 *   /caption-overlay
 *   /interview-overlay
 *   /overlay
 *
 * These three pages all share the same "floating widget" use case
 * but have different DOM shapes (caption = real-time text,
 * interview = interview question overlay, overlay = generic
 * floating panel). This test verifies all three load.
 */

const { test, expect } = require('@playwright/test');

for (const path of ['/caption-overlay', '/interview-overlay', '/overlay']) {
  test(`${path} loads and renders expected DOM`, async ({ page }) => {
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    const response = await page.goto(path);
    expect(response.status()).toBe(200);
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(50);
    expect(consoleErrors).toEqual([]);
  });
}
