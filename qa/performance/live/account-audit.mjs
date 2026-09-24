import { chromium } from '@playwright/test';
import { writeFile, access, readFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
const out='/tmp/ant-account-audit';
for (const target of await (await fetch('http://127.0.0.1:9223/json/list')).json()) {
  if(target.type==='page' && !target.url) await fetch(`http://127.0.0.1:9223/json/close/${target.id}`);
}
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
const page=browser.contexts()[0].pages().find(p=>/signin.html|index.html/.test(p.url())) || browser.contexts()[0].pages()[0];
const mode=process.argv[2] || 'inspect';
if (/index.html/.test(page.url())) await page.waitForFunction(()=>typeof isProcessing==='boolean',{},{timeout:30000});
try {
  if(mode==='cloud-check') {
    const results=[];
    for(const model of ['glm-5.3-flash:cloud','nemotron-3-ultra:cloud','minimax-m3:cloud']) {
      const result=await page.evaluate(async model=>{
        const start=performance.now();let first=null,answer='',served=null,error=null;
        const query='Use only this resume for personal facts: Jordan built Python APIs at Acme. The resume does not list certifications. Which AWS certifications do you hold and when did you earn them? If the resume does not specify this, state that briefly. Do not infer absence.';
        try {
          const params=new URLSearchParams({q:query,provider:model,mode:'interview',style:'concise',temperature:'0.2'});
          const response=await fetch(API_BASE+'/stream?'+params,{signal:AbortSignal.timeout(45000)});
          if(!response.ok)return {model,status:response.status,error:'HTTP error'};
          const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
          while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines){if(!line.startsWith('data:'))continue;let d;try{d=JSON.parse(line.slice(5));}catch{continue;}if(d.type==='meta'&&d.model)served=d.model;if(d.type==='chunk'&&d.content){if(first===null)first=(performance.now()-start)/1000;answer+=d.content;}if(d.type==='error'){const message=String(d.message||'');error=/not configured|requires.*key|missing.*key/i.test(message)?'API key is not configured':/401|403|unauthorized|invalid.*key/i.test(message)?'Authentication rejected':/404|not found|unknown model/i.test(message)?'Model unavailable':/402|429|quota|limit/i.test(message)?'Quota or rate limit':'Provider rejected or could not complete the request';}}}
        }catch(e){error=e.name==='TimeoutError'?'Timed out':'Request failed';}
        return {model,served,firstSeconds:first,totalSeconds:(performance.now()-start)/1000,answer,error};
      },model);
      results.push(result);await writeFile(out+'/cloud-check.json',JSON.stringify(results,null,2));console.log(JSON.stringify(result));
    }
  }
  if(mode==='ocr-check') {
    const bytes=await readFile('/tmp/ant-ocr-fixture.png');
    const start=Date.now();
    const result=await page.evaluate(async image=>{const r=await fetch(API_BASE+'/ocr',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_b64:image})});return {status:r.status,...await r.json()};},bytes.toString('base64'));
    result.seconds=(Date.now()-start)/1000;
    result.passed=result.status===200 && result.method==='apple-vision' && result.text==='Maya will review the budget.\nSend the project summary by Friday.';
    await page.locator('#captureBtn').click();
    await page.waitForFunction(()=>!captureBtn.classList.contains('processing'),{},{timeout:65000});
    result.screenshot={visible:await page.locator('#ocrBadge').isVisible(),text:await page.locator('#ocrBadge').innerText()};
    await page.evaluate(()=>clearPendingOcr());
    await writeFile(out+'/native-ocr.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  }
  if(mode==='study-persistence') {
    const base=page.url().replace(/[^/]+$/,'');
    await page.goto(base+'study-plan.html');await page.waitForTimeout(800);
    const before=await page.locator('#completedTasks').innerText();
    await page.locator('.task-checkbox').first().click();await page.waitForTimeout(500);
    const changed=await page.locator('#completedTasks').innerText();
    await page.reload();await page.waitForTimeout(800);
    const after=await page.locator('#completedTasks').innerText();
    const result={before,changed,after,passed:changed!==before && changed===after};
    await writeFile(out+'/study-persistence.json',JSON.stringify(result));console.log(JSON.stringify(result));
    await page.goto(base+'index.html');
  }
  if(mode==='auto-trace') {
    await page.evaluate(()=>{const original=window.fetch;window.fetch=async(...args)=>{const r=await original(...args);if(String(args[0]).includes('/stream-race'))window.auditFrames=r.clone().text();return r;};});
    await page.locator('#modelSelect').selectOption('auto');
    await page.locator('#textInput').fill('Explain Docker in two clear sentences.');
    await page.locator('#textInput').press('Enter');
    await page.waitForTimeout(1500);
    await page.waitForFunction(()=>!isProcessing,{},{timeout:65000});
    await page.waitForTimeout(500);
    await writeFile(out+'/race-frames.txt',await page.evaluate(()=>window.auditFrames));
    console.log(await page.locator('#chatArea').innerText());
  }
  if(mode==='race-debug') {
    const frames=await page.evaluate(async()=>{
      const response=await fetch(API_BASE+'/stream-race?q=Explain%20Docker%20in%20two%20sentences&enabled=groq,ollama&mode=race');
      return {status:response.status,text:await response.text()};
    });
    console.log(JSON.stringify(frames));
  }
  if(mode==='finish') {
    await page.evaluate(()=>{window.AuthHelper?.clearToken();});
    await page.evaluate(()=>window.api.closeWindow()).catch(()=>{});
    console.log('Test session signed out and audit desktop closed.');
    process.exit(0);
  }
  if(mode==='extras') {
    const results=[];const network=[];const dialogs=[];const base=page.url().replace(/[^/]+$/,'');
    page.on('response',r=>{if(r.status()>=400)network.push({path:new URL(r.url()).pathname,status:r.status()});});
    page.on('dialog',async d=>{dialogs.push(d.message());await d.dismiss();});
    await page.goto(base+'index.html');await page.waitForTimeout(1200);
    await page.locator('#menuBtn').click();await page.locator('[data-action="history"]').click();await page.waitForTimeout(500);
    const count=await page.locator('.history-item').count();
    if(count)await page.locator('.history-item-content').first().click();
    await page.waitForTimeout(700);
    results.push({name:'history-restore',count,restored:await page.locator('#chatArea').innerText()});
    if(count) {
      await page.locator('#menuBtn').click();await page.locator('[data-action="export"]').click();
      const download=page.waitForEvent('download',{timeout:10000}).then(async d=>{await d.saveAs(`${out}/conversation-export.md`);return {downloaded:true};}).catch(()=>({downloaded:false}));
      await page.locator('#confirmExportBtn').click();results.push({name:'export',...await download,dialogs:[...dialogs],network:[...network]});
    }
    await page.goto(base+'study-plan.html');await page.waitForTimeout(1500);
    const tasks=page.locator('.task-checkbox');
    const taskCount=await tasks.count();
    if(taskCount) {
      await tasks.first().click();await page.waitForTimeout(1000);
      const before=await page.locator('#completedTasks').innerText();
      await page.reload();await page.waitForTimeout(1500);
      results.push({name:'study-task-persistence',taskCount,before,after:await page.locator('#completedTasks').innerText()});
    } else results.push({name:'study-task-persistence',taskCount});
    await page.goto(base+'index.html');await page.waitForTimeout(1000);
    await page.locator('#gearBtn').click();
    const tabs=[];
    for(const name of ['General','Providers','Models','Voice','Clone','Data','Integrations']) {
      try {await page.getByRole('button',{name,exact:true}).click();await page.waitForTimeout(200);tabs.push({name,opened:true});}
      catch(e){tabs.push({name,opened:false,error:e.message.slice(0,150)});}
    }
    results.push({name:'settings-tabs',tabs});
    await page.locator('#closeSettingsBtn').click();
    await writeFile(`${out}/extras.json`,JSON.stringify({results,network,dialogs},null,2));console.log(JSON.stringify(results));
  }
  if(mode==='verify') {
    const results=[];const base=page.url().replace(/[^/]+$/,'');
    const network=[];page.on('response',r=>{if(r.status()>=400)network.push({path:new URL(r.url()).pathname,status:r.status()});});
    page.on('dialog',async d=>{results.push({name:'dialog',message:d.message()});await d.dismiss();});
    await page.goto(base+'index.html');await page.waitForTimeout(1200);
    await page.locator('#modelSelect').selectOption('auto');
    await page.locator('#textInput').fill('Explain the difference between a container and a virtual machine in two clear sentences.');
    await page.locator('#textInput').press('Enter');
    await page.waitForFunction(()=>!isProcessing,{},{timeout:70000});
    results.push({name:'auto-repeat',bubble:await page.locator('.chat-message.assistant .msg-bubble').last().innerText(),chat:(await page.locator('#chatArea').innerText()).slice(-2000)});
    await page.locator('#captureBtn').click();
    try{await page.waitForFunction(()=>!captureBtn.classList.contains('processing'),{},{timeout:65000});}catch{}
    results.push({name:'screenshot-after-wait',state:await page.evaluate(()=>({processing:captureBtn.classList.contains('processing'),attached:!!pendingOcrScreenshot,badge:ocrBadgeText?.textContent,visible:ocrBadge?.style.display}))});
    await page.evaluate(()=>clearPendingOcr());
    for(const name of ['resume-review','resume-review-v2']) {
      await page.goto(base+name+'.html');await page.waitForTimeout(1000);
      await page.locator('#resumeInput').fill('Jordan Patel. Software Engineer at Acme, 2021 to 2025. Python, PostgreSQL, Redis, Kubernetes. Built inventory APIs and caching that reduced p95 latency from 900 ms to 120 ms. Worked with Maya on rollout tests. Bachelor of Computer Science, 2020.');
      await page.locator('#jobInput').fill('Python backend engineer with PostgreSQL and Kubernetes experience.');
      await page.locator('#analyzeBtn').click();await page.waitForTimeout(8000);
      results.push({name,body:(await page.locator('body').innerText()).slice(0,6000),network:network.splice(0)});
      await page.screenshot({path:`${out}/verify-${name}.png`});
    }
    await page.goto(base+'cognitive-graph.html');await page.waitForTimeout(12000);
    results.push({name:'graph-after-wait',body:(await page.locator('body').innerText()).slice(0,2500),network:network.splice(0)});
    await writeFile(`${out}/verify.json`,JSON.stringify(results,null,2));
    console.log(JSON.stringify(results));
    await page.goto(base+'index.html');
  }
  if(mode==='desktop') {
    await access('/tmp/ant-product-benchmark/speech-0.aiff');
    const results=[];
    const base=page.url().replace(/[^/]+$/,'');
    await page.goto(base+'index.html');await page.waitForTimeout(1500);
    await page.locator('#modelSelect').selectOption('qwen3.5:9b');
    await page.locator('#modeSelect').selectOption('instant');
    for(let cycle=1;cycle<=2;cycle++) {
      const row={name:`microphone-cycle-${cycle}`};results.push(row);
      try {
        await page.locator('#textInput').fill('');
        const start=Date.now();
        await page.locator('#textInput').press('Enter');
        await page.waitForFunction(()=>!isStarting,{},{timeout:15000});
        row.started=await page.evaluate(()=>({listening:isListening,recorder:mediaRecorder?.state,tracks:mediaStream?.getAudioTracks().map(t=>({state:t.readyState,enabled:t.enabled}))}));
        if(row.started.recorder==='recording') {
          const player=spawn('/usr/bin/afplay',['/tmp/ant-product-benchmark/speech-0.aiff']);
          await new Promise(resolve=>{player.once('close',resolve);player.once('error',resolve);setTimeout(()=>{player.kill();resolve();},10000);});
          row.preview=await page.locator('#transcriptStripContent').innerText();
          const stoppedAt=Date.now();
          await page.locator('#textInput').press('Enter');
          row.stopState=await page.evaluate(()=>({listening:isListening,recorder:mediaRecorder?.state}));
          await page.waitForFunction(()=>!isProcessing,{},{timeout:65000});
          row.postStopSeconds=(Date.now()-stoppedAt)/1000;
        }
        row.totalSeconds=(Date.now()-start)/1000;
        row.chat=(await page.locator('#chatArea').innerText()).slice(-3500);
      }catch(e){row.error=e.message.slice(0,400);await page.evaluate(()=>{if(isListening)stopListening();});}
      await writeFile(`${out}/desktop.json`,JSON.stringify(results,null,2));console.log(JSON.stringify(row));
    }
    for(const name of ['protection-on','protection-off']) {
      await page.locator('#stealthBtn').click();await page.waitForTimeout(500);
      results.push({name,label:await page.locator('#stealthBtn').innerText(),nativeState:await page.evaluate(()=>window.api.getStealthState())});
    }
    await page.locator('#captureBtn').click();
    await page.waitForFunction(()=>!captureBtn.classList.contains('processing'),{},{timeout:65000});
    results.push({name:'screenshot-attachment',badge:await page.locator('#ocrBadge').innerText(),visible:await page.locator('#ocrBadge').isVisible()});
    if(await page.locator('#ocrBadge').isVisible())await page.locator('#ocrBadgeRemove').click();
    const overlays=[];
    for(const kind of ['showCaptionOverlay','showInterviewOverlay']){
      try{const result=await page.evaluate(kind=>window.api[kind](),kind);await page.waitForTimeout(1000);overlays.push({kind,result,pages:browser.contexts()[0].pages().map(p=>p.url().split('/').pop())});}catch(e){overlays.push({kind,error:e.message.slice(0,200)});}
    }
    results.push({name:'overlays',overlays});
    await page.evaluate(async()=>{await window.api.hideCaptionOverlay();await window.api.hideInterviewOverlay();});
    await page.screenshot({path:`${out}/desktop-final.png`});
    await writeFile(`${out}/desktop.json`,JSON.stringify(results,null,2));console.log(JSON.stringify({finished:'desktop',results}));
  }
  if(mode==='pages') {
    const results=[];let current=null;
    page.on('pageerror',e=>current?.errors.push(e.message));
    page.on('response',r=>{if(r.status()>=400)current?.network.push({path:new URL(r.url()).pathname,status:r.status()});});
    page.on('dialog',async d=>{current?.dialogs.push(d.message());await d.dismiss();});
    const base=page.url().replace(/[^/]+$/,'');
    for(const name of (process.argv[3]?.split(',') || ['job-tracker','study-plan','interview-simulator','pre-interview','resume-review','resume-review-v2','cognitive-graph','analytics-dashboard'])) {
      current={name,errors:[],network:[],dialogs:[]};results.push(current);
      try {
        await page.goto(base+name+'.html');await page.waitForTimeout(1800);
        current.initial=(await page.locator('body').innerText()).slice(0,3000);
        if(name==='job-tracker') {
          await page.locator('.btn-add').click();
          await page.locator('#companyInput').fill('ANT audit sample company');
          await page.locator('#roleInput').fill('QA sample engineer');
          await page.locator('#addJobForm button[type=submit]').click();
          await page.waitForTimeout(2500);
          current.afterCreate=(await page.locator('body').innerText()).slice(0,3500);
          await page.reload();await page.waitForTimeout(1500);
          current.afterReload=(await page.locator('body').innerText()).slice(0,3500);
        }
        if(name==='study-plan') {
          await page.locator('#roleInput').fill('Python backend engineer');
          await page.locator('#skillsInput').fill('Python, PostgreSQL');
          await page.locator('#generateBtn').click();
          await page.waitForFunction(()=>document.getElementById('loadingState')?.style.display==='none',{},{timeout:45000});
        }
        if(name==='interview-simulator') {
          await page.locator('#roleInput').fill('Python backend engineer');
          await page.locator('#startBtn').click();
          await page.waitForTimeout(2500);
          if(await page.locator('#answerInput').isVisible()) {
            await page.locator('#answerInput').fill('I built a Python inventory API using PostgreSQL. I added Redis caching and measured latency falling from 900 ms to 120 ms.');
            await page.locator('#submitBtn').click();await page.waitForTimeout(3000);
          }
        }
        if(name==='pre-interview') {
          await page.locator('#companyInput').fill('Acme');
          await page.locator('#roleInput').fill('Python backend engineer');
          await page.locator('#generateBtn').click();
          await page.waitForTimeout(5000);
        }
        if(name==='resume-review-v2') {
          await page.locator('#resumeInput').fill('Jordan Patel. Software Engineer at Acme 2021 to 2025. Python, PostgreSQL, Redis, Kubernetes. Built an inventory API and added caching that reduced p95 latency from 900 ms to 120 ms. Collaborated with Maya on rollout testing. Bachelor of Computer Science, 2020.');
          await page.locator('#jobInput').fill('Backend engineer working with Python, SQL, APIs, testing, and Kubernetes.');
          await page.locator('#analyzeBtn').click();await page.waitForTimeout(5000);
        }
        current.final=(await page.locator('body').innerText()).slice(0,7000);
      } catch(e) {current.actionError=e.message.slice(0,500);}
      await page.screenshot({path:`${out}/page-${name}.png`}).catch(()=>{});
      await writeFile(`${out}/pages.json`,JSON.stringify(results,null,2));
      await writeFile(`${out}/result-${name}.json`,JSON.stringify(current,null,2));
      console.log(JSON.stringify({name,errors:current.errors,network:current.network,dialogs:current.dialogs,actionError:current.actionError,summary:current.final?.slice(0,500)}));
    }
    await page.goto(base+'index.html');
  }
  if(mode==='core') {
    await page.evaluate(()=>startNewConversation());
    const results=[];
    const network=[];
    page.on('response', response=> {if(response.status()>=400) {const u=new URL(response.url());network.push({path:u.pathname,status:response.status()});}});
    async function question(name, text) {
      const before=await page.locator('.chat-message.assistant').count();
      const start=Date.now();let first=null;
      await page.locator('#textInput').fill(text);
      await page.locator('#textInput').press('Enter');
      let answer='';
      while(Date.now()-start<75000) {
        const state=await page.evaluate(()=>({busy:isProcessing,answer:[...document.querySelectorAll('.chat-message.assistant')].at(-1)?.querySelector('.msg-bubble')?.innerText || '',loading:[...document.querySelectorAll('.chat-message.assistant')].at(-1)?.classList.contains('loading'),errors:[...document.querySelectorAll('.chat-message.error')].slice(-1).map(el=>el.innerText),count:document.querySelectorAll('.chat-message.assistant').length}));
        if(state.count>before && !state.loading && state.answer.trim().length>0 && first===null) first=(Date.now()-start)/1000;
        answer=state.answer;
        if(!state.busy && state.count>before && !state.loading && state.answer.trim() && Date.now()-start>1000) {results.push({name,seconds:(Date.now()-start)/1000,firstVisibleSeconds:first,answer,errors:state.errors});break;}
        await new Promise(resolve=>setTimeout(resolve,200));
      }
      if(Date.now()-start>=75000)results.push({name,timeout:true,answer});
      await page.screenshot({path:`${out}/${name}.png`});
      await writeFile(`${out}/core.json`,JSON.stringify({results,network},null,2));
      console.log(JSON.stringify(results.at(-1)));
    }
    await page.locator('#modelSelect').selectOption('auto');
    await page.locator('#modeSelect').selectOption('adaptive');
    await page.locator('#moreAiBtn').click();
    await page.locator('#responseStyleSelect').selectOption('concise');
    await page.locator('#moreAiBtn').click();
    await question('default-answer','In two sentences, explain what Docker is.');
    await page.locator('#modelSelect').selectOption('qwen3.5:9b');
    await page.locator('#modeSelect').selectOption('interview');
    const resume='Jordan Patel. Software Engineer at Acme, 2021 to 2025. Built a Python inventory API using PostgreSQL. Deployed on Kubernetes with Helm. Added Redis caching, reducing p95 latency from 900 ms to 120 ms. Worked with Maya on rollout tests. No AWS certification is listed.';
    await page.locator('#resumeContextFile').setInputFiles({name:'audit-resume.md',mimeType:'text/markdown',buffer:Buffer.from(resume)});
    await page.waitForFunction(()=>!resumeUploadButton.disabled,{},{timeout:20000});
    results.push({name:'resume-upload',state:await page.locator('#resumeContextStatus').innerText()});
    await question('resume-answer','Tell me about your most relevant project and its measured result.');
    await question('unsupported-experience','Which AWS certifications do you hold, and when did you earn them?');
    await page.reload();await page.waitForLoadState('domcontentloaded');
    await page.waitForFunction(()=>typeof resumeContextReady!=='undefined');
    results.push({name:'resume-reload',state:await page.evaluate(async()=>{await resumeContextReady;return {attached:!!resumeAnswerContext,name:resumeAnswerContext?.name,visible:!resumeStatus.hidden};})});
    await page.locator('#modelSelect').selectOption('qwen3.5:9b');
    await page.locator('#modeSelect').selectOption('code');
    await page.locator('#moreAiBtn').click();
    await page.locator('#responseStyleSelect').selectOption('detailed');
    await page.locator('#moreAiBtn').click();
    await question('long-detailed-answer','An API running on Kubernetes starts timing out after a release. Some pods restart but others are healthy. Explain how you would investigate application logs, readiness and liveness probes, memory limits, and database connections. Explain how you would decide whether to roll back, how you would verify recovery, and what you would change to prevent a recurrence. Use a natural interview answer with enough detail to explain your reasoning. Do not claim this incident happened in my resume.');
    results.push({name:'history',state:await page.evaluate(()=>({messages:currentMessages.length,conversation:!!currentConversationId}))});
    await page.locator('#resumeContextRemove').click();
    await page.waitForFunction(()=>!resumeRemove.disabled);
    await page.reload();await page.waitForTimeout(1000);
    await page.locator('#modeSelect').selectOption('adaptive');
    await question('meeting-actions','Please send the project summary by Friday. Maya will review the budget, and Daniel will schedule the next meeting. Summarize the action items.');
    results.push({name:'resume-remove',state:await page.evaluate(async()=>{await resumeContextReady;return {removed:resumeAnswerContext===null,hidden:resumeStatus.hidden};})});
    await writeFile(`${out}/core.json`,JSON.stringify({results,network},null,2));
    console.log(JSON.stringify({finished:'core',results}));
  }
  if(mode==='inspect') {
    const snapshot=await page.evaluate(()=>({url:location.pathname,title:document.title,text:document.body.innerText.slice(0,14000),buttons:[...document.querySelectorAll('button')].filter(el=>el.getBoundingClientRect().height>0).map(el=>({id:el.id,text:el.innerText,title:el.title}))}));
    await writeFile(`${out}/screen.json`,JSON.stringify(snapshot,null,2));
    await page.screenshot({path:`${out}/current.png`});
    console.log(JSON.stringify(snapshot));
  }
} catch(error) {console.log(JSON.stringify({error:error.message}));process.exitCode=1;}
process.exit(process.exitCode || 0);
