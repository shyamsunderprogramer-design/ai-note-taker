// Launch the real desktop with its normal profile; keep it open for user observation.
import { _electron as electron } from '@playwright/test';
import { resolve } from 'node:path';
import { mkdir } from 'node:fs/promises';
await mkdir('/tmp/ant-visible-desktop', { recursive: true });
const app = await electron.launch({ args: ['--remote-debugging-port=9223', resolve('electron/main.js')], timeout: 60000 });
let page;
for (let attempt = 0; attempt < 120; attempt++) {
  page = app.windows().find(p => /signin.html|index.html/.test(p.url()));
  if (page) break;
  await new Promise(r => setTimeout(r, 500));
}
if (!page) throw new Error('Desktop window did not appear');
await page.waitForLoadState('domcontentloaded');
await app.evaluate(({ BrowserWindow }) => {
  const win = BrowserWindow.getAllWindows().find(w => /signin.html|index.html/.test(w.webContents.getURL()));
  if (win) { win.show(); win.focus(); }
});
await page.screenshot({ path: '/tmp/ant-visible-desktop/initial.png' });
console.log(JSON.stringify({ page: page.url().split('/').pop(), title: await page.title(), visible: true }));
await new Promise(resolve => app.on('close', resolve));
