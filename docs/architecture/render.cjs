// Rasterize the editable SVG for the README using the existing E2E dependency.
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function main() {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 1280, height: 960 },
      deviceScaleFactor: 2,
    });
    await page.goto(pathToFileURL(path.join(__dirname, 'overview.svg')).href);
    await page.locator('svg').screenshot({ path: path.join(__dirname, 'overview.png') });
    console.log('Rendered docs/architecture/overview.png');
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
