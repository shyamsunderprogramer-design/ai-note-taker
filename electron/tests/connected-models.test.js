const {test} = require('node:test');
const assert = require('node:assert/strict');
const {createOllamaAccount, cloudName} = require('../lib/ollama-account');
const {createConnectedModels} = require('../lib/connected-models');
const {frames, validateRequest, createSubscriptionService} = require('../lib/subscriptions');
const {createSubscriptionAuth, PERMISSION} = require('../lib/subscription-auth');
const json = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), {status, headers});
const ndjson = events => new Response(events.map(e => JSON.stringify(e)).join('\n'));
const cloud = 'gpt-oss:120b-cloud', second = 'other:cloud', local = 'local:small';
const signal = () => new AbortController().signal;

function fixture(overrides = {}, behavior = {}) {
  let data = {accounts: [{id:'one', email:'test@example.test', access_token:'secret', expires_at:Date.now()+3600000, scopes:[PERMISSION]}], active:'one',
    primary:'chatgpt', crossFallback:true, fallback:local, ollamaEnabled:true, ollamaAccount:'tester', ollamaModel:cloud, ...overrides};
  const calls = [], opened = [];
  const fetch = async (url, options = {}) => {
    calls.push({url, options});
    const pathname = new URL(url).pathname;
    if (pathname === '/v1/models') return json({models:[{slug:'chat-model', display_name:'Chat model', visibility:'list'}]});
    if (pathname === '/v1/responses') return behavior.chatgpt?.() || json({error:{}},429);
    assert.equal(new URL(url).origin, 'http://127.0.0.1:11434');
    assert.equal(options.headers?.Authorization, undefined);
    assert.equal(options.redirect, 'error');
    if (pathname === '/api/me') { assert.equal(options.method, 'POST'); return behavior.identity?.() || json({name:'tester'}); }
    if (pathname === '/api/tags') return json({models: behavior.tags || [{name:cloud, remote_host:'https://ollama.com'}, {name:second}, {name:local}]});
    if (pathname === '/api/show') return json(behavior.show || {capabilities:['completion','vision']});
    if (pathname === '/api/pull') return json({status:'success'});
    if (pathname === '/api/chat') {
      const body = JSON.parse(options.body);
      return behavior.ollama?.(body) || ndjson([{message:{content:body.model===local?'Local answer':'Cloud answer'}},{done:true}]);
    }
    throw Error(`Unexpected route: ${pathname}`);
  };
  const vault = {get:() => data, set:value => {data=value;}};
  const auth = createSubscriptionAuth({vault, fetch});
  const chatgpt = createSubscriptionService({auth, fetch});
  const ollama = createOllamaAccount({fetch, frames, openExternal:async url => opened.push(url)});
  const service = createConnectedModels({auth, chatgpt, ollama, validateRequest});
  return {service, ollama, calls, opened, vault, behavior, events:[],
    async run(request = {query:'Question', messages:[{role:'system',content:'Context'}]}) {const events=[]; await service.stream(request,e=>events.push(e),signal()); return events;}};
}
const chats = f => f.calls.filter(c => new URL(c.url).pathname === '/api/chat');

test('Ollama login opens only official sign-in URLs; public status excludes sign-in material', async () => {
  const f = fixture({ollamaEnabled:false}, {identity:() => json({signin_url:'https://ollama.com/connect?key=private'},401)});
  const status = await f.service.connectOllama();
  assert.equal(status.ollamaLoginPending,true);
  assert.equal(f.opened.length,1);
  assert.equal(JSON.stringify(status).includes('private'),false);
  f.behavior.identity=() => json({name:'tester'});
  assert.equal((await f.service.refresh()).ollama.enabled,true);
  assert.equal(f.vault.get().ollamaAccount,'tester');
  for (const url of ['https://evil.test/connect','https://ollama.com.evil.test','https://user@ollama.com','javascript:alert(1)']) {
    const bad = fixture({}, {identity:() => json({signin_url:url},401)});
    await assert.rejects(bad.service.connectOllama(),/invalid sign-in/);
    assert.equal(bad.opened.length,0);
  }
});

test('Existing Ollama login requires explicit connection; disconnect affects ANT only', async () => {
  const f = fixture({primary:'ollama-cloud',ollamaEnabled:false});
  assert.equal((await f.service.refresh()).ollama.enabled,false);
  await assert.rejects(f.run(),/Connect your Ollama/);
  assert.equal((await f.service.connectOllama()).ollama.enabled,true);
  await f.run();
  f.service.disconnectOllama();
  await assert.rejects(f.run(),/Connect your Ollama/);
  assert.equal(f.calls.some(c => c.url.endsWith('/api/signout')),false);
});

test('Cancelled Ollama sign-in does not enable ANT when browser sign-in later completes', async () => {
  const f = fixture({ollamaEnabled:false}, {identity:() => json({signin_url:'https://ollama.com/connect'},401)});
  await f.service.connectOllama(); f.service.cancelOllama();
  f.behavior.identity=() => json({name:'tester'});
  assert.equal((await f.service.refresh()).ollama.enabled,false);
});

test('ChatGPT 429 switches once to opted-in Ollama with context; next request skips paused plan', async () => {
  const f = fixture();
  const events = await f.run();
  assert.equal(events.find(e=>e.type==='chunk').content,'Cloud answer');
  assert.ok(events.some(e=>e.type==='notice' && /switched to Ollama/.test(e.message)));
  assert.equal(f.vault.get().accounts[0].paused,true);
  assert.deepEqual(JSON.parse(chats(f)[0].options.body).messages,[{role:'system',content:'Context'},{role:'user',content:'Question'}]);
  await f.run();
  assert.equal(f.calls.filter(c=>c.url.endsWith('/responses')).length,1);
  assert.equal(chats(f).length,2);
});

test('Two exhausted plans switch to selected local model and persist both pauses', async () => {
  const f = fixture({}, {ollama:body => body.model===cloud ? json({error:'usage limit'},429,{'Retry-After':'120'}) : ndjson([{message:{content:'Recovered'}},{done:true}])});
  const events = await f.run();
  assert.deepEqual(chats(f).map(c=>JSON.parse(c.options.body).model),[cloud,local]);
  assert.equal(f.vault.get().ollamaPaused,true);
  assert.ok(f.vault.get().ollamaRetryAt>Date.now());
  await assert.rejects(f.service.settings({retryOllama:true}),/wait before retrying/);
  assert.equal(events.filter(e=>e.type==='done').length,1);
  await f.run();
  assert.deepEqual(chats(f).map(c=>JSON.parse(c.options.body).model),[cloud,local,local]);
});

test('Cross-account fallback is opt-in; unconfigured alternative is skipped', async () => {
  for (const settings of [{crossFallback:false},{ollamaEnabled:false},{ollamaModel:''}]) {
    const f=fixture(settings); await f.run();
    assert.deepEqual(chats(f).map(c=>JSON.parse(c.options.body).model),[local]);
  }
  const f=fixture({crossFallback:false,fallback:''});
  await assert.rejects(f.run(),/429/); assert.equal(chats(f).length,0);
});

test('Ollama can be primary with no ChatGPT account and can fall back in the other direction', async () => {
  const only=fixture({primary:'ollama-cloud',accounts:[],active:'',crossFallback:false});
  await only.run(); assert.equal(only.calls.some(c=>c.url.includes('openai.com')),false);
  const f=fixture({primary:'ollama-cloud'}, {
    ollama:()=>json({},429), chatgpt:()=>new Response('data: {"type":"response.output_text.delta","delta":"Chat answer"}\n\ndata: {"type":"response.completed"}\n\n'),
  });
  const events=await f.run();
  assert.ok(events.some(e=>e.type==='chunk' && e.content==='Chat answer'));
  assert.ok(events.some(e=>e.type==='notice' && /switched to ChatGPT/.test(e.message)));
});

test('Changed identity and non-limit failures stop instead of sending to another provider', async () => {
  const f=fixture({primary:'ollama-cloud'}, {identity:()=>json({name:'someone-else'})});
  await assert.rejects(f.run(),/account changed/); assert.equal(chats(f).length,0);
  for (const status of [401,403,500]) {
    const failed=fixture({primary:'ollama-cloud'}, {ollama:()=>json({},status)});
    await assert.rejects(failed.run());
    assert.equal(chats(failed).length,1);
    assert.equal(failed.calls.some(c=>c.url.includes('openai.com')),false);
  }
});

test('Partial answers are reset when the fallback stream starts, and failed fallback preserves them', async () => {
  const failure=()=>new Response('data: {"type":"response.output_text.delta","delta":"Partial"}\n\ndata: {"type":"error","error":{"code":"rate_limit_exceeded"}}\n\n');
  const f=fixture({}, {chatgpt:failure});
  const events=await f.run();
  assert.equal(events.filter(e=>e.type==='reset').length,1);
  assert.ok(events.findIndex(e=>e.type==='reset')>events.findIndex(e=>e.content==='Partial'));
  assert.ok(events.findIndex(e=>e.content==='Cloud answer')>events.findIndex(e=>e.type==='reset'));
  const failed=fixture({}, {chatgpt:failure,ollama:()=>json({},500)}), seen=[];
  await assert.rejects(failed.service.stream({query:'Question'},e=>seen.push(e),signal()));
  assert.ok(seen.some(e=>e.content==='Partial')); assert.equal(seen.some(e=>e.type==='reset'),false);
});

test('Streamed quota errors persist a pause; cancellation never starts fallback', async () => {
  const f=fixture({primary:'ollama-cloud',crossFallback:false},{ollama:body=>body.model===cloud?ndjson([{error:'usage limit exceeded (429)'}]):ndjson([{done:true}])});
  await f.run(); assert.equal(f.vault.get().ollamaPaused,true);
  const cancelled=fixture(), controller=new AbortController();
  await assert.rejects(cancelled.service.stream({query:'Question'},()=>controller.abort(),controller.signal),/abort/i);
  assert.equal(chats(cancelled).length,0);
});

test('Only safe cloud references are added; model changes persist and unknown choices fail', async () => {
  const f=fixture(); await f.service.refresh();
  await f.service.settings({ollamaModel:second,primary:'ollama-cloud'});
  assert.equal(f.service.status().ollama.model,second);
  await assert.rejects(f.service.settings({ollamaModel:'unknown:cloud'}),/available/);
  await assert.rejects(f.service.settings({primary:'arbitrary'}),/Unsupported/);
  for(const name of ['local:small','https://evil.test/x','x; echo secret','../../cloud']) {
    assert.equal(cloudName(name),false); await assert.rejects(f.service.addOllamaModel(name),/cloud model name/);
  }
  await f.service.addOllamaModel(cloud);
  const pulls=f.calls.filter(c=>c.url.endsWith('/api/pull'));
  assert.equal(pulls.length,1); assert.deepEqual(JSON.parse(pulls[0].options.body),{model:cloud,stream:false});
});

test('Model routing and vision checks run before any prompt is sent', async () => {
  for(const behavior of [{tags:[{name:cloud,remote_host:'https://evil.test'}]}, {show:{remote_host:'https://evil.test'}}, {show:{capabilities:['completion']}}]) {
    const f=fixture({primary:'ollama-cloud'},behavior);
    await assert.rejects(f.run({query:'Question',image_b64:'aW1hZ2U='})); assert.equal(chats(f).length,0);
  }
  const f=fixture({crossFallback:false},{tags:[{name:local,remote_model:'remote'}]});
  await assert.rejects(f.run(),/not a local/); assert.equal(chats(f).length,0);
});
