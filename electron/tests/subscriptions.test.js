const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {createVault, createSubscriptionAuth, PERMISSION, tokenSet} = require('../lib/subscription-auth');
const {createSubscriptionService, frames, registerSubscriptionIPC} = require('../lib/subscriptions');
const account = () => ({id: 'account-1', client_id: 'issued-client', subject: 'person', email: 'person@example.test', access_token: 'secret-access', refresh_token: 'secret-refresh', expires_at: Date.now() + 3600000, scopes: [PERMISSION], model: 'model-one'});
function fixture(data = {}) {
  let value = {host: 'urn:uuid:host', accounts: [account()], active: 'account-1', fallback: '', ...data};
  return {get: () => value, set: next => { value = next; }};
}
const json = (data, status = 200, headers = {}) => new Response(JSON.stringify(data), {status, headers});
const sse = events => new Response(events.map(e => `data: ${JSON.stringify(e)}\n\n`).join(''));
const completed = () => sse([{type: 'response.output_text.delta', delta: 'Answer'}, {type: 'response.completed'}]);
function setup(fetch, data) {
  const vault = fixture(data), auth = createSubscriptionAuth({vault, fetch});
  return {vault, auth, service: createSubscriptionService({auth, fetch})};
}
const catalog = () => json({models: [{slug: 'hidden', display_name: 'Hidden', visibility: 'hide'}, {slug: 'model-one', display_name: 'My model', visibility: 'list'}]});

test('vault persists encrypted tokens and stable host with private permissions', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'ant-subscription-'));
  t.after(() => fs.rmSync(directory, {recursive: true, force: true}));
  const key = crypto.randomBytes(32);
  const safeStorage = {isEncryptionAvailable: () => true,
    encryptString: s => { const iv = crypto.randomBytes(16), c = crypto.createCipheriv('aes-256-cbc', key, iv); return Buffer.concat([iv, c.update(s), c.final()]); },
    decryptString: b => { const c = crypto.createDecipheriv('aes-256-cbc', key, b.subarray(0, 16)); return Buffer.concat([c.update(b.subarray(16)), c.final()]).toString(); }};
  const first = createVault(directory, safeStorage), host = first.get().host;
  first.set({...first.get(), accounts: [account()]});
  assert.equal(createVault(directory, safeStorage).get().host, host);
  const filename = path.join(directory, 'subscriptions.bin');
  assert.equal(fs.readFileSync(filename).includes('secret-access'), false);
  assert.equal(fs.statSync(filename).mode & 0o777, 0o600);
  assert.throws(() => createVault(directory, {...safeStorage, isEncryptionAvailable: () => false}).get(), /keychain/);
});

test('OAuth validates state, uses issued client, exact callback and PKCE; public status excludes secrets', async () => {
  const vault = fixture({accounts: [], active: ''});
  let authorize, verified = false;
  const auth = createSubscriptionAuth({vault,
    verify: async (_jwt, client, nonce) => { assert.equal(client, 'new-issued'); assert.equal(nonce, authorize.searchParams.get('nonce')); verified = true; return {sub: 'person', email: 'a@example.test'}; },
    fetch: async (url, opts) => {
      assert.equal(url, 'https://auth.openai.com/api/accounts/oauth/token');
      assert.equal(opts.body.get('client_id'), 'new-issued');
      assert.equal(opts.body.get('redirect_uri'), authorize.searchParams.get('redirect_uri'));
      assert.equal(crypto.createHash('sha256').update(opts.body.get('code_verifier')).digest('base64url'), authorize.searchParams.get('code_challenge'));
      assert.equal(opts.body.has('client_secret'), false);
      return json({access_token: 'access', refresh_token: 'refresh', id_token: 'jwt', token_type: 'Bearer', expires_in: 3600, scope: PERMISSION});
    },
    openExternal: async url => {
      authorize = new URL(url);
      assert.equal(authorize.searchParams.get('client_id'), 'dynamic_agent_client');
      assert.equal(authorize.searchParams.get('ext_agent_host_id'), vault.get().host);
      const callback = new URL(authorize.searchParams.get('redirect_uri'));
      callback.search = new URLSearchParams({state: 'wrong', code: 'code', client_id: 'new-issued'});
      assert.equal((await fetch(callback)).status, 400);
      callback.searchParams.set('state', authorize.searchParams.get('state'));
      assert.equal((await fetch(callback)).status, 200);
    }});
  await auth.connect();
  assert.equal(verified, true);
  const state = createSubscriptionService({auth}).status();
  assert.equal(state.connected, true);
  assert.equal(JSON.stringify(state).includes('refresh_token'), false);
  assert.equal(JSON.stringify(state).includes('access_token'), false);
});

test('returning account cannot substitute a client or subject, and missing grant never enables inference', async () => {
  for (const mismatch of ['client', 'subject', 'permission']) {
    const vault = fixture(); let nonce;
    const auth = createSubscriptionAuth({vault, verify: async () => ({sub: mismatch === 'subject' ? 'other-person' : 'person', nonce}),
      fetch: async () => json({access_token: 'new', token_type: 'Bearer', expires_in: 3600, scope: ''}),
      openExternal: async url => {
        const params = new URL(url).searchParams; nonce = params.get('nonce');
        assert.equal(params.get('client_id'), 'issued-client'); assert.equal(params.has('agent_name_hint'), false);
        const callback = new URL(params.get('redirect_uri'));
        callback.search = new URLSearchParams({state: params.get('state'), code: 'code', ...(mismatch === 'client' ? {client_id: 'other'} : {})});
        await fetch(callback);
      }});
    if (mismatch === 'permission') { await auth.connect('account-1'); await assert.rejects(auth.token(), /permission/); }
    else { await assert.rejects(auth.connect('account-1'), /mismatch|different/); assert.equal(auth.account().access_token, 'secret-access'); }
  }
});

test('refresh is serialized and rotates credentials; terminal errors clear tokens only', async () => {
  const vault = fixture({accounts: [{...account(), expires_at: 0}]}); let calls = 0;
  const auth = createSubscriptionAuth({vault, fetch: async (_url, options) => {
    calls++; assert.equal(options.body.has('scope'), false);
    await new Promise(resolve => setImmediate(resolve));
    return json({access_token: 'new-access', refresh_token: 'new-refresh', token_type: 'Bearer', expires_in: 3600});
  }});
  assert.deepEqual(await Promise.all([auth.token(), auth.token()]), ['new-access', 'new-access']);
  assert.equal(calls, 1); assert.equal(auth.account().refresh_token, 'new-refresh');
  auth.saveAccount({...auth.account(), expires_at: 0});
  const expired = createSubscriptionAuth({vault, fetch: async () => json({error: 'invalid_grant'}, 400)});
  await assert.rejects(expired.token());
  assert.equal(expired.account().access_token, null); assert.equal(expired.account().client_id, 'issued-client');
});

test('late refresh cannot resurrect a disconnected session; temporary errors retain credentials', async () => {
  const vault = fixture({accounts: [{...account(), expires_at: 0}]}); let resolve;
  const auth = createSubscriptionAuth({vault, fetch: async url => url.includes('oauth/token') ? new Promise(r => { resolve = r; }) : json({}, 503)});
  const pending = auth.token();
  const warning = await auth.disconnect(); assert.match(warning, /not confirmed/);
  resolve(json({access_token: 'late', refresh_token: 'late', token_type: 'Bearer', expires_in: 3600}));
  await assert.rejects(pending, /changed/); assert.equal(auth.account().access_token, null);
  const other = createSubscriptionAuth({vault: fixture({accounts: [{...account(), expires_at: 0}]}), fetch: async () => json({error: 'temporarily_unavailable'}, 503)});
  await assert.rejects(other.token()); assert.equal(other.account().refresh_token, 'secret-refresh');
});

test('subscription requests use only authorized catalog, no paid key or unsupported fields', async () => {
  const {service} = setup(async (url, options) => {
    assert.equal(options.headers.Authorization, 'Bearer secret-access');
    if (url.endsWith('/models')) return catalog();
    assert.equal(url, 'https://api.openai.com/v1/responses');
    const body = JSON.parse(options.body);
    assert.deepEqual(Object.keys(body).sort(), ['input', 'model', 'store', 'stream']);
    assert.equal(body.input[0].role, 'developer'); assert.equal(body.model, 'model-one');
    return completed();
  });
  const events = [];
  await service.stream({query: 'Question', messages: [{role: 'system', content: 'Context'}]}, e => events.push(e), new AbortController().signal);
  assert.deepEqual(events.map(e => e.type), ['meta', 'chunk', 'done']);
  assert.deepEqual((await service.models()).map(m => m.slug), ['model-one']);
});

test('429 pauses whole plan, honors retry-after, switches only to opted-in installed local fallback', async () => {
  let cloudCalls = 0;
  const {service, auth} = setup(async (url, options) => {
    if (url.endsWith('/models')) return catalog();
    if (url.endsWith('/responses')) { cloudCalls++; return json({error: {code: 'subscription_sharing_usage_limit_exceeded'}}, 429, {'retry-after': '120'}); }
    assert.equal(options.headers?.Authorization, undefined);
    if (url.endsWith('/tags')) return json({models: [{name: 'local:small'}, {name: 'bad:cloud'}]});
    if (url.endsWith('/show')) return json({capabilities: ['completion']});
    assert.equal(url, 'http://127.0.0.1:11434/api/chat');
    return new Response(JSON.stringify({message: {content: 'Local answer'}, done: true}) + '\n');
  }, {fallback: 'local:small'});
  const events = [];
  for (let i = 0; i < 2; i++) await service.stream({query: 'Question'}, e => events.push(e), new AbortController().signal);
  assert.equal(cloudCalls, 1); assert.equal(auth.account().paused, true);
  assert.ok(events.some(e => e.type === 'notice' && e.message.includes('switched')));
  await assert.rejects(service.settings({retry: true}), /wait/);
});

test('partial limit restarts answer explicitly; no fallback leaves partial answer incomplete', async () => {
  for (const fallback of ['', 'local:small']) {
    const {service} = setup(async url => {
      if (url.endsWith('/models')) return catalog();
      if (url.endsWith('/responses')) return sse([{type: 'response.output_text.delta', delta: 'Partial'}, {type: 'response.failed', response: {error: {code: 'subscription_sharing_usage_limit_exceeded'}}}]);
      if (url.endsWith('/tags')) return json({models: [{name: 'local:small'}]});
      if (url.endsWith('/show')) return json({capabilities: ['completion']});
      return new Response(JSON.stringify({message: {content: 'Replacement'}, done: true}));
    }, {fallback});
    const events = [], run = service.stream({query: 'Question'}, e => events.push(e), new AbortController().signal);
    if (fallback) { await run; assert.ok(events.findIndex(e => e.type === 'reset') < events.findIndex(e => e.content === 'Replacement')); }
    else { await assert.rejects(run, /429/); assert.equal(events.some(e => e.type === 'done'), false); }
  }
});

test('cloud local-model aliases and text-only screenshot fallback fail closed', async () => {
  for (const info of [{remote_host: 'https://cloud.example'}, {capabilities: ['completion']}]) {
    const {service} = setup(async url => {
      if (url.endsWith('/models')) return catalog();
      if (url.endsWith('/responses')) return json({}, 429);
      if (url.endsWith('/tags')) return json({models: [{name: 'local:small'}]});
      if (url.endsWith('/show')) return json(info);
      assert.fail('must not send input to local chat');
    }, {fallback: 'local:small'});
    await assert.rejects(service.stream({query: 'Question', image_b64: 'aGVsbG8='}, () => {}, new AbortController().signal), /locally|screenshots/);
  }
});

test('SSE framing supports split Unicode, CRLF and final frames', async () => {
  const bytes = new TextEncoder().encode('data: {"text":"héllo"}\r\n\r\ndata: {"done":true}');
  const response = new Response(new ReadableStream({start(c) { for (const b of bytes) c.enqueue(Uint8Array.of(b)); c.close(); }}));
  const result = []; for await (const value of frames(response, true)) result.push(value);
  assert.deepEqual(result, [{text: 'héllo'}, {done: true}]);
});

test('subscription IPC rejects remote pages and child frames before reading credentials', async () => {
  const handlers = new Map();
  registerSubscriptionIPC({ipcMain: {handle: (name, fn) => handlers.set(name, fn)}, directory: '/unused', safeStorage: {}, shell: {}, rendererDirectory: '/renderer'});
  const mainFrame = {url: 'https://attacker.test/index.html'}, sender = {mainFrame};
  for (const name of ['subscriptions:status', 'subscriptions:connect', 'subscriptions:start']) {
    assert.match((await handlers.get(name)({sender, senderFrame: mainFrame})).error, /Unauthorized|Invalid/);
    mainFrame.url = 'file:///renderer/index.html';
    assert.match((await handlers.get(name)({sender, senderFrame: {url: mainFrame.url}})).error, /Unauthorized|Invalid/);
    mainFrame.url = 'https://attacker.test/index.html';
  }
});

test('malformed token responses cannot grant indefinite access', () => {
  assert.throws(() => tokenSet({access_token: 'a', token_type: 'Bearer', expires_in: -1}), /Incomplete/);
  assert.throws(() => tokenSet({access_token: 'a', token_type: 'other', expires_in: 3600}), /Incomplete/);
});

test('real signed ID tokens enforce signature, issuer, audience, expiry and nonce', async () => {
  const {generateKeyPair, SignJWT} = await import('jose');
  const {verifyIdentity} = require('../lib/subscription-auth');
  const key = await generateKeyPair('RS256'), other = await generateKeyPair('RS256');
  const signed = async (changes = {}, signingKey = key.privateKey) => new SignJWT({sub: 'person', nonce: 'nonce', ...changes})
    .setProtectedHeader({alg: 'RS256'}).setIssuer(changes.iss || 'https://auth.openai.com').setAudience(changes.aud || 'issued')
    .setIssuedAt().setExpirationTime(changes.exp || '5m').sign(signingKey);
  assert.equal((await verifyIdentity(await signed(), 'issued', 'nonce', key.publicKey)).sub, 'person');
  for (const changes of [{iss: 'https://evil.test'}, {aud: 'wrong'}, {nonce: 'wrong'}, {exp: 1}, {sub: ''}]) {
    await assert.rejects(verifyIdentity(await signed(changes), 'issued', 'nonce', key.publicKey));
  }
  await assert.rejects(verifyIdentity(await signed({}, other.privateKey), 'issued', 'nonce', key.publicKey));
});

test('cancellation stops reads and never falls back', async () => {
  const controller = new AbortController();
  const {service} = setup(async url => {
    if (url.endsWith('/models')) return catalog();
    assert.ok(url.endsWith('/responses'));
    controller.abort(); return completed();
  }, {fallback: 'local:small'});
  await assert.rejects(service.stream({query: 'Question'}, () => {}, controller.signal), {name: 'AbortError'});
});
