const { test, expect } = require('@playwright/test');

test.describe('ANT AI Note Taker - Dashboard', () => {
  test('index page loads', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page).toHaveTitle(/ANT|Dashboard|Note Taker/i);
  });

  test('navigation links are present', async ({ page }) => {
    await page.goto('/index.html');
    const body = await page.locator('body').textContent();
    expect(body).toMatch(/interview|tracker|analytics|settings/i);
  });
});
