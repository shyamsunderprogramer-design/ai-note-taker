const {isAppFrame} = require('./auth-session');
const {createVault, createSubscriptionAuth, PERMISSION, RESOURCE} = require('./subscription-auth');
const USAGE = 'https://chatgpt.com/settings/usage';
const LOCAL = 'http://127.0.0.1:11434';
const localName = name => typeof name === 'string' && name.length < 256 && !/cloud|https?:|\//i.test(name);

// Incremental framing handles split UTF-8, CRLF, multi-line SSE data, and final frames.
async function* frames(response, sse) {
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = '';
  try {
    for (;;) {
      const {value, done} = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
      if (buffer.length > 8 * 1024 * 1024) throw Error('Model response exceeded the stream buffer limit.');
      const parts = buffer.split(sse ? /\r?\n\r?\n/ : /\r?\n/);
      buffer = parts.pop();
      if (done && buffer.trim()) parts.push(buffer);
      for (const part of parts) {
        const data = sse ? part.split(/\r?\n/).filter(l => l.startsWith('data:')).map(l => l.slice(5).trimStart()).join('\n') : part;
        if (data && data !== '[DONE]') yield JSON.parse(data);
      }
      if (done) break;
    }
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
function limitError(status, data = {}, headers = new Headers()) {
  const error = data.error || data.response?.error || {};
  const code = typeof error.code === 'string' ? error.code : '';
  const limited = status === 429 || code === 'subscription_sharing_usage_limit_exceeded' || code === 'rate_limit_exceeded';
  const seconds = headers.get('retry-after');
  const until = seconds == null ? 0 : /^\d+$/.test(seconds) ? Date.now() + Number(seconds) * 1000 : Date.parse(seconds);
  const message = limited ? 'ChatGPT usage limit reached (429). Manage usage in ChatGPT settings.' :
    status === 401 ? 'ChatGPT did not accept this session. Reconnect in Providers.' :
    status === 403 ? 'ChatGPT plan usage is unavailable for this account, workspace, or region.' :
    status === 503 ? 'ChatGPT plan usage is temporarily unavailable. Try again later.' :
    code === 'subscription_sharing_unsupported_capability' ? 'This ChatGPT model does not support the requested input.' : 'ChatGPT could not complete the answer. Try again or choose another model.';
  return Object.assign(Error(message), {limited, status, code, param: typeof error.param === 'string' ? error.param : '',
    requestId: headers.get('x-request-id') || '', retryAt: Number.isFinite(until) ? until : 0});
}
function validateRequest(request) {
  if (!request || typeof request.query !== 'string' || !request.query.trim() || request.query.length > 200000) throw Error('Invalid subscription question.');
  if (request.image_b64 && (typeof request.image_b64 !== 'string' || request.image_b64.length > 12000000 || !/^[A-Za-z0-9+/=\r\n]+$/.test(request.image_b64))) throw Error('Invalid screenshot.');
  if (request.messages != null && (!Array.isArray(request.messages) || request.messages.length > 300)) throw Error('Too much conversation history.');
  const messages = (request.messages || []).map(m => {
    const content = m.content ?? m.text;
    if (!['user', 'assistant', 'system', 'developer'].includes(m.role) || typeof content !== 'string') throw Error('Invalid conversation context.');
    return {role: m.role === 'system' ? 'developer' : m.role, content};
  });
  if (JSON.stringify(messages).length > 800000) throw Error('Conversation context is too large. Start a new conversation.');
  return {query: request.query, messages, image: request.image_b64 || null};
}
function createSubscriptionService({auth, fetch = globalThis.fetch}) {
  const catalogs = new Map();
  const request = (url, options = {}) => fetch(url, {...options, redirect: 'error', signal: options.signal || AbortSignal.timeout(12000)});
  async function models(id = auth.vault.get().active) {
    const bearer = await auth.token(id);
    const response = await request(`${RESOURCE}/models`, {headers: {Authorization: `Bearer ${bearer}`}});
    if (!response.ok) throw limitError(response.status, await response.json().catch(() => ({})), response.headers);
    const data = await response.json();
    if (!Array.isArray(data.models)) throw Error('ChatGPT returned an unsupported model catalog.');
    const result = data.models.filter(m => m.visibility === 'list' && typeof m.slug === 'string' && typeof m.display_name === 'string')
      .map(m => ({slug: m.slug, name: m.display_name}));
    catalogs.set(id, result);
    return result;
  }
  async function locals() {
    try {
      const response = await request(`${LOCAL}/api/tags`);
      if (!response.ok) return [];
      return ((await response.json()).models || []).filter(m => localName(m.name) && !m.remote_host && !m.remote_model).map(m => m.name);
    } catch { return []; }
  }
  function status() {
    const data = auth.vault.get(), a = auth.account();
    return {accounts: data.accounts.map((a, i) => ({id: a.id, label: `${a.email} · Account ${i + 1}`, connected: !!a.access_token})),
      active: data.active, connected: !!a?.access_token, enabled: !!a?.access_token && !!a.scopes?.includes(PERMISSION),
      connecting: auth.connecting, paused: !!a?.paused, retryAt: a?.retryAt || 0, model: a?.model || '',
      models: catalogs.get(data.active) || [], fallback: data.fallback || '', welcomeSeen: !!data.welcomeSeen};
  }
  async function settings(change) {
    const data = auth.vault.get();
    if (typeof change.active === 'string') {
      if (!auth.account(change.active)) throw Error('Unknown ChatGPT account.');
      auth.vault.set({...data, active: change.active});
      return status();
    }
    if (typeof change.model === 'string') {
      const a = auth.account();
      if (!(catalogs.get(data.active) || []).some(m => m.slug === change.model)) throw Error('Select a model from your account catalog.');
      auth.saveAccount({...a, model: change.model});
    }
    if (typeof change.fallback === 'string') {
      if (change.fallback && !(await locals()).includes(change.fallback)) throw Error('Select an installed local model. Start Ollama if it is unavailable.');
      auth.vault.set({...auth.vault.get(), fallback: change.fallback});
    }
    if (change.welcomeSeen === true) auth.vault.set({...auth.vault.get(), welcomeSeen: true});
    if (change.retry === true && auth.account()) {
      const a = auth.account();
      if (a.retryAt > Date.now()) throw Error('ChatGPT asked ANT to wait before retrying.');
      auth.saveAccount({...a, paused: false, retryAt: 0});
    }
    return status();
  }
  async function stream(raw, emit, signal, {allowLocalFallback = true} = {}) {
    const input = validateRequest(raw), id = auth.vault.get().active;
    const a = auth.account(id), fallback = auth.vault.get().fallback;
    if (!a?.access_token || !a.scopes?.includes(PERMISSION)) throw Error('Connect and enable your ChatGPT plan in Settings → Providers.');
    let wrote = false, recover = false;
    try {
      if (a.paused && (!a.retryAt || a.retryAt > Date.now())) throw Object.assign(Error('ChatGPT usage is paused. Manage usage or retry from Subscriptions.'), {limited: true});
      if (a.paused) auth.saveAccount({...a, paused: false, retryAt: 0});
      const catalog = catalogs.get(id) || await models(id);
      signal.throwIfAborted();
      const model = catalog.find(m => m.slug === a.model) || catalog[0];
      if (!model) throw Error('No models are available for this ChatGPT account.');
      const bearer = await auth.token(id);
      const content = [{type: 'input_text', text: input.query}];
      if (input.image) content.push({type: 'input_image', image_url: `data:image/png;base64,${input.image}`});
      const response = await request(`${RESOURCE}/responses`, {method: 'POST', signal,
        headers: {Authorization: `Bearer ${bearer}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({model: model.slug, store: false, stream: true, input: [...input.messages, {role: 'user', content}]})});
      if (!response.ok) throw limitError(response.status, await response.json().catch(() => ({})), response.headers);
      emit({type: 'meta', model: model.slug, display: `${model.name} · ChatGPT plan`});
      for await (const event of frames(response, true)) {
        signal.throwIfAborted();
        if (event.type === 'response.output_text.delta') { wrote = true; emit({type: 'chunk', content: event.delta}); }
        if (event.type === 'response.completed') { emit({type: 'done'}); return; }
        if (['response.failed', 'response.incomplete', 'error'].includes(event.type)) throw limitError(200, event, response.headers);
      }
      throw Error('ChatGPT connection ended before the answer completed.');
    } catch (error) {
      if (signal.aborted || !error.limited) throw error;
      const current = auth.account(id);
      if (current) auth.saveAccount({...current, paused: true, retryAt: error.retryAt || current.retryAt || 0});
      emit({type: 'notice', message: error.message, status: error.status || 429, code: error.code || '', requestId: error.requestId || ''});
      if (!allowLocalFallback || !fallback) throw error;
      recover = true;
    }
    if (recover) {
      signal.throwIfAborted();
      if (!(await locals()).includes(fallback)) throw Error('ChatGPT is paused and your selected local fallback is unavailable. Start Ollama or manage ChatGPT usage.');
      // Check capabilities and remote routing again immediately before sending private context.
      const details = await request(`${LOCAL}/api/show`, {method: 'POST', signal, headers: {'Content-Type': 'application/json'}, body: JSON.stringify({model: fallback})});
      if (!details.ok) throw Error('Unable to verify the selected local fallback.');
      const info = await details.json();
      if (info.remote_host || info.remote_model) throw Error('Fallback must run locally. Cloud Ollama models are not enabled for subscription recovery.');
      if (input.image && !info.capabilities?.includes('vision')) throw Error('Your local fallback cannot read screenshots. Select a vision model or send text only.');
      const messages = input.messages.map(m => ({...m, role: m.role === 'developer' ? 'system' : m.role}));
      messages.push({role: 'user', content: input.query, ...(input.image ? {images: [input.image]} : {})});
      const response = await request(`${LOCAL}/api/chat`, {method: 'POST', signal, headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({model: fallback, stream: true, messages})});
      if (!response.ok) throw Error(`Local fallback failed (${response.status}). ChatGPT remains paused.`);
      emit({type: 'notice', message: `ChatGPT limit reached → switched to ${fallback} on this device.${wrote ? ' Restarting the incomplete answer.' : ''}`});
      if (wrote) emit({type: 'reset'});
      emit({type: 'meta', model: fallback, display: `${fallback} · Local fallback`});
      for await (const event of frames(response, false)) {
        signal.throwIfAborted();
        if (event.error) throw Error('Local fallback could not complete the answer.');
        if (event.message?.content) emit({type: 'chunk', content: event.message.content});
        if (event.done) { emit({type: 'done'}); return; }
      }
      throw Error('Local fallback connection ended before the answer completed.');
    }
  }
  return {status, settings, models, locals, stream};
}
function registerSubscriptionIPC({ipcMain, directory, safeStorage, shell, rendererDirectory, app}) {
  const ownsSession = app?.requestSingleInstanceLock ? app.requestSingleInstanceLock() : true;
  const auth = createSubscriptionAuth({vault: createVault(directory, safeStorage), openExternal: url => shell.openExternal(url)});
  const chatgpt = createSubscriptionService({auth});
  const {createOllamaAccount} = require('./ollama-account');
  const {createConnectedModels} = require('./connected-models');
  const ollama = createOllamaAccount({frames, openExternal: url => shell.openExternal(url)});
  const service = createConnectedModels({auth, chatgpt, ollama, validateRequest});
  const streams = new Map();
  const trusted = event => ownsSession && isAppFrame(event, rendererDirectory) && new URL(event.senderFrame.url).pathname.endsWith('/index.html');
  const stop = () => { for (const c of streams.values()) c.abort(); };
  const operations = {
    status: () => service.status(),
    refresh: () => service.refresh(),
    connectOllama: async () => { stop(); return service.connectOllama(); },
    disconnectOllama: () => { stop(); return service.disconnectOllama(); },
    cancelOllama: () => service.cancelOllama(),
    addOllamaModel: name => service.addOllamaModel(name),
    ollamaUsage: () => shell.openExternal('https://ollama.com/settings/usage'),
    ollamaDownload: () => shell.openExternal('https://ollama.com/download'),
    connect: async id => { stop(); await auth.connect(id); return service.status(); },
    cancelLogin: () => { auth.cancel(); return service.status(); },
    disconnect: async () => { stop(); const warning = await auth.disconnect(); return {...service.status(), warning}; },
    settings: async change => {
      if (['active', 'model', 'fallback', 'retry', 'primary', 'crossFallback', 'ollamaModel', 'retryOllama'].some(key => Object.hasOwn(change || {}, key))) stop();
      return service.settings(change || {});
    },
    usage: () => shell.openExternal(USAGE),
  };
  for (const [name, operation] of Object.entries(operations)) ipcMain.handle(`subscriptions:${name}`, async (event, value) => {
    if (!ownsSession) return {error: 'Subscriptions are open in another ANT instance. Quit the other instance and restart this app.'};
    if (!trusted(event)) return {error: 'Unauthorized subscription request.'};
    try { return {value: await operation(value)}; } catch (error) { return {error: error.message}; }
  });
  ipcMain.handle('subscriptions:start', (event, id, input) => {
    if (!trusted(event) || typeof id !== 'string' || !/^[a-f0-9-]{36}$/.test(id)) return {error: 'Invalid subscription request.'};
    const key = `${event.sender.id}:${id}`;
    if (streams.size || streams.has(key)) return {error: 'A subscription answer is already in progress.'};
    const controller = new AbortController(), sender = event.sender, frame = event.senderFrame;
    streams.set(key, controller);
    const abort = () => controller.abort();
    sender.once('destroyed', abort); sender.once('did-start-navigation', abort);
    const timer = setTimeout(abort, 65000);
    const emit = data => { if (!controller.signal.aborted && !sender.isDestroyed() && sender.mainFrame === frame) frame.send('subscriptions:event', id, data); };
    service.stream(input, emit, controller.signal).catch(error => emit({type: 'error', message: error.message})).finally(() => {
      clearTimeout(timer); streams.delete(key); sender.removeListener('destroyed', abort); sender.removeListener('did-start-navigation', abort);
      if (!sender.isDestroyed() && sender.mainFrame === frame) frame.send('subscriptions:event', id, {type: 'end'});
    });
    return {value: true};
  });
  ipcMain.handle('subscriptions:cancel', (event, id) => {
    if (trusted(event)) streams.get(`${event.sender.id}:${id}`)?.abort();
  });
  app?.on('before-quit', () => { stop(); auth.cancel(); });
}
module.exports = {createSubscriptionService, registerSubscriptionIPC, frames, limitError, validateRequest};
