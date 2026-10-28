// Production HTML/script smoke check with synthetic API responses; no user backend calls.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, resolve, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const dist = resolve(dirname(fileURLToPath(import.meta.url)), '../../../apps/web/dist');
const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
const server = createServer(async (req, res) => {
  const path = resolve(dist, '.' + new URL(req.url, 'http://localhost').pathname);
  if (!path.startsWith(dist + '/')) { res.writeHead(404).end(); return; }
  try { res.setHeader('Content-Type', types[extname(path)] || 'application/octet-stream'); res.end(await readFile(path)); }
  catch { res.writeHead(404).end(); }
});
await new Promise((done, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', done); });
const {default:assert}=await import('node:assert/strict');
const {mkdir,writeFile}=await import('node:fs/promises');
const out=resolve('qa/performance/results/2026-10-04-two-tasks');await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:false});
try {
 const origin=`http://127.0.0.1:${server.address().port}`;
 const context=await browser.newContext({viewport:{width:960,height:720},serviceWorkers:'block'});
 await context.addInitScript(()=>localStorage.setItem('hasOnboarded','true'));
 await context.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.origin===origin)return route.continue();
  if(url.pathname==='/auth/status')return route.fulfill({json:{auth_required:false}});
  if(url.pathname==='/stream-recover')return route.fulfill({response:await route.fetch({url:'http://127.0.0.1:8041/stream-recover',timeout:65000})});
  return route.fulfill({status:503,json:{detail:'Isolated test'}});
 });
 const terminal=await context.newPage();await terminal.setContent('<body style="background:#151515;color:white;font:28px monospace;padding:30px"><pre>ssh dev@qa-host\n$ cat example.py\n\ndef add(a, b):\n    # Return the sum of a and b\n    pass</pre></body>');
 const screen=(await terminal.screenshot()).toString('base64');
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let socket;await page.routeWebSocket('**/ws/transcribe?**',ws=>{socket=ws});
 await page.goto(origin+'/index.html');await page.waitForLoadState('networkidle');
 await page.evaluate(screen=>{
  window.qaCaptures=0;window.qaResize=[];
  window.api={captureScreenshot:async()=>{qaCaptures++;return screen},setConversationCollapsed:async(...args)=>qaResize.push(args)};
  runOcr=async()=>({text:''});
  getRuntimeModelCatalog=async()=>[{id:'qwen3.5:9b',provider:'ollama',configured:true,text:true,vision:true,size:1e9}];
  modelSelect.add(new Option('Local test vision','qwen3.5:9b'));modelSelect.value='qwen3.5:9b';
  setListeningUI(true);systemAudioWs=openSystemAudioSocket();
 },screen);
 assert.equal(await page.locator('#conversationPanel').isVisible(),false);
 while(!socket)await new Promise(r=>setTimeout(r,20));
 socket.send(JSON.stringify({type:'question',session_id:'qa-ssh',answer_id:1,question:'Complete this function. Show the Python code.'}));
 await page.waitForFunction(()=>document.querySelector('.chat-message.assistant'),null,{timeout:30000});
 assert.equal(await page.locator('#conversationPanel').isVisible(),true);
 await page.locator('#conversationToggle').click();
 socket.send(JSON.stringify({type:'question',session_id:'qa-ssh',answer_id:2,question:'Why does that implementation work? Answer briefly.'}));
 await page.waitForFunction(()=>currentMessages.filter(m=>m.role==='assistant').length===2&&!isProcessing,null,{timeout:90000});
 assert.equal(await page.locator('#conversationPanel').isVisible(),false);
 await page.locator('#conversationToggle').click();
 const result=await page.evaluate(()=>({captures:qaCaptures,listening:isListening,resize:qaResize,messages:currentMessages.map(m=>({role:m.role,text:m.text})),status:[...document.querySelectorAll('.recovery-status')].map(e=>e.textContent)}));
 assert.equal(result.captures,2);assert.equal(result.listening,true);assert.equal(result.messages.filter(m=>m.role==='user').length,2);
 assert.match(result.messages.find(m=>m.role==='assistant').text,/return\s+a\s*\+\s*b/);
 assert.ok(!result.status.some(s=>/Stopped|incomplete|No answer/i.test(s)));
 await page.screenshot({path:out+'/expanded.png'});
 await page.locator('#conversationToggle').click();await page.screenshot({path:out+'/collapsed.png'});
 await page.locator('#textInput').fill('Typed test: What is 2 plus 3? Answer briefly.');
 await page.locator('#textInput').press('Enter');
 await page.waitForFunction(()=>currentMessages.filter(m=>m.role==='assistant').length===3&&!isProcessing,null,{timeout:90000});
 assert.equal(await page.evaluate(()=>isListening),true);
 assert.equal(await page.locator('#conversationPanel').isVisible(),false);
 assert.match(await page.evaluate(()=>currentMessages.filter(m=>m.role==='assistant').at(-1).text),/5|five/i);

 result.typedQuestionVerified=true;result.automaticRevealVerified=true;
 await writeFile(out+'/live.json',JSON.stringify({result,errors},null,2));assert.deepEqual(errors,[]);
 console.log(JSON.stringify({passed:true,captures:result.captures,answers:3,typedWhileListening:true,keptListening:result.listening,hiddenWhileAnswering:true,status:result.status}));
}finally{await browser.close();server.close()}
