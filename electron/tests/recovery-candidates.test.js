const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../../electron/renderer/app.js'),'utf8').replace(/\r\n/g,'\n');

test('answer routing uses recent inventory without waiting for a stalled refresh', async () => {
 const scope = vm.createContext({Date, AbortSignal, API_BASE:'http://qa', fetch:()=>new Promise(()=>{})});
 vm.runInContext(source.slice(source.indexOf('let runtimeCatalogCache ='), source.indexOf('async function recoveryCandidates(')), scope);
 vm.runInContext('runtimeCatalogCache = {time:Date.now()-31000,models:[{id:"groq-fast"}]}',scope);
 const pending = vm.runInContext('getRuntimeModelCatalog({allowStale:true})',scope);
 const outcome = await Promise.race([pending, new Promise(resolve=>setImmediate(()=>resolve('blocked')))]);
 assert.notEqual(outcome,'blocked','a background refresh must not delay a question');
 assert.equal(outcome[0].id,'groq-fast');
});

test('inventory older than the stale limit waits for fresh data and deduplicates requests', async () => {
 let release, calls=0;
 const scope = vm.createContext({Date, AbortSignal, API_BASE:'http://qa', fetch:()=>{calls++;return new Promise(resolve=>release=resolve)}});
 vm.runInContext(source.slice(source.indexOf('let runtimeCatalogCache ='), source.indexOf('async function recoveryCandidates(')), scope);
 vm.runInContext('runtimeCatalogCache = {time:Date.now()-300001,models:[{id:"removed"}]}',scope);
 const first=vm.runInContext('getRuntimeModelCatalog({allowStale:true})',scope);
 const second=vm.runInContext('getRuntimeModelCatalog({allowStale:true})',scope);
 assert.equal(calls,1);
 release({ok:true,json:async()=>({models:[{id:'new'}]})});
 assert.equal((await first)[0].id,'new');
 assert.equal((await second)[0].id,'new');
});
function setup({settings={},keys={},installed=[],disabled=[],catalog=null}={}) {
 const scope=vm.createContext({getRuntimeModelCatalog:async()=>catalog,getBackendProviders:async()=>keys,appSettings:{get:async key=>settings[key]},
 PROVIDER_META:{'ollama-cloud':{models:[{value:'qa:cloud'}]}},isModelDisabled:model=>disabled.includes(model),
 API_BASE:'http://qa',AbortSignal,fetch:async()=>({ok:true,json:async()=>({models:installed.map(name=>({name}))})})});
 vm.runInContext(source.slice(source.indexOf('function getModelProvider('),source.indexOf('// Update the model provider info bar')),scope);
 vm.runInContext(source.slice(source.indexOf('async function recoveryCandidates('),source.indexOf('async function streamRecoveringAnswer(')),scope);
 return code=>vm.runInContext(code,scope);
}

for (const state of ['cold', 'expired']) {
 test(`explicit cloud text starts without waiting for ${state} local inventory`, async () => {
  const run=setup({keys:{'ollama-cloud':true}});
  // Exercise the real catalog loader, including its unresolved network request.
  run(source.slice(source.indexOf('let runtimeCatalogCache ='),source.indexOf('async function recoveryCandidates(')));
  run('fetch = () => new Promise(() => {})');
  if (state === 'expired') run('runtimeCatalogCache = {time:Date.now()-300001,models:[{id:"removed"}]}');
  const candidates=run('recoveryCandidates("groq-qwen3-8-27b",null)');
  const result=await Promise.race([candidates,new Promise(resolve=>setImmediate(()=>resolve('blocked')))]);
  assert.notEqual(result,'blocked','a chosen cloud model must not wait for local model metadata');
  assert.deepEqual(Array.from(result),['groq-qwen3-8-27b','qa:cloud']);
 });
}

test('nonblocking catalog refresh remains shared with capability-dependent requests',async()=>{
 let release,calls=0;
 const scope=vm.createContext({Date,AbortSignal,API_BASE:'http://qa',fetch:()=>{calls++;return new Promise(resolve=>release=resolve)}});
 vm.runInContext(source.slice(source.indexOf('let runtimeCatalogCache ='),source.indexOf('async function recoveryCandidates(')),scope);
 const quick=vm.runInContext('getRuntimeModelCatalog({allowStale:true,waitForRefresh:false})',scope);
 const outcome=await Promise.race([quick,new Promise(resolve=>setImmediate(()=>resolve('blocked')))]);
 assert.equal(outcome,null);
 const full=vm.runInContext('getRuntimeModelCatalog()',scope);
 assert.equal(calls,1);
 release({ok:true,json:async()=>({models:[{id:'verified:vision',vision:true}]})});
 assert.equal((await full)[0].vision,true);
});

for (const [selected,image] of [['auto',null],['qwen3.5:9b',null],['groq-qwen3-8-27b','image']]) {
 test(`${selected} ${image || 'text'} retains capability discovery`,async()=>{
  const run=setup();
  run(source.slice(source.indexOf('let runtimeCatalogCache ='),source.indexOf('async function recoveryCandidates(')));
  run('fetch = () => new Promise(() => {})');
  const request=run(`recoveryCandidates(${JSON.stringify(selected)},${JSON.stringify(image)})`);
  const result=await Promise.race([request,new Promise(resolve=>setImmediate(()=>resolve('waiting')))]);
  assert.equal(result,'waiting');
 });
}

test('cold explicit-cloud routing still checks live provider opt-outs',async()=>{
 const run=setup({keys:{'ollama-cloud':true},settings:{provider_groq:{enabled:false}}});
 run(source.slice(source.indexOf('let runtimeCatalogCache ='),source.indexOf('async function recoveryCandidates(')));
 run('fetch = () => new Promise(() => {})');
 assert.deepEqual(Array.from(await run('recoveryCandidates("groq-qwen3-8-27b",null)')),['qa:cloud']);
});
test('both cloud suffixes belong to the cloud provider',()=>{
 const run=setup();for(const name of ['qa:cloud','qa:123b-cloud'])assert.equal(run(`getModelProvider('${name}').id`),'ollama-cloud');
});
test('local discovery cannot bypass a disabled cloud provider',async()=>{
 const run=setup({installed:['qa:cloud','qa:123b-cloud','local:small'],settings:{'provider_ollama-cloud':{enabled:false}}});
 assert.deepEqual(Array.from(await run('recoveryCandidates("auto",null)')),['local:small']);
});
test('an explicitly disabled provider never enters recovery',async()=>{
 const run=setup({settings:{provider_openai:{enabled:false}},installed:['local:small']});
 assert.deepEqual(Array.from(await run('recoveryCandidates("openai-custom",null)')),['local:small']);
});
test('disabled local models are excluded and custom explicit selection stays first',async()=>{
 const run=setup({installed:['local:bad','local:good'],disabled:['local:bad']});
 assert.deepEqual(Array.from(await run('recoveryCandidates("custom:chosen",null)')),['custom:chosen']);
});

test('stalled desktop provider discovery has a deadline',async()=>{
 const scope=vm.createContext({window:{api:{getProviders:()=>new Promise(()=>{})}},setTimeout:fn=>setTimeout(fn,10),clearTimeout});
 const start=source.indexOf('async function getBackendProviders()');
 const end=source.indexOf('\n}\n',start)+2;
 vm.runInContext(source.slice(start,end),scope);
 await assert.rejects(vm.runInContext('getBackendProviders()',scope),/timed out/);
});

test('runtime inventory controls candidates and actual vision capability',async()=>{
 const catalog=[{id:'embed:latest',provider:'ollama',configured:true,text:false},
 {id:'fresh:vision',provider:'ollama',configured:true,text:true,vision:true},
 {id:'openai-live',provider:'openai',configured:true,vision:false},
 {id:'openai-stale',provider:'openai',configured:false}];
 const run=setup({catalog});
 assert.deepEqual(Array.from(await run('recoveryCandidates("auto","image")')),['fresh:vision']);
 await assert.rejects(run('recoveryCandidates("openai-live","image")'),/does not support images/);
 assert.deepEqual(Array.from(await run('recoveryCandidates("auto",null)')),['openai-live','fresh:vision']);
});

test('automatic local fallback prefers a smaller compatible model, preserving explicit selection', async()=>{
 const catalog=[
  {id:'large:latest',provider:'ollama',configured:true,text:true,vision:true,size:18e9},
  {id:'tiny:text',provider:'ollama',configured:true,text:true,vision:false,size:1e9},
  {id:'small:vision',provider:'ollama',configured:true,text:true,vision:true,size:2e9},
 ];
 const run=setup({catalog});
 assert.deepEqual(Array.from(await run('recoveryCandidates("auto","image")')),['small:vision']);
 assert.deepEqual(Array.from(await run('recoveryCandidates("auto",null)')),['tiny:text']);
 assert.deepEqual(Array.from(await run('recoveryCandidates("large:latest","image")')),['large:latest']);
});
test('automatic recovery prefers installed Qwen over tiny vision and oversized models',async()=>{
 const catalog=['muse-glimmer:latest','minicpm-v4.6:1b','qwen3.5:9b'].map((id,i)=>({id,provider:'ollama',configured:true,text:true,vision:true,size:[18e9,1.6e9,6.6e9][i]}));
 const run=setup({catalog});assert.deepEqual(Array.from(await run('recoveryCandidates("auto","image")')),['qwen3.5:9b']);
 assert.deepEqual(Array.from(await run('recoveryCandidates("minicpm-v4.6:1b","image")')),['minicpm-v4.6:1b']);
});
test('Auto routes text to fast cloud and screenshots to known cloud vision',async()=>{
 const catalog=[{id:'openai-gpt-4o-mini',provider:'openai',configured:true,vision:true},
 {id:'google-gemini-3-8-flash',provider:'google',configured:true,vision:true},
 {id:'groq-gpt-oss-120b',provider:'groq',configured:true,vision:false},
 {id:'qwen3.5:9b',provider:'ollama',configured:true,vision:true}];
 const run=setup({catalog});
 assert.equal((await run('recoveryCandidates("auto",null)'))[0],'groq-gpt-oss-120b');
 assert.equal((await run('recoveryCandidates("auto","image")'))[0],'google-gemini-3-8-flash');
 assert.equal((await run('recoveryCandidates("openai-gpt-4o-mini",null)'))[0],'openai-gpt-4o-mini');
});

test('configured cloud answer does not wait for optional local discovery',async()=>{
 const run=setup({keys:{'ollama-cloud':true}});
 run('fetch = () => { throw Error("Local discovery must stay off the cloud critical path") }');
 assert.deepEqual(Array.from(await run('recoveryCandidates("auto",null)')),['qa:cloud']);
});

test('catalog reads provider settings once per provider, in parallel',async()=>{
 const run=setup({catalog:[
  {id:'groq-first',provider:'groq',configured:true},
  {id:'groq-second',provider:'groq',configured:true},
  {id:'openai-first',provider:'openai',configured:true},
 ]});
 run(`globalThis.reads = []; globalThis.pending = [];
  appSettings.get = key => { reads.push(key); return new Promise(resolve => pending.push(resolve)) }`);
 const result=run('recoveryCandidates("auto",null)');
 await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(Array.from(run('reads')),['provider_groq','provider_openai']);
 run('pending.forEach(resolve=>resolve({}))');
 assert.deepEqual(Array.from(await result),['groq-first','openai-first']);
});
