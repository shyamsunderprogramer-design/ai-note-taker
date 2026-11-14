import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
const origin='http://127.0.0.1:8042';
const browser=await chromium.launch({headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
try {
 const page=await browser.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(url=>{window.__API_URL__=url;localStorage.setItem('hasOnboarded','true')},origin);
 await page.goto(origin+'/index.html');await page.waitForLoadState('networkidle');
 await page.evaluate(async()=>{
   suppressAutoSave=true;
   resumeAnswerContext={name:'synthetic.md',text:'Alex built Python APIs at Acme.'};
   jobDescriptionContext='Python platform engineer';
   modelSelect.value='groq-gpt-oss-120b';
   window.api={autoScreenshotGetStatus:async()=>({enabled:false})};
 });
 const reset=()=>page.request.post(origin+'/qa/reset');
 const visible=word=>page.waitForFunction(word=>[...document.querySelectorAll('.chat-message.assistant')].at(-1)?.innerText.includes(word),word);
 await reset();
 await page.evaluate(()=>submitText('partial question'));
 await visible('Maple is $300 under budget.');
 let last=page.locator('.chat-message.assistant').last();
 assert.match(await last.innerText(),/Maple is \$300/);
 assert.equal((await last.locator('.msg-bubble').innerText()).match(/Cedar/g).length,1);
 assert.match(await last.locator('.model-badge').innerText(),/groq.*→.*openai/i);
 assert.match(await last.locator('.model-badge').getAttribute('title'),/4096 tokens/);
 assert.equal(await page.evaluate(()=>isProcessing),false);
 await page.screenshot({path:'/tmp/ant-recovery-partial.png'});
 await reset();
 // Exercise the completed recording path with synthetic audio and controlled transcription.
 await page.evaluate(()=>submitAudio(new Blob(['synthetic audio'],{type:'audio/webm'})));
 await visible('Maple is $300 under budget.');
 assert.match(await page.locator('.chat-message.assistant').last().innerText(),/Maple/);
 await reset();
 await page.evaluate(()=>submitText('quota question'));
 let events=await (await page.request.get(origin+'/qa/events')).json();
 assert.equal(events.filter(e=>e.event==='start').length,2);
 await page.evaluate(()=>submitText('next question'));
 events=await (await page.request.get(origin+'/qa/events')).json();
 assert.ok(events.filter(e=>e.event==='start').at(-1).model.startsWith('openai'));
 await reset();
 await page.evaluate(()=>{resumeAnswerContext=null; void submitText('slow question')});
 await page.waitForFunction(()=>document.querySelector('.chat-message.assistant:last-child .msg-bubble')?.textContent.includes('Old partial'));
 await page.evaluate(()=>autoSendToAI('new spoken question'));
 await visible('New answer complete');
 assert.match(await page.locator('.chat-message.assistant').last().innerText(),/New answer complete/);
 await page.waitForFunction(async()=>{const events=await(await fetch('/qa/events')).json();return events.some(e=>e.event==='closed'&&e.question.includes('slow question'))});
 assert.doesNotMatch(await page.locator('#chatArea').innerText(),/STALE ANSWER MUST NOT APPEAR/);
 await reset();
 await page.evaluate(()=>{resumeAnswerContext={name:'synthetic.md',text:'Alex built Python APIs at Acme.'};void submitText('slow question')});
 await page.waitForFunction(async()=>{const e=await(await fetch('/qa/events')).json();return e.some(x=>x.event==='start'&&x.question==='slow question')});
 await page.evaluate(()=>autoSendToAI('new spoken question'));
 await visible('New answer complete');
 await page.waitForFunction(async()=>{const e=await(await fetch('/qa/events')).json();return e.some(x=>x.event==='closed'&&x.question==='slow question')});
 assert.doesNotMatch(await page.locator('#chatArea').innerText(),/STALE ANSWER MUST NOT APPEAR/);

 await reset();
 await page.evaluate(()=>submitText('exhausted question'));
 await visible('Partial result');
 assert.match(await page.locator('.chat-message.assistant').last().innerText(),/Partial result[\s\S]*Answer incomplete/);
 assert.equal(await page.evaluate(()=>isProcessing),false);
 events=await(await page.request.get(origin+'/qa/events')).json();
 assert.equal(events.filter(e=>e.event==='start').length,3);
 assert.ok(events.filter(e=>e.event==='start').at(-1).model.includes('qa-local'));
 const preferenceCheck=await page.evaluate(async()=>{
   await appSettings.set('provider_openai',{enabled:false});
   setModelDisabled('qa-local:1b',true);
   const candidates=await recoveryCandidates('auto',null);
   await appSettings.set('provider_openai',{enabled:true});
   setModelDisabled('qa-local:1b',false);
   return candidates.every(model=>!model.startsWith('openai')&&model!=='qa-local:1b');
 });
 assert.equal(preferenceCheck,true);
 // Exercise runtime inventory as well as the unavailable-catalog legacy path above.
 const catalog={models:[
   {id:'groq-gpt-oss-120b',provider:'groq',configured:true,text:true},
   {id:'openai-gpt-4o',provider:'openai',configured:true,text:true},
   {id:'embedding:latest',provider:'ollama',configured:true,text:false},
   {id:'qa-local:1b',provider:'ollama',configured:true,text:true},
 ]};
 await page.route('**/models/catalog',route=>route.fulfill({json:catalog}));
 await page.evaluate(()=>{runtimeCatalogCache=null});
 await reset();
 await page.evaluate(()=>submitText('partial question'));
 await visible('Maple is $300 under budget.');
 assert.match(await page.locator('.chat-message.assistant').last().innerText(),/groq.*→.*openai/is);
 await reset();
 await page.evaluate(()=>submitText('exhausted question'));
 events=await(await page.request.get(origin+'/qa/events')).json();
 assert.deepEqual(events.filter(e=>e.event==='start').map(e=>e.model),['groq-gpt-oss-120b','openai-gpt-4o','qa-local:1b']);
 // A newer question must own the result even while the shared inventory request stalls.
 await page.unroute('**/models/catalog');
 let releaseCatalog;
 const delayedCatalog=new Promise(resolve=>{releaseCatalog=resolve});
 await page.route('**/models/catalog',async route=>{await delayedCatalog;await route.fulfill({json:catalog})});
 await page.evaluate(()=>{runtimeCatalogCache=null});
 await reset();
 const requested=page.waitForRequest('**/models/catalog');
 await page.evaluate(()=>{void submitText('slow question')});
 await requested;
 await page.evaluate(()=>{void autoSendToAI('new spoken question')});
 releaseCatalog();
 await visible('New answer complete');
 events=await(await page.request.get(origin+'/qa/events')).json();
 assert.equal(events.filter(e=>e.event==='start').length,1);
 assert.ok(!events.some(e=>e.question==='slow question'));
 await page.unroute('**/models/catalog');
 let releaseUnavailable;
 const unavailable=new Promise(resolve=>{releaseUnavailable=resolve});
 await page.route('**/models/catalog',async route=>{
   await unavailable;
   await route.fulfill({status:503,json:{detail:'Unavailable'}}).catch(()=>{});
 });
 await page.evaluate(()=>{runtimeCatalogCache=null});
 await reset();
 const discoveryStart=Date.now();
 try {
   await page.evaluate(()=>submitText('next question after discovery timeout'));
   await visible('New answer complete');
   assert.ok(Date.now()-discoveryStart<9000,'Catalog timeout must release recovery promptly');
   assert.equal(await page.evaluate(()=>isProcessing),false);
 } finally {releaseUnavailable()}
 assert.deepEqual(errors,[]);
 console.log('PASS: real UI + production recovery endpoint; partial preservation, attribution, resume/JD, recorded-audio submission, cooldown, newer spoken-question cancellation, local fallback, bounded exhaustion, runtime inventory, embedding exclusion, unavailable-catalog fallback and cancellation during delayed discovery.');
} finally {await browser.close()}
