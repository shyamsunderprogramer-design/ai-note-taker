// Cross-provider routing is explicit: one chosen primary, one other connected
// account if opted in, then the chosen local model. Never routes to API-key billing.
function createConnectedModels({auth, chatgpt, ollama, validateRequest}) {
  let cloudState = {running: false, connected: false}, cloudModels = [];
  function status() {
    const data = auth.vault.get();
    return {...chatgpt.status(), primary: data.primary || 'chatgpt', crossFallback: !!data.crossFallback, ollamaLoginPending: ollama.pending,
      ollama: {...cloudState, enabled: !!data.ollamaEnabled && cloudState.connected && cloudState.name === data.ollamaAccount,
        model: data.ollamaModel || '', models: cloudModels, paused: !!data.ollamaPaused, retryAt: data.ollamaRetryAt || 0}};
  }
  async function refresh() {
    const first = chatgpt.status();
    const [catalog, locals, identity, models] = await Promise.allSettled([
      first.enabled ? chatgpt.models(first.active) : [], chatgpt.locals(), ollama.identity(), ollama.models(),
    ]);
    cloudState = identity.status === 'fulfilled' ? identity.value : {running: false, connected: false};
    // Never send a sign-in URL through renderer IPC.
    delete cloudState.signin;
    cloudModels = models.status === 'fulfilled' ? models.value : [];
    if (ollama.pending && cloudState.connected) { enableOllama(cloudState.name); ollama.cancel(); }
    const current = status();
    return {...current, models: current.active === first.active && catalog.status === 'fulfilled' ? catalog.value : current.models,
      locals: locals.status === 'fulfilled' ? locals.value : [], warning: catalog.status === 'rejected' ? catalog.reason.message : ''};
  }
  function enableOllama(name) {
    const data = auth.vault.get(), changed = data.ollamaAccount !== name;
    auth.vault.set({...data, ollamaEnabled: true, ollamaAccount: name,
      ...(changed ? {ollamaPaused: false, ollamaRetryAt: 0, ollamaModel: ''} : {})});
  }
  async function connectOllama() {
    const result = await ollama.connect();
    if (result.connected) enableOllama(result.name);
    return {...await refresh(), ollamaLoginPending: ollama.pending};
  }
  function disconnectOllama() {
    ollama.cancel();
    const data = auth.vault.get();
    auth.vault.set({...data, ollamaEnabled: false});
    return status();
  }
  async function settings(change) {
    const old = auth.vault.get();
    if (Object.hasOwn(change, 'primary') && !['chatgpt', 'ollama-cloud'].includes(change.primary)) throw Error('Unsupported account provider.');
    if (Object.hasOwn(change, 'ollamaModel') && !cloudModels.some(m => m.slug === change.ollamaModel)) throw Error('Choose an available Ollama Cloud model.');
    if (change.retryOllama && old.ollamaRetryAt > Date.now()) throw Error('Ollama asked ANT to wait before retrying.');
    await chatgpt.settings(change);
    const data = auth.vault.get();
    auth.vault.set({...data,
      ...(change.primary ? {primary: change.primary} : {}),
      ...(typeof change.crossFallback === 'boolean' ? {crossFallback: change.crossFallback} : {}),
      ...(change.ollamaModel ? {ollamaModel: change.ollamaModel} : {}),
      ...(change.retryOllama ? {ollamaPaused: false, ollamaRetryAt: 0} : {}),
    });
    return status();
  }
  async function stream(raw, emit, signal) {
    const input = validateRequest(raw), data = {...auth.vault.get()};
    const primary = data.primary || 'chatgpt';
    const candidates = [primary];
    if (data.crossFallback) candidates.push(primary === 'chatgpt' ? 'ollama-cloud' : 'chatgpt');
    if (data.fallback) candidates.push('local');
    let previous = '', partial = false, lastError;
    for (const provider of candidates) {
      signal.throwIfAborted();
      if (provider !== primary) {
        if (provider === 'chatgpt' && !chatgpt.status().enabled) continue;
        if (provider === 'ollama-cloud' && (!data.ollamaEnabled || !data.ollamaModel)) continue;
      }
      const label = provider === 'chatgpt' ? 'ChatGPT' : provider === 'ollama-cloud' ? 'Ollama Cloud' : data.fallback;
      // Wait for a real successful stream before discarding a partial answer.
      let started = false;
      const forward = event => {
        if (!started && ['meta', 'chunk'].includes(event.type)) {
          started = true;
          if (previous) emit({type: 'notice', provider, message: `${previous} reached its limit → switched to ${label}.${partial ? ' Restarting the incomplete answer.' : ''}`});
          if (partial) { emit({type: 'reset'}); partial = false; }
        }
        if (event.type === 'chunk') partial = true;
        emit(event);
      };
      try {
        if (provider === 'chatgpt') await chatgpt.stream(raw, forward, signal, {allowLocalFallback: false});
        else if (provider === 'local') await ollama.stream(input, data.fallback, forward, signal, {local: true});
        else {
          if (!data.ollamaEnabled) throw Error('Connect your Ollama account in Settings → Providers.');
          const identity = await ollama.identity();
          if (!identity.connected || identity.name !== data.ollamaAccount) throw Error('Your Ollama account changed or signed out. Connect it again in Providers.');
          if (data.ollamaPaused && (!data.ollamaRetryAt || data.ollamaRetryAt > Date.now())) throw Object.assign(Error('Ollama Cloud is paused after a usage limit.'), {limited: true});
          if (data.ollamaPaused) auth.vault.set({...auth.vault.get(), ollamaPaused: false, ollamaRetryAt: 0});
          if (!data.ollamaModel) throw Error('Select an Ollama Cloud model in Providers.');
          await ollama.stream(input, data.ollamaModel, forward, signal);
        }
        return;
      } catch (error) {
        signal.throwIfAborted();
        if (!error.limited) throw error;
        if (provider === 'ollama-cloud') auth.vault.set({...auth.vault.get(), ollamaPaused: true, ollamaRetryAt: error.retryAt || data.ollamaRetryAt || 0});
        emit({type: 'notice', provider, message: error.message});
        previous = label; lastError = error;
      }
    }
    throw lastError || Error('No connected account or selected local fallback is available.');
  }
  return {status, refresh, settings, stream, connectOllama, disconnectOllama,
    async addOllamaModel(name) { await ollama.addModel(name); return refresh(); },
    cancelOllama() { ollama.cancel(); return status(); }};
}
module.exports = {createConnectedModels};
