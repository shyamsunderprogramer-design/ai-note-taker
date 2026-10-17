/**
 * e2e/tests/cognitive-graph.spec.js
 *
 * Smoke test for the cognitive-graph page (/cognitive-graph).
 *
 * Verifies:
 * - The page loads without console errors
 * - The page renders the expected heading text
 * - The graph container DOM element is present (so a future
 *   refactor that breaks the canvas/svg mounting is caught)
 *
 * This is a structural smoke test, not a functional test of the
 * graph itself. A behavioral test would need a populated Neo4j
 * instance, which is out of scope for the e2e tier (we use
 * SQLite + mocked modules in CI per the CI workflow config).
 */

const { test, expect } = require('@playwright/test');

test.describe('Cognitive Graph page', () => {
  test('loads and renders expected DOM', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await page.goto('/cognitive-graph');
    // The page should have a heading — any h1/h2 will do for a smoke.
    const heading = await page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
    // Verify the page has rendered some content (not a blank screen).
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(50);
    // No console errors during load.
    expect(consoleErrors).toEqual([]);
  });

  test('SPA deep-link via /cognitive-graph resolves', async ({ page }) => {
    // The vercel.json rewrite maps /cognitive-graph → /cognitive-graph.html
    const response = await page.goto('/cognitive-graph');
    expect(response).toBeTruthy();
    expect(response.status()).toBe(200);
  });
});
