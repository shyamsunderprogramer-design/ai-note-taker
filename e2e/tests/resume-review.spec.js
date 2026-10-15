/**
 * e2e/tests/resume-review.spec.js
 *
 * Smoke test for the resume-review page (/resume-review) and
 * resume-review-v2 (/resume-review-v2). Both pages exist in
 * the SPA (the v2 was added later as a redesign); this test
 * verifies both load.
 */

const { test, expect } = require('@playwright/test');

for (const path of ['/resume-review', '/resume-review-v2']) {
  test(`${path} loads and renders expected DOM`, async ({ page }) => {
    const consoleErrors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await page.goto(path);
    const heading = await page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(50);
    expect(consoleErrors).toEqual([]);
  });
}
