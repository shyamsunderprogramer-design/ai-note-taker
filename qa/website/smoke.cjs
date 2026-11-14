/* Isolated marketing-page checks. No real app accounts, backend or provider calls. */
const { chromium } = require('@playwright/test');
const { default: AxeBuilder } = require(process.env.ANT_AXE_MODULE || '@axe-core/playwright');
const { spawn } = require('node:child_process');
const { mkdtemp, writeFile } = require('node:fs/promises');
const { tmpdir } = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const base = process.env.ANT_SITE_URL || 'http://127.0.0.1:4178';
const tags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
(async () => {
  const artifacts = await mkdtemp(path.join(tmpdir(), 'ant-website-'));
  let server, browser;
  const report = { base, artifacts, views: [], checks: [] };
  try {
    if (!process.env.ANT_SITE_URL) {
      server = spawn(process.execPath, ['scripts/preview-site.mjs'], { cwd: root, stdio: ['ignore', 'pipe', 'inherit'] });
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Preview startup timed out')), 10000);
        server.once('error', reject);
        server.once('exit', code => { clearTimeout(timer); reject(new Error(`Preview exited: ${code}`)); });
        server.stdout.once('data', () => { clearTimeout(timer); resolve(); });
      });
    }
    browser = await chromium.launch({ ...(process.env.ANT_BROWSER_CHANNEL ? {channel: process.env.ANT_BROWSER_CHANNEL} : {}) });
    for (const theme of ['light', 'dark']) {
      for (const width of [1440, 390, 320]) {
        const context = await browser.newContext({ viewport: {width, height: width === 1440 ? 900 : 844}, colorScheme: theme, reducedMotion: 'reduce' });
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', e => errors.push(e.message));
        page.on('response', r => { if (r.url().startsWith(base) && r.status() >= 400) errors.push(`${r.status()}: ${r.url()}`); });
        const response = await page.goto(base, {waitUntil: 'networkidle'});
        assert.equal(response.status(), 200);
        assert.equal(await page.locator('h1').count(), 1);
        assert(await page.locator('#source-updates').innerText().then(t => t.includes('available from source')));
        assert(await page.locator('#privacy').innerText().then(t => t.includes('Universal screenshot invisibility is not guaranteed')));
        assert.equal(await page.locator('a[href="/app"]').count(), 0);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
        assert.equal(overflow, false, `${theme}/${width} horizontal overflow`);
        await page.keyboard.press('Tab');
        assert.equal(await page.locator(':focus').textContent(), 'Skip to content');
        await page.keyboard.press('Enter');
        assert.equal(await page.locator(':focus').getAttribute('id'), 'main');
        if (width < 851) {
          await page.locator('.menu-toggle').focus();
          await page.keyboard.press('Enter');
          assert.equal(await page.locator('.menu-toggle').getAttribute('aria-expanded'), 'true');
          await page.screenshot({path:path.join(artifacts,`${theme}-${width}-menu.png`)});
          const menuAxe = await new AxeBuilder({page}).withTags(tags).analyze();
          assert.deepEqual(menuAxe.violations.map(v => ({id:v.id,nodes:v.nodes.map(n=>n.target)})), [], 'Open-menu accessibility');
          await page.keyboard.press('Escape');
          assert.equal(await page.locator('.menu-toggle').getAttribute('aria-expanded'), 'false');
          assert.equal(await page.locator(':focus').getAttribute('class'), 'menu-toggle');
        }
        await page.locator('#tab-meeting').focus();
        await page.keyboard.press('ArrowRight');
        assert.equal(await page.locator('#tab-screen').getAttribute('aria-selected'), 'true');
        assert(page.url().includes('example=screen'));
        await page.keyboard.press('End');
        assert.equal(await page.locator('#tab-practice').getAttribute('aria-selected'), 'true');
        await page.goBack();
        assert.equal(await page.locator('#tab-screen').getAttribute('aria-selected'), 'true');
        await page.locator('#tab-screen').focus();
        await page.keyboard.press('Home');
        assert.equal(await page.locator('#tab-meeting').getAttribute('aria-selected'), 'true');
        await page.locator('.faq-list summary').first().focus();
        await page.keyboard.press('Space');
        assert.equal(await page.locator('.faq-list details').first().getAttribute('open'), '');
        const axe = await new AxeBuilder({page}).withTags(tags).analyze();
        assert.deepEqual(axe.violations.map(v => ({id:v.id,nodes:v.nodes.map(n=>n.target)})), [], `${theme}/${width} accessibility`);
        const missingAnchors = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')].map(a=>a.hash.slice(1)).filter(id=>id&&!document.getElementById(id)));
        assert.deepEqual(missingAnchors, []);
        const downloads = await page.locator('.download-card a').evaluateAll(nodes=>nodes.map(n=>n.href));
        assert.equal(downloads.length, 6);
        assert.equal(new Set(downloads).size, 6);
        assert(downloads.every(url=>url.includes('/releases/download/v2.3.0-rc.2/')));
        await page.evaluate(() => { document.activeElement.blur(); scrollTo(0,0); });
        await page.screenshot({path:path.join(artifacts,`${theme}-${width}-hero.png`)});
        for (const section of ['source-updates','privacy','download']) {
          await page.locator('#'+section).scrollIntoViewIfNeeded();
          await page.screenshot({path:path.join(artifacts,`${theme}-${width}-${section}.png`)});
        }
        assert.deepEqual(errors, []);
        report.views.push({theme,width,axeViolations:0,errors,downloads:downloads.length});
        await context.close();
      }
    }
    for (const route of ['/app','/signin','/browser-app.html']) {
      const response = await fetch(base+route, {redirect:'manual'});
      assert([307,308].includes(response.status), `${route}: expected redirect`);
      assert.equal(response.headers.get('location'), '/#download');
    }
    assert.equal((await fetch(base+'/missing-asset.js')).status,404);
    assert.equal((await fetch(base+'/app.js')).status,404);
    assert.equal((await fetch(base+'/manifest.json')).status,404);
    assert.equal((await fetch(base+'/.env')).status,404);
    const headers = (await fetch(base)).headers;
    assert(headers.get('content-security-policy').includes("form-action 'none'"));
    assert(headers.get('permissions-policy').includes('microphone=()'));
    report.checks.push('Retired routes, absent app/private files, CSP and permissions headers');
    if (!process.env.ANT_SITE_URL) {
      const context = await browser.newContext();
      const page = await context.newPage();
      await page.goto(base);
      await page.route('**/sw.js', route => route.fulfill({contentType:'application/javascript',body:"self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));"}));
      await page.evaluate(async () => {
        localStorage.setItem('ant-qa-saved-note','keep');
        await caches.open('ant-cache-v5');
        await caches.open('unrelated-cache');
        await navigator.serviceWorker.register('/sw.js');
        await navigator.serviceWorker.ready;
      });
      await page.unroute('**/sw.js');
      await page.reload();
      await page.waitForFunction(async () => !(await navigator.serviceWorker.getRegistration('/')) && !(await caches.keys()).some(n=>n.startsWith('ant-cache-')));
      assert.equal(await page.evaluate(()=>localStorage.getItem('ant-qa-saved-note')), 'keep');
      assert(await page.evaluate(async () => (await caches.keys()).includes('unrelated-cache')));
      report.checks.push('Old worker retired; ANT public caches cleared; saved notes and unrelated caches preserved');
      await context.close();
    }
    await writeFile(path.join(artifacts,'report.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report,null,2));
  } finally {
    await browser?.close();
    server?.kill();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
