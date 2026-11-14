// Actual Electron renderer + preload + production streaming backend, isolated data.
// Synthetic questions/resume only. --screen captures then crops a marked test window;
// pixels outside its verified border are never sent to OCR or the model.
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const {spawn} = require('node:child_process');
const {_electron: electron, chromium} = require('@playwright/test');
const assert = require('node:assert/strict');

async function main() {
 const root = path.resolve(__dirname, '../../..');
 const output = await fs.mkdtemp(path.join(os.tmpdir(), 'ant-desktop-answer-'));
 const port = 19000 + process.pid % 1000;
 const origin = `http://127.0.0.1:${port}`;
 const backend = spawn(path.join(root,'AINT_Venv/bin/python'), [path.join(root,'qa/performance/ai/desktop-answer-server.py'),String(port)], {
  cwd:root, env:{...process.env,ANT_DATA_DIR:path.join(output,'backend'),PYTHONDONTWRITEBYTECODE:'1'},stdio:['ignore','pipe','pipe']
 });
 let backendErrors='';backend.stderr.on('data',b=>{backendErrors=(backendErrors+b.toString()).slice(-2000)});
 let app,backdrop;
 try {
  for(let attempt=0;;attempt++) {
   if(backend.exitCode!==null)throw Error('Isolated backend exited: '+backendErrors);
   if(await fetch(origin+'/health').then(r=>r.ok).catch(()=>false))break;
   if(attempt>=60)throw Error('Isolated backend did not become ready: '+backendErrors);
   await new Promise(r=>setTimeout(r,500));
  }
  let screenFixture=null;
  if(process.argv.includes('--screen')) {
   backdrop=await chromium.launch({channel:'chrome',headless:false,args:['--window-position=40,60','--window-size=900,700']});
   const screenPage=await backdrop.newPage({viewport:null});
   await screenPage.setContent('<body style="margin:0;background:#f000f0;padding:24px;box-sizing:border-box;height:100vh"><main style="background:white;height:100%;padding:40px;box-sizing:border-box;font:24px system-ui"><h1>Synthetic interview task</h1><p>Write a Python function that returns the sum of even numbers in a list.</p><p>Input: [1, 2, 3, 4]. Expected result: 6.</p><p>No candidate history is shown here.</p></main></body>');
   await screenPage.bringToFront();
   screenFixture=await screenPage.evaluate(()=>{
    const border=(outerWidth-innerWidth)/2;
    return {x:screenX+border,y:screenY+outerHeight-innerHeight-border,width:innerWidth,height:innerHeight};
   });
  }
  const mainFile=path.join(output,'main.cjs');
  await fs.writeFile(mainFile, `
   const {app,BrowserWindow,ipcMain,session,screen,nativeImage}=require('electron');
   app.setPath('userData',${JSON.stringify(path.join(output,'profile'))});
   const values={model:'groq-qwen3-8-27b',mode:'code',responseStyle:'spoken',temperature:'1.0',contextLength:'10',
    attachedResumeContext:{name:'Synthetic QA resume',text:'Alex Rivera. Built Python APIs and collaborated with a software team.'},
    hasOnboarded:true};
   ipcMain.on('auth:session:get',event=>{event.returnValue={value:null}});
   const handlers={
    'store:get':(_,key)=>values[key], 'store:set':(_,key,value)=>{values[key]=value},
    'apiKey:has':()=>({hasKey:true}), 'auto-screenshot:get-status':()=>({enabled:${!!screenFixture}}),
    'window:get-stealth-state':()=>({enabled:true,undetectable:true,supported:true,partial:false,platform:process.platform,externallyVerified:false}),
    'subscriptions:status':()=>({accounts:[],connected:false,models:[],welcomeSeen:true}),
    'backend:status':()=>({status:'ready'}),
    'conversation:list':()=>[], 'window:is-maximized':()=>false
   };
   if(${!!screenFixture}) {
    const bounds=${JSON.stringify(screenFixture)};
    const capture=require(${JSON.stringify(path.join(root,'electron/lib/native-screen-capture.js'))}).captureNativeScreen;
    handlers['window:capture-screenshot-context']=async()=>{
     const display=screen.getDisplayMatching(bounds);
     const started=Date.now();
     const raw=await capture(display.id,process.pid);
     const image=nativeImage.createFromBuffer(Buffer.from(raw,'base64'));
     const scale=image.getSize().width/display.bounds.width;
     const cropped=image.crop({x:Math.round((bounds.x-display.bounds.x)*scale),y:Math.round((bounds.y-display.bounds.y)*scale),width:Math.round(bounds.width*scale),height:Math.round(bounds.height*scale)});
     const size=cropped.getSize(),pixels=cropped.toBitmap();
     // Verify a synthetic border on all four sides before any external transfer.
     for(const [x,y] of [[12,100],[size.width-12,100],[100,12],[100,size.height-12]]) {
      const i=(Math.round(y)*size.width+Math.round(x))*4;
      if(!(pixels[i]>160&&pixels[i+1]<100&&pixels[i+2]>160))throw Error('Test screen border is obscured; capture will not be transmitted');
     }
     globalThis.lastCaptureMs=Date.now()-started;
     return {image:cropped.toPNG().toString('base64'),capturedAt:Date.now(),displayId:String(display.id)};
    };
   }
   const preload=${JSON.stringify(path.join(root,'electron/preload.js'))};
   const source=require('fs').readFileSync(preload,'utf8');
   for(const m of source.matchAll(/ipcRenderer\\.invoke\\(["']([^"']+)["']/g)) {
    if(!Object.hasOwn(handlers,m[1]))handlers[m[1]]=()=>null;
   }
   for(const [name,handler] of Object.entries(handlers))ipcMain.handle(name,handler);
   app.whenReady().then(async()=>{
    session.defaultSession.webRequest.onBeforeRequest((details,callback)=>{
     if(details.url.startsWith('http://127.0.0.1:8000/'))return callback({redirectURL:details.url.replace('http://127.0.0.1:8000',${JSON.stringify(origin)})});
     callback({cancel:/^https?:/.test(details.url)&&!details.url.startsWith(${JSON.stringify(origin)})});
    });
    const win=new BrowserWindow({width:1280,height:900,show:false,webPreferences:{preload,contextIsolation:true,nodeIntegration:false}});
    win.setContentProtection(true);
    await win.loadFile(${JSON.stringify(path.join(root,'electron/renderer/index.html'))});win.show();
   });
  `);
  app=await electron.launch({args:[mainFile]});
  const page=await app.firstWindow();
  const pageErrors=[];page.on('pageerror',error=>pageErrors.push(error.message));
  await page.waitForFunction(()=>typeof submitText==='function' && isBackendReady && modelSelect.value==='groq-qwen3-8-27b');
  await page.evaluate(async()=>{await resumeContextReady;await jobDescriptionReady;suppressAutoSave=true});
  const results=[];
  const questions=screenFixture
   ? ['Solve the task on screen. Return code only.','What result should the function return for the input on screen?']
   : ['What is a Kubernetes cluster?','Write a Python function to sum even numbers in a list. Return code only.','Explain the difference between a process and a thread in two sentences.'];
  for(const question of questions) {
   await page.locator('#textInput').click();
   await page.locator('#textInput').fill(question);
   await page.evaluate(()=>{
    window.__latency={start:null,requestMs:null,ocrStartMs:null,ocrCompleteMs:null,firstVisibleMs:null,completeMs:null};
    const previousAnswers=new Set(document.querySelectorAll('.chat-message.assistant'));
    const input=document.getElementById('textInput');
    input.addEventListener('keydown',()=>{window.__latency.start=performance.now()},{capture:true,once:true});
    if(!window.__latencyFetch){
     window.__latencyFetch=window.fetch;
     window.fetch=async function(url,options){
      const state=window.__latency;
      if(String(url).includes('/stream-recover')&&state.start!==null)state.requestMs=performance.now()-state.start;
      const ocr=String(url).endsWith('/ocr')&&state.start!==null;
      if(ocr)state.ocrStartMs=performance.now()-state.start;
      const response=await window.__latencyFetch.call(this,url,options);
      if(ocr)state.ocrCompleteMs=performance.now()-state.start;
      return response;
     };
    }
    window.__latencyObserver?.disconnect();
    let framePending=false;
    const checkVisible=()=>{
     framePending=false;
     const state=window.__latency;if(state.start===null)return;
     const bubble=document.querySelector('.chat-message.assistant:last-child .msg-bubble');
     if(bubble&&!previousAnswers.has(bubble.closest('.chat-message'))&&!bubble.closest('.loading')&&bubble.textContent.trim()&&state.firstVisibleMs===null){
      const chat=document.getElementById('chatArea').getBoundingClientRect();
      const walker=document.createTreeWalker(bubble,NodeFilter.SHOW_TEXT);
      for(let node;node=walker.nextNode();) {
       if(!node.textContent.trim()||node.parentElement.closest('button,.typing-cursor,.loading-indicator'))continue;
       const range=document.createRange();range.selectNodeContents(node);
       for(const rect of range.getClientRects()) {
        const left=Math.max(rect.left,chat.left,0),right=Math.min(rect.right,chat.right,innerWidth);
        const top=Math.max(rect.top,chat.top,0),bottom=Math.min(rect.bottom,chat.bottom,innerHeight);
        if(right>left&&bottom>top&&bubble.contains(document.elementFromPoint((left+right)/2,(top+bottom)/2))) {
         state.firstVisibleMs=performance.now()-state.start;return;
        }
       }
      }
     }
     if(state.firstVisibleMs===null&&performance.now()-state.start<65000){framePending=true;requestAnimationFrame(checkVisible)}
    };
    window.__latencyObserver=new MutationObserver(()=>{
     if(!framePending){framePending=true;requestAnimationFrame(checkVisible)}
    });
    window.__latencyObserver.observe(document.getElementById('chatArea'),{childList:true,subtree:true,characterData:true,attributes:true});
   });
   await page.locator('#textInput').press('Enter');
   await page.waitForFunction(()=>window.__latency.firstVisibleMs!==null&&!isProcessing&&activeQuestion===null,{},{timeout:70000});
   const row=await page.evaluate(()=>({
    ...window.__latency,completeMs:performance.now()-window.__latency.start,
    answer:document.querySelector('.chat-message.assistant:last-child .msg-bubble')?.textContent,
    status:document.querySelector('.chat-message.assistant:last-child .recovery-status')?.textContent,
    errors:[...document.querySelectorAll('.chat-message.error')].map(el=>el.textContent),
    model:modelSelect.value,mode:modeSelect.value
   }));
   delete row.start;row.question=question;
   if(screenFixture)row.nativeCaptureMs=await app.evaluate(()=>globalThis.lastCaptureMs);
   assert(row.answer?.trim()&&!/incomplete|failed|unavailable|deadline/i.test(row.status||''),JSON.stringify(row));
   assert(Number.isFinite(row.firstVisibleMs),'No first visible answer was measured');
   results.push(row);console.log(JSON.stringify(row));
   await page.screenshot({path:path.join(output,`answer-${results.length}.png`)});
  }
  await fs.writeFile(path.join(output,'results.json'),JSON.stringify({scope:'Enter to visible answer in actual Electron, real provider and resume verification; isolated IPC settings/auth.',screenCapture:!!screenFixture,results,pageErrors},null,2));
  console.log('Artifacts: '+output);
  assert.deepEqual(pageErrors,[],'Unexpected renderer errors in the isolated desktop');
 } finally {if(app)await app.close();if(backdrop)await backdrop.close();backend.kill('SIGTERM')}
}
main().catch(error=>{console.error(error);process.exitCode=1});
