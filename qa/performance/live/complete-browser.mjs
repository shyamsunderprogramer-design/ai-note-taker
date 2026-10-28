// Actual UI workflows on disposable accounts/data. No personal desktop profile.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const out=resolve('qa/performance/results/2026-10-02-complete');await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:false,args:['--use-fake-device-for-media-stream']});
const context=await browser.newContext({viewport:{width:1100,height:800},serviceWorkers:'block'});
await context.route('**/*',route=>{
 const url=new URL(route.request().url());
 return ['127.0.0.1','localhost'].includes(url.hostname)||!['http:','https:'].includes(url.protocol)?route.continue():route.fulfill({status:503,body:'External service disabled in QA'});
});
const rows=[];const errors=[];const page=await context.newPage();page.setDefaultTimeout(10000);
page.on('pageerror',error=>errors.push(error.message));
page.on('dialog',dialog=>dialog.dismiss());
await context.addInitScript(()=>localStorage.setItem('hasOnboarded','true'));
const origin='http://127.0.0.1:8048';
async function check(name,fn){try{rows.push({name,status:'passed',detail:await fn()})}catch(error){rows.push({name,status:'failed',detail:error.message.slice(0,1800)})}await writeFile(out+'/browser-workflows.json',JSON.stringify({checks:rows,scriptErrors:errors},null,2));console.log(JSON.stringify(rows.at(-1)))}
const user='browser_'+Date.now();
try {
 const registration=await context.request.post('http://127.0.0.1:8046/auth/register',{form:{username:user,email:user+'@example.com',password:'TestPass123!'}});
 assert.ok(registration.ok());
 await check('Sign in through actual form',async()=>{
  await page.goto(origin+'/signin.html');await page.locator('#siUser').fill(user);await page.locator('#siPass').fill('TestPass123!');await page.locator('#siBtn').click();
  await page.waitForURL('**/index.html');return 'Disposable account signed in';
 });
 await check('Settings tabs and model selector',async()=>{
  await page.locator('#gearBtn').click();
  for(const tab of ['general','providers','models','voice','clone','data','integrations']){
   await page.locator(`.settings-tab[data-tab="${tab}"]`).click();assert.ok(await page.locator(`.settings-tab-content[data-content="${tab}"]`).isVisible());
  }
  await page.locator('#closeSettingsBtn').click();
  const options=await page.locator('#modelSelect option').count();assert.ok(options>1);return {tabs:7,modelOptions:options};
 });
 await check('Job description save/cancel/reload/remove',async()=>{
  const open=async()=>{if(!await page.locator('#jobDescriptionButton').isVisible())await page.locator('#answerContextButton').click();await page.locator('#jobDescriptionButton').click()};
  await open();await page.locator('#jobDescriptionInput').fill('Synthetic role: Python engineer building tested APIs.');await page.locator('#jobDescriptionSave').click();
  await page.reload();await open();assert.match(await page.locator('#jobDescriptionInput').inputValue(),/Synthetic role/);
  await page.locator('#jobDescriptionInput').fill('Unsaved edit');await page.locator('#jobDescriptionCancel').click();await open();assert.match(await page.locator('#jobDescriptionInput').inputValue(),/Synthetic role/);
  await page.locator('#jobDescriptionRemove').click();await page.reload();await open();assert.equal(await page.locator('#jobDescriptionInput').inputValue(),'');await page.locator('#jobDescriptionCancel').click();
  return 'Saved context persists; cancel preserves it; remove clears it';
 });
 await check('Denied microphone produces actionable error',async()=>{
  await page.evaluate(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Denied by synthetic test','NotAllowedError')}});
  await page.locator('#listenBtn').click();
  await page.waitForFunction(()=>/microphone|permission/i.test(document.querySelector('#chatArea')?.textContent||''));
  const result=await page.evaluate(()=>({processing:isProcessing,text:document.querySelector('#chatArea')?.textContent||''}));
  assert.match(result.text,/denied|permission|allow|access/i);assert.equal(result.processing,false);return 'Permission-denial UI releases processing state (injected rejection)';
 });
 let jobId,jobRequest;
 await check('Create job in actual UI and reload',async()=>{
  await page.goto(origin+'/job-tracker.html');await page.getByRole('button',{name:/Add Application/}).first().click();
  await page.locator('#companyInput').fill('Synthetic Browser Labs');await page.locator('#roleInput').fill('Python engineer');await page.locator('#notesInput').fill('Synthetic note must persist');
  const result=page.waitForResponse(response=>response.url().includes('/job-tracker/application?')&&response.request().method()==='POST');
  await page.locator('#addJobForm button[type="submit"]').click();const response=await result;jobRequest=response.request().url();assert.ok(response.ok(),'Job creation HTTP '+response.status()+'; authenticated UI must forward its token to configured API');jobId=(await response.json()).application.id;
  await page.reload();await page.locator('.job-card').filter({hasText:'Synthetic Browser Labs'}).waitFor();return 'Application survives page reload';
 });
 await check('Job form preserves notes',async()=>{
  assert.ok(jobRequest,'Job submission prerequisite failed');assert.equal(new URL(jobRequest).searchParams.get('notes'),'Synthetic note must persist','The actual submitted request omitted form notes');return 'Notes submitted';
 });
 await check('Job card opens a usable detail view',async()=>{
  if(!jobId){
   const token=await page.evaluate(()=>localStorage.getItem('ainotetaker_auth_token'));
   const response=await context.request.post('http://127.0.0.1:8046/job-tracker/application',{headers:{Authorization:'Bearer '+token},params:{company:'Synthetic Browser Labs',role:'Python engineer'}});
   assert.ok(response.ok(),'Independent synthetic job seed failed');jobId=(await response.json()).application.id;await page.reload();
  }
  await page.locator('.job-card').filter({hasText:'Synthetic Browser Labs'}).first().click();
  const visible=await page.locator('dialog[open], [role="dialog"], .modal-overlay.active').count();assert.ok(visible>0,'Clicking the job card opens no detail dialog');return 'Details opened';
 });
 await check('Study plan generation and browser completion persistence',async()=>{
  await page.goto(origin+'/study-plan.html');await page.locator('#roleInput').fill('Python engineer');await page.locator('#skillsInput').fill('Python');await page.locator('#generateBtn').click();
  await page.locator('#planContent').waitFor({state:'visible'});const boxes=page.locator('.task-checkbox');
  await boxes.first().click();const before=await page.locator('#completedTasks').innerText();assert.notEqual(before,'0');
  await page.reload();await page.locator('#planContent').waitFor({state:'visible'});assert.equal(await page.locator('#completedTasks').innerText(),before);return {completedBefore:before,completedAfter:await page.locator('#completedTasks').innerText(),storage:'Browser-local persistence; backend tested separately'};
 });
 await check('Job tracker unavailable-backend state',async()=>{
  await page.route('**/job-tracker/**',route=>route.fulfill({status:503,json:{detail:'Backend unavailable'}}));
  try{await page.goto(origin+'/job-tracker.html');await page.waitForTimeout(1000);const text=await page.locator('body').innerText();assert.match(text,/unavailable|could not|failed|try again|retry/i);return 'Visible actionable unavailable state'}finally{await page.unroute('**/job-tracker/**')}
 });
 const layout=[];const labels=[];
 for(const file of ['index.html','job-tracker.html','study-plan.html','resume-review-v2.html','interview-simulator.html','analytics-dashboard.html']){
  await page.goto(origin+'/'+file);await page.waitForTimeout(300);
  for(const width of [390,960,1440]){
   await page.setViewportSize({width,height:800});
   const dimensions=await page.evaluate(()=>({width:innerWidth,content:document.documentElement.scrollWidth}));
   layout.push({page:file,...dimensions,passed:dimensions.content<=dimensions.width+2});
  }
  const unnamed=await page.evaluate(()=>[...document.querySelectorAll('button,input:not([type="hidden"]),select,textarea')].filter(el=>el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden').filter(el=>!el.getAttribute('aria-label')&&!el.getAttribute('aria-labelledby')&&!el.title&&!el.labels?.length&&!(el.tagName==='BUTTON'&&el.textContent.trim())).map(el=>({tag:el.tagName,id:el.id,type:el.type})));labels.push({page:file,unnamed});
 }
 rows.push({name:'Responsive document overflow',status:layout.every(item=>item.passed)?'passed':'failed',detail:layout});
 rows.push({name:'Visible control accessible-name precheck',status:labels.every(item=>!item.unnamed.length)?'passed':'failed',detail:labels,scope:'Name-presence precheck only; not a full accessibility conformance audit'});
 await writeFile(out+'/browser-workflows.json',JSON.stringify({checks:rows,scriptErrors:errors},null,2));
 console.log(JSON.stringify(rows.slice(-2)));
 await page.screenshot({path:out+'/browser-final.png'});
} finally {await browser.close()}
process.exitCode=rows.some(item=>item.status==='failed')?1:0;
