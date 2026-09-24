import { chromium } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const page = browser.contexts()[0].pages().find(p => /index.html/.test(p.url()));
if (!page) throw new Error('Sign in is required in the visible app');
await page.bringToFront();
await page.reload();
await page.waitForFunction(() => typeof isProcessing === 'boolean');
const errors=[];
page.on('pageerror', e => errors.push(e.message));
const results=[];
for (const item of [
  { model:'groq-gpt-oss-120b', name:'explicit-cloud', question:'LIVE CHECK: Extract only pending actions from this meeting: Elena will send the invoice Tuesday. Marcus will check the contract, with no deadline stated. The launch checklist needs updating by Thursday; nobody is assigned. Lee already sent the draft. Keep each owner and deadline separate.' },
  { model:'auto', name:'auto-cloud', question:'LIVE CHECK: A container was OOMKilled. Must its liveness probe fail before Kubernetes can restart it? Explain briefly and account for restartPolicy.' },
]) {
  await page.waitForFunction(() => !isProcessing);
  await page.locator('#modelSelect').selectOption(item.model);
  await page.locator('#textInput').fill(item.question);
  await page.screenshot({path:`/tmp/ant-visible-desktop/${item.name}-question.png`});
  const before=await page.locator('.chat-message.assistant').count();
  const start=Date.now();
  await page.locator('#textInput').press('Enter');
  await page.waitForFunction(count => document.querySelectorAll('.chat-message.assistant').length > count, before, {timeout:20000});
  await page.waitForFunction(() => !isProcessing, {}, {timeout:90000});
  const answer=await page.locator('.chat-message.assistant').last().innerText();
  await page.waitForTimeout(300);
  const scroll = await page.evaluate(() => ({ following: followChatOutput, distanceFromBottom: chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight }));
  const result={name:item.name,selected:item.model,seconds:(Date.now()-start)/1000,answer,scroll};
  if (scroll.distanceFromBottom > 40) throw new Error("Newest answer is not visible: " + JSON.stringify(scroll));
  results.push(result);
  await page.screenshot({path:`/tmp/ant-visible-desktop/${item.name}-answer.png`});
  await writeFile('/tmp/ant-visible-desktop/results.json',JSON.stringify({results,errors},null,2));
  console.log(JSON.stringify(result));
  await page.waitForTimeout(4000);
}
await browser.close();
