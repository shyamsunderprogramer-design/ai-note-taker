// Uses the same local account flow as `ollama signin`. Ollama owns its credentials.
const LOCAL = 'http://127.0.0.1:11434';
const cloudName = name => typeof name === 'string' && /^[a-z0-9][a-z0-9._-]*(?::[a-z0-9._-]+)?$/i.test(name) && /(?::|-|^)cloud$/i.test(name);
function officialRemote(host) {
  if (!host) return true;
  try { const url = new URL(host.includes('://') ? host : `https://${host}`); return url.origin === 'https://ollama.com' && !url.username && !url.password; }
  catch { return false; }
}
function ollamaError(status, body, headers = new Headers()) {
  const message = typeof body?.error === 'string' ? body.error : '';
  const limited = status === 429 || /\b429\b|rate.?limit|usage limit|quota exceeded/i.test(message);
  const retry = headers.get('retry-after');
  const retryAt = retry == null ? 0 : /^\d+$/.test(retry) ? Date.now() + Number(retry) * 1000 : Date.parse(retry);
  return Object.assign(Error(limited ? 'Ollama Cloud usage limit reached (429).' : status === 401 ? 'Sign in to Ollama again in Providers.' : `Ollama could not complete the request${status >= 400 ? ` (${status})` : ''}.`),
    {limited, status, retryAt: Number.isFinite(retryAt) ? retryAt : 0, provider: 'ollama-cloud'});
}
function createOllamaAccount({fetch = globalThis.fetch, openExternal, frames}) {
  let pending = false;
  const request = (pathname, options = {}) => fetch(`${LOCAL}${pathname}`, {...options, redirect: 'error',
    signal: options.signal ? AbortSignal.any([options.signal, AbortSignal.timeout(65000)]) : AbortSignal.timeout(5000)});
  async function identity() {
    try {
      const response = await request('/api/me', {method: 'POST'});
      const body = await response.json();
      if (response.status === 401) return {running: true, connected: false, signin: body.signin_url};
      if (!response.ok) return {running: true, connected: false, warning: 'Ollama could not check this account. Update Ollama or try again.'};
      return {running: true, connected: typeof body.name === 'string' && !!body.name, name: typeof body.name === 'string' ? body.name : ''};
    } catch { return {running: false, connected: false, warning: 'Start the Ollama app, then refresh.'}; }
  }
  async function connect() {
    const state = await identity();
    if (!state.running || state.warning) throw Error(state.warning);
    if (state.connected) return state;
    let url;
    try { url = new URL(state.signin); } catch { throw Error('Update Ollama, then sign in from its app or run ollama signin.'); }
    if (url.origin !== 'https://ollama.com' || url.username || url.password) throw Error('Ollama returned an invalid sign-in address.');
    await openExternal(url.href); pending = true;
    return {running: true, connected: false, pending: true};
  }
  async function models() {
    const response = await request('/api/tags');
    if (!response.ok) throw Error('Start Ollama to load its models.');
    const data = await response.json();
    return (data.models || []).filter(m => cloudName(m.name) && officialRemote(m.remote_host)).map(m => ({slug: m.name, name: m.name}));
  }
  async function addModel(name) {
    if (!cloudName(name)) throw Error('Enter an Ollama cloud model name ending in :cloud or -cloud.');
    const response = await request('/api/pull', {method: 'POST', signal: AbortSignal.timeout(30000),
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify({model: name, stream: false})});
    if (!response.ok) throw ollamaError(response.status, await response.json().catch(() => ({})), response.headers);
    const result = await response.json();
    if (result.error) throw ollamaError(200, result);
    return models();
  }
  async function stream(input, model, emit, signal, {local = false} = {}) {
    const listing = await request('/api/tags', {signal});
    if (!listing.ok) throw Error('Start Ollama to use this model.');
    const entry = ((await listing.json()).models || []).find(m => m.name === model);
    if (!entry) throw Error('The selected Ollama model is unavailable. Refresh models in Providers.');
    if (!local && (!cloudName(model) || !officialRemote(entry.remote_host))) throw Error('Select an official Ollama Cloud model.');
    if (local && (cloudName(model) || entry.remote_host || entry.remote_model)) throw Error('The selected fallback is not a local model.');
    const response = await request('/api/show', {method: 'POST', signal, headers: {'Content-Type': 'application/json'}, body: JSON.stringify({model})});
    if (!response.ok) throw ollamaError(response.status, await response.json().catch(() => ({})), response.headers);
    const info = await response.json();
    if ((local && (info.remote_host || info.remote_model)) || (!local && !officialRemote(info.remote_host))) throw Error('Ollama model routing changed. Refresh and select a model again.');
    if (input.image && !info.capabilities?.includes('vision')) throw Error('The selected Ollama model cannot read screenshots. Select a vision model or send text only.');
    const messages = input.messages.map(m => ({...m, role: m.role === 'developer' ? 'system' : m.role}));
    messages.push({role: 'user', content: input.query, ...(input.image ? {images: [input.image]} : {})});
    const chat = await request('/api/chat', {method: 'POST', signal, headers: {'Content-Type': 'application/json'}, body: JSON.stringify({model, stream: true, messages})});
    if (!chat.ok) throw ollamaError(chat.status, await chat.json().catch(() => ({})), chat.headers);
    emit({type: 'meta', model, display: `${model} · ${local ? 'Local fallback' : 'Ollama account'}`});
    for await (const event of frames(chat, false)) {
      signal.throwIfAborted();
      if (event.error) throw ollamaError(200, event, chat.headers);
      if (event.message?.content) emit({type: 'chunk', content: event.message.content});
      if (event.done) { emit({type: 'done'}); return; }
    }
    throw Error('Ollama connection ended before the answer completed.');
  }
  return {identity, connect, models, addModel, stream, get pending() { return pending; }, cancel() { pending = false; }};
}
module.exports = {createOllamaAccount, cloudName, ollamaError, officialRemote};
