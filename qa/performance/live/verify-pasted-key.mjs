import {chromium} from '@playwright/test';
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
try {
 const page=browser.contexts().flatMap(c=>c.pages()).find(p=>/index.html/.test(p.url()));
 const ready=await page.evaluate(()=>activeProvider==='google' && !!document.getElementById('configApiKeyInput').value && !document.getElementById('configSaveBtn').disabled);
 if(!ready) throw new Error('Google key field not ready; left unchanged');
 await page.locator('#configSaveBtn').click();
 await page.waitForFunction(()=>!document.getElementById('configSaveBtn').disabled,null,{timeout:45000});
 console.log(JSON.stringify(await page.evaluate(()=>({result:document.getElementById('configTestResult').textContent,success:document.getElementById('configTestResult').classList.contains('success')}))));
} finally {await browser.close()}
