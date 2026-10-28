// Visible controlled image -> production OCR -> actual renderer -> local model.
// Browser fixture capture substitutes for native OS capture; no personal profile.
import {chromium} from '@playwright/test';
import {writeFile,mkdir} from 'node:fs/promises';
const output='/tmp/ant-screen-remediation';await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:process.argv.includes("--headless"),args:["--disable-gpu"]});
try {
 const context=await browser.newContext({serviceWorkers:'block'});
 await context.route('**/*',route=>{
  const url=new URL(route.request().url());
  if(['127.0.0.1','localhost'].includes(url.hostname)||['data:','about:'].includes(url.protocol))return route.continue();
  return route.abort();
 });
 const fixture=await context.newPage();
 await fixture.setContent('<body style="font:32px Arial;padding:35px;background:white;color:black"><h1>Numbered questions</h1><p>1. What is 7 + 8?</p><p>2. What is the capital of France?</p></body>');
 
 const page=await context.newPage();
 await page.exposeFunction('captureFixture',async()=>({image:(await fixture.screenshot({type:'jpeg'})).toString('base64'),capturedAt:Date.now(),displayId:'controlled-fixture',source:'fresh'}));
 await page.goto('http://127.0.0.1:8048/index.html');
 await page.waitForFunction(()=>typeof submitText==='function');
 await page.evaluate(async()=>{
  window.api ||= {};
  window.api.getOcrUrl=()=>"http://127.0.0.1:8046/ocr";
  window.api.captureScreenshotContext=()=>window.captureFixture();
  window.api.captureScreenshot=async()=>(await window.captureFixture()).image;
  window.api.autoScreenshotGetStatus=async()=>({enabled:true});
  recoveryCandidates=async()=>['qwen3.5:9b']; // Restrict QA to installed local inference.
  const option=new Option('QA local Qwen','qwen3.5:9b');modelSelect.add(option);modelSelect.value=option.value;
 });
 const results=[];
 for(const [question,check] of [
  ['Answer all visible questions',answer=>/15/.test(answer)&&/Paris/i.test(answer)],
  ['Answer the question on screen',answer=>/which|specify|clarif|1 or 2|1 and 2/i.test(answer)],
 ]) {
  await page.evaluate(q=>submitText(q),question);
  const answer=await page.evaluate(()=>currentMessages.filter(m=>m.role==='assistant').at(-1)?.text || '');
  results.push({question,answer,passed:check(answer)});
 }
 await fixture.setContent('<body style="font:32px Arial;padding:35px;background:white;color:black"><h1>Updated question</h1><p>3. What is 9 + 6?</p></body>');
 await page.evaluate(()=>submitText('Answer question 3 on screen'));
 const answer=await page.evaluate(()=>currentMessages.filter(m=>m.role==='assistant').at(-1)?.text || '');
 results.push({question:'Updated fixture: question 3',answer,passed:/15/.test(answer)});
 const metadata=await page.evaluate(()=>currentMessages.filter(m=>m.role==='user').map(m=>m.captureMetadata));
 results.push({question:'Fresh capture metadata per question',passed:metadata.length===3&&metadata.every(m=>m.displayId==='controlled-fixture')&&metadata[2].capturedAt>metadata[0].capturedAt});
 await page.screenshot({path:output+'/answers.png'});
 await writeFile(output+'/results.json',JSON.stringify({scope:'Controlled browser screenshots, real OCR, real renderer and local Qwen; native OS capture not exercised',results},null,2));
 console.log(JSON.stringify(results,null,2));
 if(results.some(r=>!r.passed))process.exitCode=1;
} finally {await browser.close();}
