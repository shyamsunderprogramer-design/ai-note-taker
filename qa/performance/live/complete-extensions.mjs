// Install each original extension into its own disposable Chromium profile.
import {chromium} from '@playwright/test';
import {mkdtemp, mkdir, readFile, writeFile, cp} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve, join} from 'node:path';
const out=resolve('qa/performance/results/2026-10-02-complete');
await mkdir(out,{recursive:true});
const results=[];
for(const name of ['chrome-extension','browser-extension','chrome-extension-diagnostic']) {
 let context;
 const record={name,status:'failed',checks:[],errors:[]};
 try {
  let directory=resolve(name.replace('-diagnostic',''));
  const manifest=JSON.parse(await readFile(join(directory,'manifest.json'),'utf8'));
  if(name.endsWith('-diagnostic')) {
   const copy=await mkdtemp(join(tmpdir(),'ant-extension-manifest-diagnostic-'));
   await cp(directory,copy,{recursive:true});directory=copy;
   manifest.content_scripts[1].matches=manifest.content_scripts[1].matches.filter(pattern=>pattern!=='*://careers.*.com/*');
   await writeFile(join(copy,'manifest.json'),JSON.stringify(manifest));
   record.scope='Temporary diagnostic copy removes only careers.*.com wildcard; original product remains unchanged';
  }
  const profile=await mkdtemp(join(tmpdir(),'ant-extension-'));
  context=await chromium.launchPersistentContext(profile,{channel:'chromium',headless:true,ignoreDefaultArgs:['--disable-extensions'],
   args:[`--disable-extensions-except=${directory}`,`--load-extension=${directory}`]});
  // Never send extension requests to the user's backend or external services.
  await context.route('**/*',route=>{
   const url=new URL(route.request().url());
   if(!['http:','https:'].includes(url.protocol)) return route.continue();
   if(url.hostname==='www.linkedin.com')return route.fulfill({contentType:'text/html',body:'<html><head><title>Python engineer at Synthetic Labs</title><meta property="og:title" content="Python engineer at Synthetic Labs"></head><body><h1>Python engineer</h1><p class="location">Remote</p></body></html>'});
   if(url.pathname==='/health')return route.fulfill({json:{status:'ok'}});
   if(url.pathname==='/job-tracker/stats')return route.fulfill({json:{total_applications:0,total_applied:0,pipeline:{}}});
   return route.fulfill({status:503,json:{detail:'External access disabled in extension QA'}});
  });
  const manager=await context.newPage();
  await manager.goto('chrome://extensions/');
  await manager.waitForTimeout(1500);
  const inventory=await manager.evaluate(()=>{
   const root=document.querySelector('extensions-manager')?.shadowRoot;
   const list=root?.querySelector('extensions-item-list')?.shadowRoot;
   return [...(list?.querySelectorAll('extensions-item') || [])].map(item=>({id:item.data?.id || item.id,name:item.data?.name,errors:item.data?.manifestErrors}));
  });
  record.inventory=inventory;
  const extension=inventory.find(item=>item.name===manifest.name);
  if(!extension)throw Error('Original extension did not load in Chromium; no matching installed entry.');
  record.checks.push('Original manifest installed');
  const popup=await context.newPage();
  popup.on('pageerror',error=>record.errors.push(error.message));
  await popup.goto(`chrome-extension://${extension.id}/${manifest.action.default_popup}`);
  await popup.waitForTimeout(1200);
  record.popupTitle=await popup.title();
  record.checks.push('Popup opened with real extension APIs and stubbed network');
  const storage=await popup.evaluate(async()=>{
   await chrome.storage.local.set({qaRoundTrip:'synthetic'});
   const saved=await chrome.storage.local.get('qaRoundTrip');
   await chrome.storage.local.remove('qaRoundTrip');
   return saved.qaRoundTrip==='synthetic';
  });
  if(!storage)throw Error('Extension storage round trip failed');
  record.checks.push('Real extension storage round trip');
  if(name==='browser-extension') {
   record.protectedTabErrors=[...record.errors];record.errors.length=0;
   const fixture=await context.newPage();await fixture.goto('https://www.linkedin.com/jobs/view/123');
   await fixture.bringToFront();await popup.reload();await popup.waitForTimeout(1500);
   record.detectedCompany=await popup.locator('#companyInput').inputValue();
   record.detectedRole=await popup.locator('#roleInput').inputValue();
   if(record.detectedCompany!=='Synthetic Labs'||record.detectedRole!=='Python engineer')throw Error('Supported synthetic job page was not extracted');
   record.checks.push('Supported page extraction via real extension scripting API');
   await popup.locator('#companyInput').fill('');await popup.locator('#captureBtn').click();
   if(!/enter company/i.test(await popup.locator('#errorMsg').innerText()))throw Error('Empty company not rejected');
   record.checks.push('Empty capture form rejected');
   if(record.protectedTabErrors.length)throw Error('Protected/unavailable tab crashes popup: '+record.protectedTabErrors.join('; '));
  }
  if(manifest.background) {
   const state=await popup.evaluate(()=>new Promise(resolve=>chrome.runtime.sendMessage({action:'get-recording-state'},resolve)));
   record.recordingState=state?.status;
   if(state?.status!=='idle')throw Error('Unexpected initial recording state');
   record.checks.push('Background recording state is idle');
  }
  if(record.errors.length)throw Error('Popup script error: '+record.errors.join('; '));
  await popup.screenshot({path:join(out,name+'-popup.png')});
  record.status='passed';
 } catch(error) {record.error=error.message.slice(0,1500)}
 finally {if(context)await context.close()}
 results.push(record);
 await writeFile(join(out,'extensions.json'),JSON.stringify(results,null,2));
 console.log(JSON.stringify(record));
}
process.exitCode=results.some(record=>record.status==='failed')?1:0;
