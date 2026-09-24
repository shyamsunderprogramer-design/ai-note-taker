import {chromium} from '@playwright/test';
import {readFile,writeFile,access,unlink} from 'node:fs/promises';
const fixtureBrowser=await chromium.launch({headless:false,args:['--start-maximized']});
const fixture=await fixtureBrowser.newPage({viewport:null});
await fixture.setContent('<html><body style="background:white;color:black;font:32px Arial;padding:60px"><h1>SCREEN CONTEXT PROBE 7341</h1><h2>Project budget review</h2><p>Cedar: budget $4,800; spent $6,200.</p><p>Maple: budget $3,000; spent $2,700.</p><p>Use this table to answer the spoken or typed question.</p></body></html>');
await fixture.bringToFront();
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
const page=browser.contexts()[0].pages().find(p=>/index.html|signin.html/.test(p.url()));
if(!page)throw Error('Sign in to the visible app is required');
await page.bringToFront();
if(process.argv.includes('--replay-question')) await page.reload();
if (!process.argv.includes('--capture-only')) await page.waitForFunction(()=>typeof getQuestionScreenContext==='function', {}, {timeout:60000});
if(process.argv.includes('--no-blink')) {
 await page.evaluate(()=>{
  window.captureVisibilityEvents=[];
  document.addEventListener('visibilitychange',()=>window.captureVisibilityEvents.push(document.hidden));
  const marker=document.createElement('div');marker.id='capture-self-marker';marker.textContent='ANT SELF CAPTURE 9274';
  marker.style.cssText='position:fixed;top:20px;left:20px;z-index:999999;background:white;color:black;font:30px Arial;padding:15px';document.body.appendChild(marker);
 });
}
await page.evaluate(interval=>window.api.autoScreenshotSetEnabled(true,interval),process.argv.includes('--no-blink') ? 3000 : 60000);
const context=await page.evaluate(async()=>{const image=await window.api.captureScreenshot();const response=await fetch('http://127.0.0.1:8000/ocr',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_b64:image})}); if(!response.ok)throw Error('OCR returned '+response.status);const ocr=await response.json();return {image,text:ocr.text||''}});
await writeFile('/tmp/ant-visible-desktop/excluded-app-screen.jpg',Buffer.from(context.image,'base64'));
const capture={fixtureRead:/Cedar/.test(context.text)&&/6,200|6200/.test(context.text),appExcluded:!/AI Note Taker|Protection off|Summarize|Ask anything|ANT SELF CAPTURE|9274/.test(context.text)};
console.log(JSON.stringify({capture}));
if(!capture.fixtureRead||!capture.appExcluded)throw Error('Screen exclusion or OCR did not pass');
if(process.argv.includes('--no-blink')) {
 await page.waitForTimeout(12000);
 const visibility=await page.evaluate(()=>({hidden:document.hidden,events:window.captureVisibilityEvents}));
 console.log(JSON.stringify({visibility}));
 await page.evaluate(()=>document.getElementById('capture-self-marker')?.remove());
 await writeFile('qa/performance/results/2026-09-23-no-blink.json',JSON.stringify({capture,visibility,passed:capture.fixtureRead&&capture.appExcluded&&!visibility.hidden&&!visibility.events.includes(true)},null,2));
 if(visibility.hidden||visibility.events.includes(true))throw Error('ANT became hidden during capture');
}
if(process.argv.includes('--capture-only')){await writeFile('qa/performance/results/2026-09-23-screen-exclusion.json',JSON.stringify(capture));await fixtureBrowser.close();await page.bringToFront();await browser.close();process.exit(0);}
const results=[];
await page.locator('#modelSelect').selectOption('groq-gpt-oss-120b');
const modes=process.argv.includes('--replay-question') ? ['replayed-microphone-question'] : ['typed',process.argv.includes('--live-mic') ? 'live-microphone' : 'voice'];
for(const mode of modes){
 const start=Date.now();const before=await page.locator('.chat-message.assistant').count();
 if(mode==='replayed-microphone-question'){
  const previous=JSON.parse(await readFile('qa/performance/results/2026-09-23-live-screen-microphone.json','utf8'));
  const text=previous.results.find(r=>r.mode==='live-microphone').transcript.split('YOU\n\n')[1];
  await page.locator('#textInput').fill(text);await page.locator('#textInput').press('Enter');
 }else if(mode==='typed'){
  await page.locator('#textInput').fill('Which project is above budget, and by how much?');await page.locator('#textInput').press('Enter');
 }else if(mode==='live-microphone'){
  const stopFile='/tmp/ant-visible-desktop/stop-live-mic';
  await unlink(stopFile).catch(()=>{});
  await page.locator('#textInput').fill('');
  await page.locator('#listenBtn').click();
  await page.waitForFunction(()=>isListening && mediaRecorder?.state==='recording', {}, {timeout:15000});
  console.log(JSON.stringify({microphone:'recording',instruction:'Ask: Which project is above budget, and by how much?'}));
  const deadline=Date.now()+90000;
  while(Date.now()<deadline){
    if(await access(stopFile).then(()=>true).catch(()=>false))break;
    await page.waitForTimeout(500);
  }
  if(await page.evaluate(()=>isListening))await page.locator('#listenBtn').click();
 }else{
  const audio=await readFile('/tmp/ant-screen-question.aiff');
  await page.evaluate(async bytes=>{await submitAudio(new Blob([new Uint8Array(bytes)],{type:'audio/aiff'}));},Array.from(audio));
 }
 await page.waitForFunction(count=>document.querySelectorAll('.chat-message.assistant').length>count,before,{timeout:60000});
 await page.waitForFunction(()=>!isProcessing,{},{timeout:90000});
 const answer=await page.locator('.chat-message.assistant').last().innerText();
 const passed=mode==='replayed-microphone-question' ? /\?/.test(answer) && !/can.t help with that/i.test(answer) : /Cedar/i.test(answer)&&/1,400|1400/.test(answer);
 const transcript=await page.locator('.chat-message.user').last().innerText();
 results.push({mode,seconds:(Date.now()-start)/1000,transcript,answer,passed});console.log(JSON.stringify(results.at(-1)));
 await page.screenshot({path:`/tmp/ant-visible-desktop/screen-${mode}.png`});
 await page.waitForTimeout(2500);
}
await writeFile(process.argv.includes('--replay-question') ? 'qa/performance/results/2026-09-23-voice-question-replay.json' : process.argv.includes('--live-mic') ? 'qa/performance/results/2026-09-23-live-screen-microphone.json' : 'qa/performance/results/2026-09-23-screen-question.json',JSON.stringify({capture,results,limits:process.argv.includes('--replay-question') ? 'Exact transcript from the earlier physical microphone run resubmitted through visible UI after prompt fix; this is not another microphone recording.' : process.argv.includes('--live-mic') ? 'Actual desktop capture, native microphone MediaRecorder, production transcription, real cloud inference and visible rendered answers. Controlled reference page on the physical display.' : 'Actual desktop capture and OCR; real cloud inference; synthetic speech file through production transcription, not physical microphone.'},null,2));
await fixtureBrowser.close();await page.bringToFront();await browser.close();
if(results.some(r=>!r.passed))process.exitCode=1;
