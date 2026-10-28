import { chromium } from 'playwright';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const output = '/tmp/ant-overlay-verification';
fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ headless: false });
const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
await context.addInitScript(() => { window.API_BASE = 'http://127.0.0.1:8046'; });
const results = [];
try {
  for (const file of ['caption-overlay.html', 'interview-overlay.html']) {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.join(root, 'apps/web', file)).href);
    await page.waitForFunction(() => document.getElementById('statusText')?.textContent === 'Live', { timeout: 15000 });
    if (errors.length) throw new Error(errors.join('\n'));
    await page.screenshot({ path: path.join(output, file + '.png') });
    results.push({ page: file, protocol: 'file:', status: 'Live', errors });
    console.log(JSON.stringify(results.at(-1)));
  }
  fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(results, null, 2));
  console.log('Both overlay windows are open for review. Close the browser to finish.');
  await new Promise(resolve => browser.on('disconnected', resolve));
} catch (error) {
  await browser.close();
  throw error;
}
