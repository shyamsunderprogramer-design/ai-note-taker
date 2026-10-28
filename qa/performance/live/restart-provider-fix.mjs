import { chromium, _electron as electron } from '@playwright/test';
import { resolve } from 'node:path';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const old = browser.contexts().flatMap(c => c.pages()).find(p => /index.html/.test(p.url()));
if (!old) throw new Error('ANT main window unavailable');
const state = await old.evaluate(() => {
  if (isProcessing || isListening) throw new Error('ANT is busy; restart deferred');
  return { key: document.getElementById('configApiKeyInput').value, provider: activeProvider, draft: document.getElementById('textInput').value };
});
await old.evaluate(() => { window.api.closeWindow(); }).catch(() => {});
await browser.close().catch(() => {});
await new Promise(r => setTimeout(r, 2000));
const app = await electron.launch({ args: ['--remote-debugging-port=9223', resolve('electron/main.js')], timeout: 60000 });
let page;
for (let i=0;i<120;i++) {
  page=app.windows().find(p=>/index.html/.test(p.url()));
  if(page) break;
  await new Promise(r=>setTimeout(r,500));
}
if(!page) { console.log('ANT restarted; sign-in required. Unsaved key remains in this process memory.'); await new Promise(r=>setTimeout(r,60000)); page=app.windows().find(p=>/index.html/.test(p.url())); }
if (!page) throw new Error('No main window after restart');
await page.waitForFunction(()=>typeof openProviderConfig==='function');
await page.evaluate(s=>{
  document.getElementById('textInput').value=s.draft;
  document.getElementById('gearBtn').click();
  document.querySelector('.settings-tab[data-tab="providers"]').click();
  openProviderConfig(s.provider || 'google');
  document.getElementById('configApiKeyInput').value=s.key;
},state);
console.log(JSON.stringify(await page.evaluate(()=>({updatedValidator:validateApiKeyFormat('google','AQ.'+'x'.repeat(300)),keyRestored:!!document.getElementById('configApiKeyInput').value,hint:getApiKeyHint('google')}))));
state.key='';
await page.bringToFront();
await new Promise(r=>app.on('close',r));
