// ChatGPT public-client OAuth. Credentials never cross the preload bridge.
const crypto = require('node:crypto');
const http = require('node:http');
const path = require('node:path');
const {readPrivateFile, writePrivateFile} = require('./auth-session');
const AUTH = 'https://auth.openai.com';
const RESOURCE = 'https://api.openai.com/v1';
const PERMISSION = 'chatgpt.tokens.use.direct';
const SCOPES = `openid profile email offline_access resource.invoke ${PERMISSION}`;
const TERMINAL = new Set(['invalid_grant', 'invalid_refresh_token', 'token_expired', 'refresh_token_expired', 'refresh_token_invalidated', 'refresh_token_reused']);
let jwks;
async function verifyIdentity(token, clientId, nonce, verificationKey) {
  const {jwtVerify, createRemoteJWKSet} = await import('jose');
  if (!verificationKey) jwks ||= createRemoteJWKSet(new URL(`${AUTH}/.well-known/jwks.json`));
  const {payload} = await jwtVerify(token, verificationKey || jwks, {issuer: AUTH, audience: clientId,
    algorithms: ['RS256', 'ES256'], requiredClaims: ['sub', 'exp', 'iat'], clockTolerance: 5});
  if (typeof payload.sub !== 'string' || !payload.sub || payload.nonce !== nonce) throw Error('ChatGPT identity validation failed. Start sign-in again.');
  return payload;
}
function createVault(directory, safeStorage) {
  const filename = path.join(directory, 'subscriptions.bin');
  let value;
  const secure = () => {
    if (!safeStorage.isEncryptionAvailable() || (process.platform === 'linux' && safeStorage.getSelectedStorageBackend() === 'basic_text')) {
      throw Error('Unlock your system keychain to connect a subscription.');
    }
  };
  return {
    get() {
      if (value) return value;
      secure();
      try { value = JSON.parse(safeStorage.decryptString(readPrivateFile(filename))); }
      catch (error) {
        if (error.code !== 'ENOENT') throw Error('Unable to read subscription storage. Unlock your system keychain and try again.');
        this.set({host: `urn:uuid:${crypto.randomUUID()}`, accounts: [], active: '', fallback: '', welcomeSeen: false});
      }
      if (!value.host || !Array.isArray(value.accounts)) throw Error('Invalid subscription storage.');
      return value;
    },
    set(next) {
      secure();
      const encrypted = safeStorage.encryptString(JSON.stringify(next));
      if (encrypted.length > 128 * 1024) throw Error('Subscription storage is full. Too many account registrations.');
      writePrivateFile(filename, encrypted);
      value = next;
    },
  };
}
function tokenSet(data, previous = {}) {
  if (typeof data.access_token !== 'string' || !data.access_token || data.access_token.length > 16384 ||
      !Number.isFinite(data.expires_in) || data.expires_in <= 0 || String(data.token_type).toLowerCase() !== 'bearer') {
    throw Error('Incomplete ChatGPT token response. Please sign in again.');
  }
  return {access_token: data.access_token, refresh_token: data.refresh_token || previous.refresh_token,
    id_token: data.id_token || previous.id_token, expires_at: Date.now() + data.expires_in * 1000,
    scopes: typeof data.scope === 'string' ? data.scope.split(/\s+/) : previous.scopes || []};
}
function createSubscriptionAuth({vault, openExternal, fetch = globalThis.fetch, verify = verifyIdentity}) {
  let attempt = null;
  let generation = 0;
  const refreshes = new Map();
  const account = (id = vault.get().active) => vault.get().accounts.find(a => a.id === id);
  const saveAccount = next => {
    const data = vault.get();
    vault.set({...data, accounts: data.accounts.map(a => a.id === next.id ? next : a)});
  };
  async function exchange(form, signal) {
    const response = await fetch(`${AUTH}/api/accounts/oauth/token`, {method: 'POST',
      body: new URLSearchParams({...form, resource: RESOURCE}), redirect: 'error',
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000)});
    const data = await response.json();
    if (!response.ok) {
      const code = typeof data.error === 'string' ? data.error : data.error?.code;
      throw Object.assign(Error(`ChatGPT sign-in could not be renewed (${response.status}). Please try signing in again.`), {code});
    }
    return data;
  }
  function cancel() { generation++; attempt?.cancel(); }
  async function connect(id = '') {
    if (attempt) throw Error('A ChatGPT sign-in is already in progress.');
    const saved = id ? account(id) : null;
    if (id && !saved) throw Error('Unknown saved account.');
    const host = vault.get().host; // Persist the installation identity before opening a browser.
    const epoch = generation;
    const random = () => crypto.randomBytes(32).toString('base64url');
    const state = random(), nonce = random(), verifier = random();
    const controller = new AbortController();
    let timer, redirect, claimed = false;
    let resolveResult, rejectResult;
    const result = new Promise((resolve, reject) => { resolveResult = resolve; rejectResult = reject; });
    // A rejection may happen before the browser-opening promise resolves.
    result.catch(() => {});
    const server = http.createServer(async (req, res) => {
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      res.setHeader('Cache-Control', 'no-store');
      res.setHeader('Referrer-Policy', 'no-referrer');
      const url = new URL(req.url, redirect);
      if (req.method !== 'GET' || url.pathname !== '/auth/callback' || req.headers.host !== new URL(redirect).host) {
        res.writeHead(404).end('Not found'); return;
      }
      if (url.searchParams.getAll('state').length !== 1 || url.searchParams.get('state') !== state || claimed) {
        res.writeHead(400).end('Invalid or expired sign-in attempt. Return to ANT.'); return;
      }
      claimed = true;
      try {
        if (url.searchParams.has('error')) throw Error('ChatGPT sign-in was declined. You can try again in Settings → Subscriptions.');
        const clientId = url.searchParams.get('client_id') || saved?.client_id;
        const code = url.searchParams.get('code');
        if (!clientId || clientId === 'dynamic_agent_client' || clientId.length > 256 || !code ||
            (saved && clientId !== saved.client_id)) throw Error('Incomplete or mismatched ChatGPT registration.');
        const data = await exchange({grant_type: 'authorization_code', client_id: clientId, code,
          code_verifier: verifier, redirect_uri: redirect}, controller.signal);
        const identity = await verify(data.id_token, clientId, nonce);
        if (saved && identity.sub !== saved.subject) throw Error('That is a different account. Choose Add account to connect it.');
        if (generation !== epoch || controller.signal.aborted) throw Error('Sign-in cancelled.');
        const current = vault.get();
        const duplicate = current.accounts.find(a => a.client_id === clientId && a.subject === identity.sub);
        const next = {...(duplicate || saved), id: duplicate?.id || saved?.id || crypto.randomUUID(), client_id: clientId,
          subject: identity.sub, email: typeof identity.email === 'string' ? identity.email : 'ChatGPT account',
          ...tokenSet(data), paused: false};
        vault.set({...current, active: next.id, accounts: [...current.accounts.filter(a => a.id !== next.id), next]});
        res.end('ChatGPT connected. You can close this tab and return to ANT.');
        resolveResult();
      } catch (error) {
        res.writeHead(400).end('Sign-in did not complete. Return to ANT for details.');
        rejectResult(error);
      }
    });
    attempt = {cancel() { controller.abort(); rejectResult(Error('Sign-in cancelled.')); server.close(); }};
    try {
      await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
      if (generation !== epoch || controller.signal.aborted) throw Error('Sign-in cancelled.');
      redirect = `http://127.0.0.1:${server.address().port}/auth/callback`;
      const params = new URLSearchParams({client_id: saved?.client_id || 'dynamic_agent_client', ext_agent_host_id: host,
        response_type: 'code', redirect_uri: redirect, scope: SCOPES, resource: RESOURCE, state, nonce,
        code_challenge_method: 'S256', code_challenge: crypto.createHash('sha256').update(verifier).digest('base64url')});
      if (saved) {
        if (saved.id_token) params.set('id_token_hint', saved.id_token);
        if (saved.email) params.set('login_hint', saved.email);
        if (!saved.scopes?.includes(PERMISSION)) params.set('prompt', 'consent');
      } else params.set('agent_name_hint', 'ANT (AI Note Taker)');
      timer = setTimeout(() => attempt?.cancel(), 180000);
      await openExternal(`${AUTH}/api/accounts/authorize?${params}`);
      await result;
    } finally {
      clearTimeout(timer); controller.abort(); server.close(); server.closeAllConnections(); attempt = null;
    }
  }
  async function token(id = vault.get().active) {
    let a = account(id);
    if (!a?.access_token) throw Error('Connect your ChatGPT account in Settings → Subscriptions.');
    if (!a.scopes?.includes(PERMISSION)) throw Error('ChatGPT plan usage needs permission. Continue with ChatGPT in Subscriptions.');
    if (a.expires_at > Date.now() + 60000) return a.access_token;
    if (refreshes.has(id)) return refreshes.get(id);
    if (!a.refresh_token) throw Error('Sign in with ChatGPT again to renew your connection.');
    const old = a.refresh_token;
    const pending = (async () => {
      try {
        const data = await exchange({grant_type: 'refresh_token', client_id: a.client_id, refresh_token: old});
        if (account(id)?.refresh_token !== old) throw Error('ChatGPT connection changed. Please try again.');
        a = {...account(id), ...tokenSet(data, a)};
        saveAccount(a);
        if (!a.scopes.includes(PERMISSION)) throw Error('ChatGPT plan permission is no longer enabled. Please sign in again.');
        return a.access_token;
      } catch (error) {
        if (TERMINAL.has(error.code) && account(id)?.refresh_token === old) {
          saveAccount({...account(id), access_token: null, refresh_token: null, id_token: null, scopes: []});
        }
        throw error;
      }
    })();
    refreshes.set(id, pending);
    try { return await pending; } finally { refreshes.delete(id); }
  }
  async function disconnect(id = vault.get().active) {
    cancel();
    const a = account(id);
    if (!a) return '';
    // Invalidate in-flight refreshes immediately; retain the secret only for revocation.
    saveAccount({...a, access_token: null, refresh_token: null, id_token: null, scopes: [], paused: false});
    if (!a.refresh_token) return '';
    try {
      const discovery = await fetch(`${AUTH}/.well-known/openid-configuration`, {signal: AbortSignal.timeout(10000), redirect: 'error'});
      if (!discovery.ok) throw Error();
      const url = new URL((await discovery.json()).revocation_endpoint);
      if (url.origin !== AUTH || url.username || url.password) throw Error();
      const response = await fetch(url.href, {method: 'POST', redirect: 'error', signal: AbortSignal.timeout(10000),
        body: new URLSearchParams({token: a.refresh_token, token_type_hint: 'refresh_token', client_id: a.client_id})});
      if (response.status !== 200) throw Error();
      return '';
    } catch { return 'Signed out locally. Remote revocation was not confirmed; disconnect ANT in ChatGPT settings.'; }
  }
  return {connect, cancel, token, disconnect, account, saveAccount, vault, get connecting() { return !!attempt; }};
}
module.exports = {createVault, createSubscriptionAuth, verifyIdentity, tokenSet, PERMISSION, RESOURCE};
