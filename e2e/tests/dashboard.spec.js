const { test, expect } = require('@playwright/test');

test.describe('ANT AI Note Taker - Dashboard', () => {
  test('index page loads', async ({ page }) => {
    const response = await page.goto('/index.html');
    expect(response.status()).toBe(200);
    await expect(page).not.toHaveTitle(/Error response/i);
    await expect(page).toHaveTitle(/ANT|Dashboard|Note Taker/i);
  });

  test('navigation links are present', async ({ page }) => {
    const response = await page.goto('/index.html');
    expect(response.status()).toBe(200);
    await expect(page).not.toHaveTitle(/Error response/i);
    const body = await page.locator('body').textContent();
    expect(body).toMatch(/interview|tracker|analytics|settings/i);
  });
});
