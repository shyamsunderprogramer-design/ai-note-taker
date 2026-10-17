// @ts-check
const { defineConfig, devices } = require('@playwright/test');
const path = require('node:path');
const fs = require('node:fs');
const root = path.resolve(__dirname, '..');
const localPython = path.join(root, 'AINT_Venv/bin/python');
const python = process.env.ANT_TEST_PYTHON || (fs.existsSync(localPython) ? localPython : 'python3');
const quote = value => "'" + value.replace(/'/g, "'\\''") + "'";

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://127.0.0.1:8048',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],
  webServer: [
    {
      command: `${quote(python)} ${quote(path.join(root, 'qa/performance/backend/isolated.py'))} serve --port 8049`,
      url: 'http://127.0.0.1:8049/health',
      reuseExistingServer: false,
      timeout: 120 * 1000,
    },
    {
      command: `${quote(python)} ${quote(path.join(root, 'e2e/serve.py'))} --port 8048 --api http://127.0.0.1:8049`,
      url: 'http://127.0.0.1:8048',
      reuseExistingServer: false,
      timeout: 30 * 1000,
    },
  ],
});
