const { test, expect } = require('@playwright/test');

test.describe('ANT AI Note Taker - Sign In Page', () => {
  test('page loads with correct title', async ({ page }) => {
    await page.goto('/signin.html');
    await expect(page).toHaveTitle(/ANT|Sign In|Login/i);
  });

  test('login form is visible', async ({ page }) => {
    await page.goto('/signin.html');
    const usernameInput = page.locator('input[name="username"], input[type="text"]').first();
    const passwordInput = page.locator('input[name="password"], input[type="password"]').first();
    await expect(usernameInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
  });

  test('invalid login shows error', async ({ page }) => {
    await page.goto('/signin.html');
    const username = page.locator('input[name="username"], input[type="text"]').first();
    const password = page.locator('input[name="password"], input[type="password"]').first();
    await username.fill('invalid_user_test');
    await password.fill('wrongpassword');
    const submit = page.locator('button[type="submit"], button:has-text("Sign In"), button:has-text("Login")').first();
    if (await submit.isVisible().catch(() => false)) {
      await submit.click();
      await page.waitForTimeout(1000);
      const errorText = await page.locator('body').textContent();
      expect(errorText).toMatch(/invalid|error|incorrect|failed/i);
    }
  });
});
