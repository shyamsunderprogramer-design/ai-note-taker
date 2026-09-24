import { chromium } from '@playwright/test';
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
const page=browser.contexts()[0].pages().find(p=>/index.html/.test(p.url()));
await page.evaluate(()=>window.api.closeWindow()).catch(()=>{});
await browser.close().catch(()=>{});
