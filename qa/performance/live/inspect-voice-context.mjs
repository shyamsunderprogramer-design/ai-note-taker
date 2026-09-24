import {chromium} from '@playwright/test';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
const page=browser.contexts()[0].pages().find(p=>/index.html/.test(p.url()));
const data=await page.evaluate(async()=>{
 const node=[...document.querySelectorAll('.chat-message.user')].at(-1);
 const image=node?.querySelector('.screenshot-indicator')?.dataset.fullB64;
 const text=image?(await runOcr(image)).text:'';
 return {image,screenText:text,microphoneActive:isListening,processing:isProcessing};
});
if(data.image)await writeFile('/tmp/ant-visible-desktop/actual-voice-context.jpg',Buffer.from(data.image,'base64'));
console.log(JSON.stringify({hasScreen:!!data.image,fixturePresent:/Cedar/.test(data.screenText||''),appExcluded:!/AI Note Taker|Protection off|Summarize|Ask anything/.test(data.screenText||''),microphoneActive:data.microphoneActive,processing:data.processing}));
await browser.close();
