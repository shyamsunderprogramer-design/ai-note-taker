// Visible navigation; --demo submits one clearly labeled sample through the UI.
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const page = browser.contexts().flatMap(context => context.pages()).find(page => /\/index.html/.test(page.url()) || (process.argv.includes('--responsiveness') && /\/signin.html/.test(page.url())));
if (!page) throw new Error('Sign in to the visible ANT app first.');
const output = '/tmp/ant-live-tour';
await mkdir(output, { recursive: true });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.bringToFront();
  console.log(JSON.stringify(await page.evaluate(() => ({
    screen: document.title,
    backend: document.getElementById('backendStatusIndicator')?.title,
    selectedModel: document.getElementById('modelSelect')?.value,
    processing: typeof isProcessing === 'boolean' ? isProcessing : null,
    installedOptions: Array.from(document.querySelectorAll('#ollamaLocalGroup option')).map(option => ({id:option.value,disabled:option.disabled})),
  }))));
  await page.screenshot({path:output+'/main.png'});
  if (process.argv.includes('--responsiveness')) {
    const started=Date.now();
    if (/\/signin.html/.test(page.url())) {
      await page.locator('#siUser').focus();
      console.log(JSON.stringify(await page.evaluate(()=>({screen:'sign-in',inputFocused:document.activeElement===document.getElementById('siUser'),signInEnabled:!document.getElementById('siBtn').disabled}))));
    } else {
    await page.locator('#gearBtn').click({timeout:5000});
    await page.locator('#settingsPanel.open').waitFor({state:'visible',timeout:5000});
    await page.waitForTimeout(1000);
    await page.locator('#closeSettingsBtn').click({timeout:5000});
    await page.locator('#textInput').focus();
    const state=await page.evaluate(()=>({inputFocused:document.activeElement===document.getElementById('textInput'),processing:isProcessing}));
    console.log(JSON.stringify({settingsOpenedAndClosed:true,...state,seconds:(Date.now()-started)/1000}));
    }
  }
  else if (process.argv.includes('--observe')) {
    await page.waitForFunction(() => !isProcessing, null, {timeout:90000});
    const result = await page.evaluate(() => {
      const message = [...document.querySelectorAll('.chat-message.assistant')].at(-1);
      const answer = message?.querySelector('.msg-bubble')?.textContent || '';
      return {processing:isProcessing,provider:message?.querySelector('.model-badge')?.textContent,
        status:message?.querySelector('.recovery-status')?.textContent || '',characters:answer.length,
        mentionsLIFO:/LIFO/i.test(answer),mentionsFIFO:/FIFO/i.test(answer),
        visibleError:[...document.querySelectorAll('.error-message')].at(-1)?.textContent || ''};
    });
    await page.screenshot({path:output+'/demo-result.png'});
    await writeFile(output+'/demo-result.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  }
  else if (process.argv.includes('--demo')) {
    const safe = await page.evaluate(() => !isProcessing && !document.getElementById('textInput').value.trim() && !document.querySelector('.chat-message'));
    if (!safe) throw new Error('Demo requires an idle, empty chat so existing work is preserved.');
    const prompt = 'LIVE DEMO: Explain the difference between a stack and a queue in three short bullets. Include LIFO, FIFO, and one practical example of each.';
    await page.locator('#textInput').fill(prompt);
    await page.waitForTimeout(2500);
    const started = Date.now();
    await page.locator('#textInput').press('Enter');
    await page.waitForFunction(() => document.querySelector('.chat-message.assistant'), null, {timeout:30000});
    await page.waitForFunction(() => !isProcessing, null, {timeout:90000});
    const result = await page.evaluate(() => {
      const message = [...document.querySelectorAll('.chat-message.assistant')].at(-1);
      const answer = message?.querySelector('.msg-bubble')?.textContent || '';
      return {provider:message?.querySelector('.model-badge')?.textContent,
        status:message?.querySelector('.recovery-status')?.textContent || '',
        characters:answer.length,mentionsLIFO:/LIFO/i.test(answer),mentionsFIFO:/FIFO/i.test(answer)};
    });
    result.seconds = (Date.now()-started)/1000;
    await page.locator('.chat-message.assistant').last().scrollIntoViewIfNeeded();
    await page.screenshot({path:output+'/demo.png'});
    await writeFile(output+'/demo.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  }
  else if (process.argv.includes('--inspect')) process.exitCode = 0;
  else {
    if (!process.argv.includes('--finish')) {
    await page.waitForTimeout(4000);
    await page.locator('#gearBtn').click();
    for (const tab of ['general','providers','models','voice','clone','data','integrations']) {
      await page.locator(`.settings-tab[data-tab="${tab}"]`).click();
      await page.locator(`.settings-tab-content[data-content="${tab}"]`).waitFor({state:'visible'});
      console.log('Showing settings: '+tab);
      await page.waitForTimeout(5000);
    }
    await page.locator('#closeSettingsBtn').click();
    }
    if (!await page.locator('#appMenu').evaluate(element=>element.classList.contains('open'))) await page.locator('#menuBtn').click();
    await page.locator('.app-menu-item[data-action="history"]').click();
    await page.locator('#historyPanel').waitFor({state:'visible'});
    console.log('Showing saved conversations');
    await page.waitForTimeout(5000);
    await page.locator('#historyBackBtn').click();
    await page.locator('#shortcutsInfoBtn').click();
    console.log('Showing keyboard shortcuts');
    await page.waitForTimeout(5000);
    await page.locator('#shortcutsInfoBtn').click();
    console.log('Returned to main screen');
  }
  await writeFile(output+'/navigation.json',JSON.stringify({errors,completed:!process.argv.includes('--inspect')},null,2));
  console.log(JSON.stringify({errors}));
} finally { await browser.close(); }
