import { chromium } from '@playwright/test';
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
const page=browser.contexts()[0].pages().find(p=>/index.html/.test(p.url()));
console.log(await page.evaluate(()=>({scrollTop:chatArea.scrollTop,scrollHeight:chatArea.scrollHeight,height:chatArea.clientHeight,following:followChatOutput,processing:isProcessing})));
await page.evaluate(async()=>{if(!await window.api.isWindowMaximized()) await window.api.toggleMaximizeWindow();});
await page.locator('.chat-message.assistant').last().scrollIntoViewIfNeeded();
await page.screenshot({path:'/tmp/ant-visible-desktop/current.png'});
await browser.close();
