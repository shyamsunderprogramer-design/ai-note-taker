// Isolated saved-chat UI acceptance: synthetic conversations, no user data.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
const dist = resolve('apps/web/dist');
const server = createServer(async (req, res) => {
  const file = resolve(dist, '.' + new URL(req.url, 'http://localhost').pathname);
  if (!file.startsWith(dist + '/')) return res.writeHead(404).end();
  try { res.setHeader('Content-Type', ({'.html':'text/html','.js':'application/javascript','.css':'text/css'})[extname(file)] || 'application/octet-stream'); res.end(await readFile(file)); }
  catch { res.writeHead(404).end(); }
});
await new Promise(done => server.listen(0, '127.0.0.1', done));
let browser;
try {
  browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:960,height:720}});
  const errors = []; page.on('pageerror', e => {errors.push(e.message); console.error(e.message);});
  const origin = `http://127.0.0.1:${server.address().port}`;
  await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : (new URL(route.request().url()).pathname === '/auth/status' ? route.fulfill({json:{auth_required:false}}) : route.fulfill({status:503,json:{detail:'Isolated test'}})));
  await page.addInitScript(() => localStorage.setItem('hasOnboarded', 'true'));
  await page.goto(origin + '/index.html');
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => {
    window.api = {autoScreenshotSetEnabled: async () => {}};
    window.historyFixtures = Array.from({length:125}, (_, i) => ({
      id:`chat-${i}`, title: i === 0 ? 'Platform engineer interview preparation' : `Interview practice ${i}`,
      preview:'Discussed system design, delivery experience, and follow-up questions.',
      updatedAt:Date.now()-i*3600000, createdAt:Date.now()-i*3600000, pinned:i===0,
      messageCount:2, messages:[{role:'user',text:i===124 ? 'Older archived lighthouse discussion' : `Practice question ${i}`}]
    }));
    window.api.conversationList = async () => historyFixtures;
    window.api.conversationLoad = async id => historyFixtures.find(c => c.id===id);
    window.api.conversationSave = async c => { historyFixtures[historyFixtures.findIndex(x=>x.id===c.id)] = c; return c; };
    toggleHistoryPanel();
  });
  await page.waitForSelector('.history-item');
  await page.waitForTimeout(250);
  assert.equal(await page.locator('.history-item').count(),101);
  await page.screenshot({path:'/tmp/ant-history-desktop.png'});
  await page.locator('.history-load-more').click();
  await page.waitForFunction(() => document.querySelectorAll('.history-item').length === 125);
  await page.locator('#historySearch').fill('lighthouse');
  await page.waitForFunction(() => document.querySelectorAll('.history-item').length === 1);
  assert.match(await page.locator('.history-item').innerText(), /lighthouse/);
  await page.locator('#historySearch').fill('no-such-conversation');
  await page.waitForSelector('.history-empty');
  assert.match(await page.locator('.history-empty').innerText(), /No matches/);
  await page.locator('#historySearch').fill('');
  await page.locator('#historySort').selectOption('createdAt');
  await page.waitForFunction(() => document.querySelectorAll('.history-item')[1]?.dataset.id === 'chat-124');
  await page.locator('#historySort').selectOption('title');
  await page.waitForFunction(() => document.querySelectorAll('.history-item')[2]?.dataset.id === 'chat-10');
  await page.locator('#historySort').selectOption('createdAt');
  await page.waitForFunction(() => document.querySelectorAll('.history-item')[1]?.dataset.id === 'chat-124');
  await page.setViewportSize({width:390,height:640});
  await page.screenshot({path:'/tmp/ant-history-mobile.png'});
  assert.equal(await page.evaluate(() => {const r=historyPanel.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth && historyPanel.scrollWidth<=historyPanel.clientWidth;}),true);
  await page.locator('.history-item').nth(1).focus();
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => !historyPanel.classList.contains('open'));
  assert.equal(await page.evaluate(() => currentConversationId),'chat-124');
  await page.evaluate(() => toggleHistoryPanel());
  await page.locator('#historySearch').press('Escape');
  assert.equal(await page.evaluate(() => historyPanel.inert), true);
  await page.evaluate(() => {
    window.deletedFixtureIds = [];
    window.failFixtureDelete = true;
    window.api.conversationDelete = async id => {
      if (id === 'chat-0' && failFixtureDelete) return false;
      deletedFixtureIds.push(id);
      historyFixtures = historyFixtures.filter(c => c.id !== id);
      return true;
    };
    toggleHistoryPanel();
  });
  await page.locator('#deleteAllChatsBtn').click();
  assert.match(await page.locator('#deleteAllChatsDescription').innerText(), /125/);
  await page.locator('#deleteAllChatsCancel').click();
  assert.equal(await page.evaluate(() => deletedFixtureIds.length), 0);
  await page.evaluate(() => { if (!historyPanel.classList.contains('open')) toggleHistoryPanel(); });
  await page.locator('#historySearch').fill('lighthouse');
  await page.waitForFunction(() => document.querySelectorAll('.history-item').length === 1);
  await page.locator('#deleteAllChatsBtn').click();
  assert.match(await page.locator('#deleteAllChatsDescription').innerText(), /125/);
  await page.locator('#deleteAllChatsConfirm').click();
  await page.waitForFunction(() => document.getElementById('deleteAllChatsError').textContent.includes('1 could not'));
  assert.equal(await page.evaluate(() => historyFixtures.length), 1);
  assert.equal(await page.evaluate(() => currentConversationId), null);
  await page.evaluate(() => { failFixtureDelete = false; });
  await page.locator('#deleteAllChatsConfirm').click();
  await page.waitForFunction(() => !document.getElementById('deleteAllChatsDialog').open);
  assert.equal(await page.evaluate(() => historyFixtures.length), 0);
  console.log('PASS: bulk-delete cancellation, full count under search, partial failure/retry, and active-chat reset.');
  assert.deepEqual(errors, []);
  console.log('PASS: previews, all-chat search, pagination, oldest sort, keyboard open/close, 390px layout.');
} finally { await browser?.close(); await new Promise(done=>server.close(done)); }
