// Launch the real desktop with its normal profile; keep it open for user observation.
import { _electron as electron } from '@playwright/test';
import { resolve } from 'node:path';
import { mkdir } from 'node:fs/promises';
await mkdir('/tmp/ant-visible-desktop', { recursive: true });
// Launch the package directory, as `npm run electron:start` does. A bare main.js
// gives Electron its default app name and selects a different userData profile.
const app = await electron.launch({ env:{...process.env, ANT_ENABLE_LOCAL_QA:'1'}, args: ['--remote-debugging-port=9223', resolve('electron')], timeout: 60000 });
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
console.log(JSON.stringify(await app.evaluate(({app})=>({appName:app.getName(),profile:app.getPath('userData')}))));
await new Promise(resolve => app.on('close', resolve));
