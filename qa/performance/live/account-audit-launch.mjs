// Real Electron, real backend, test-account login. Never record credentials.
import { _electron as electron } from '@playwright/test';
import { readFile, unlink, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';
import { createWriteStream } from 'node:fs';
const out = '/tmp/ant-account-audit';
const credentials = JSON.parse(await readFile(`${out}/credentials.json`, 'utf8'));
await unlink(`${out}/credentials.json`);
const app = await electron.launch({
  args: ['--remote-debugging-port=9223', `--user-data-dir=${out}/profile`, resolve('electron/main.js')],
  timeout: 60000,
});
let page;
for (let i=0; i<120; i++) {
  page = app.windows().find(p => p.url().includes('signin.html') || p.url().includes('index.html'));
  if (page) break;
  await new Promise(resolve => setTimeout(resolve,500));
}
if (!page) throw new Error('No app login window opened');
await page.waitForLoadState('domcontentloaded');
if (page.url().includes('signin.html')) {
  await page.waitForFunction(async()=>{try{return (await fetch((window.API_BASE || 'http://127.0.0.1:8000')+'/health')).ok;}catch{return false;}},{},{timeout:60000});
  await page.locator('#siUser').fill(credentials.username);
  await page.locator('#siPass').fill(credentials.password);
  await page.locator('#siBtn').click();
  try { await page.waitForURL('**/index.html', {timeout:60000}); }
  catch {
    const message = await page.locator('#siError').innerText().catch(()=> 'Login failed');
    await writeFile(`${out}/login.json`, JSON.stringify({passed:false,message}));
    console.log(JSON.stringify({login:false,message}));
  }
}
credentials.password = '';
if (page.url().includes('index.html')) {
  await page.waitForTimeout(1500);
  await page.screenshot({path:`${out}/desktop.png`});
  const result = {passed:true,page:page.url().split('/').pop(),title:await page.title()};
  await writeFile(`${out}/login.json`, JSON.stringify(result));
  console.log(JSON.stringify({login:true,title:result.title}));
}
console.log('Audit desktop available on local CDP port 9223');
if (process.argv.includes('--verify') || process.argv.includes('--ocr-only')) {
  await page.waitForURL('**/index.html', {timeout:60000});
  for (const mode of (process.argv.includes('--ocr-only') ? ['ocr-check'] : ['core','desktop'])) {
    const output=createWriteStream(`/tmp/ant-final-${mode}.log`);
    const child=spawn(process.execPath,['qa/performance/live/account-audit.mjs',mode],{stdio:['ignore','pipe','pipe']});
    child.stdout.pipe(output);child.stderr.pipe(output);
    const code=await new Promise(resolve=>child.on('close',resolve));
    output.end();console.log(JSON.stringify({check:mode,exitCode:code}));
    if(code!==0) break;
  }
}

await new Promise(resolve => app.on('close', resolve));
