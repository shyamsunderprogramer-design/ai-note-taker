/* Native subscription bridge. No OAuth tokens are exposed to this page. */
(() => {
  const native = window.api?.subscriptions;
  let state = {}, localModels = [], busy = false, ollamaBusy = false, pollTimer = null;
  const activeLabel = () => state.primary === 'ollama-cloud'
    ? state.ollama?.paused ? 'Ollama Cloud paused' : state.ollama?.enabled ? 'Using Ollama account' : 'Connect Ollama in Providers'
    : state.paused ? 'ChatGPT paused' : state.enabled ? 'Using ChatGPT plan' : 'Connect ChatGPT in Providers';
  const el = id => document.getElementById(id);
  const feedback = message => { el('subscriptionFeedback').textContent = message; };
  async function call(method, value) {
    if (!native) throw Error('Open the ANT desktop app to connect your subscription.');
    const result = await native[method](value);
    if (result?.error) throw Error(result.error);
    return result?.value;
  }
  function options(select, entries, value, placeholder) {
    select.replaceChildren();
    if (placeholder) select.add(new Option(placeholder, ''));
    for (const entry of entries) select.add(new Option(entry.label, entry.value));
    select.value = value;
  }
  function render(next) {
    state = {...state, ...next};
    if (next.locals) localModels = next.locals;
    const current = state.accounts?.find(a => a.id === state.active);
    const summary = !native ? 'Subscription login is available in the ANT desktop app.' :
      busy ? 'Finish signing in with ChatGPT in your browser…' : state.paused ? 'ChatGPT plan paused after a usage limit. Manage usage or retry below.' :
      state.enabled ? `Connected: ${current?.label || 'ChatGPT account'}` : state.connected ? 'Signed in. Continue with ChatGPT to enable plan usage.' : 'No ChatGPT plan connected.';
    el('subscriptionStatus').textContent = summary;
    options(el('subscriptionAccount'), (state.accounts || []).map(a => ({label: a.label + (a.connected ? '' : ' · signed out'), value: a.id})), state.active || '', 'Add an account');
    options(el('subscriptionModel'), (state.models || []).map(m => ({label: m.name, value: m.slug})), state.model || state.models?.[0]?.slug || '', state.models?.length ? null : 'Connect or refresh to see your models');
    const fallbacks = [...new Set([...localModels, ...(state.fallback ? [state.fallback] : [])])];
    options(el('subscriptionFallback'), fallbacks.map(name => ({label: name + (localModels.includes(name) ? '' : ' · unavailable'), value: name})), state.fallback || '', 'Off — ask me to retry');
    el('subscriptionConnect').disabled = !native || busy;
    el('subscriptionAccount').disabled = !native || busy;
    el('subscriptionCancel').hidden = !busy;
    el('subscriptionDisconnect').hidden = !state.connected || busy;
    el('subscriptionModel').disabled = !state.enabled || !state.models?.length || busy;
    el('subscriptionUse').disabled = !state.enabled || !state.models?.length || busy;
    el('subscriptionFallback').disabled = !native || busy;
    el('subscriptionRefresh').disabled = !native || busy;
    el('subscriptionRetry').hidden = !state.paused;
    el('subscriptionPrimary').value = state.primary || 'chatgpt';
    el('subscriptionPrimary').disabled = !native;
    el('subscriptionCrossFallback').checked = !!state.crossFallback;
    el('subscriptionCrossFallback').disabled = !native;
    el('subscriptionShortcut').textContent = 'Providers';
    el('chatgptConnection').querySelector('summary').textContent = `ChatGPT subscription · ${state.enabled ? 'Connected' : 'Sign in without an API key'}`;
    el('ollamaConnection').querySelector('summary').textContent = `Ollama account · ${state.ollama?.enabled ? 'Connected' : 'Sign in without an API key'}`;
    if (el('modelSelect').value === 'subscription') {
      el('modelProviderStatus').textContent = activeLabel();
      el('subscriptionComposerUsage').href = state.primary === 'ollama-cloud' ? 'https://ollama.com/settings/usage' : 'https://chatgpt.com/settings/usage';
    }
    const o = state.ollama || {};
    el('ollamaAccountStatus').textContent = !native ? 'Open the desktop app to connect Ollama.' : o.paused ? 'Ollama Cloud paused after a usage limit.' :
      o.enabled ? `Connected: ${o.name}` : o.connected ? `Signed in to Ollama as ${o.name}. Connect to allow ANT to use this account.` :
      state.ollamaLoginPending ? 'Finish signing in in your browser, then check sign-in.' : o.warning || (o.running ? 'Ollama is running. Connect your account to use cloud models.' : 'Start the Ollama app, then check sign-in.');
    options(el('ollamaAccountModel'), (o.models || []).map(m => ({label: m.name, value: m.slug})), o.model || o.models?.[0]?.slug || '', o.models?.length ? null : 'Add a cloud model in Ollama or below');
    for (const id of ['ollamaAccountConnect','ollamaAccountRefresh','ollamaAccountAdd']) el(id).disabled = !native || ollamaBusy;
    el('ollamaAccountModel').disabled = !o.enabled || !o.models?.length || ollamaBusy;
    el('ollamaAccountUse').disabled = !o.enabled || !o.models?.length || ollamaBusy;
    el('ollamaAccountCancel').hidden = !state.ollamaLoginPending;
    el('ollamaAccountDisconnect').hidden = !o.enabled;
    el('ollamaAccountRetry').hidden = !o.paused;

  }
  async function refresh() {
    if (!native) { render({}); return; }
    render(await call('status'));
    try { const result = await call('refresh'); render(result); feedback(result.warning || ''); } catch (error) { feedback(error.message); }
  }
  function open(event) {
    event?.stopPropagation();
    if (typeof closeProviderConfig === 'function') closeProviderConfig();
    if (typeof openSettings === 'function') openSettings();
    document.querySelector('[data-tab="providers"]')?.click();
    el('providersTitle').focus({preventScroll: true});
    el('providersSettings').closest('.settings-body').scrollTop = 0;
  }
  function selectSubscription() {
    el('modelSelect').value = 'subscription';
    el('modelSelect').dispatchEvent(new Event('change', {bubbles: true}));
  }
  function notice(message, provider) {
    call('status').then(render).catch(() => {});
    el('subscriptionNotice').hidden = false;
    el('subscriptionNoticeText').textContent = message;
    const link = el('subscriptionNotice').querySelector('a');
    link.href = provider === 'ollama-cloud' ? 'https://ollama.com/settings/usage' : 'https://chatgpt.com/settings/usage';
  }
  async function ensureReady() {
    const current = await call('status');
    // ChatGPT's grant is known locally. Reject a missing connection before
    // capturing the screen; Ollama identity/model validation stays in its route.
    if (current?.primary !== 'ollama-cloud' && !current?.enabled) {
      throw Error('Connect and enable your ChatGPT plan in Settings → Providers, or choose a configured model from Model.');
    }
  }
  async function response(input, signal) {
    if (!native) throw Error('Subscription answers require the ANT desktop app.');
    signal?.throwIfAborted();
    const id = crypto.randomUUID(), encoder = new TextEncoder();
    let off, ended = false, controller;
    const clean = () => { off?.(); signal?.removeEventListener('abort', abort); };
    const abort = () => {
      if (ended) return;
      ended = true; clean(); native.cancel(id).catch(() => {});
      controller.error(new DOMException('Subscription answer cancelled.', 'AbortError'));
    };
    const body = new ReadableStream({
      start(value) {
        controller = value;
        off = native.onEvent((requestId, data) => {
          if (requestId !== id || ended) return;
          if (data.type === 'end') { ended = true; clean(); controller.close(); return; }
          if (data.type === 'notice') { notice(data.message, data.provider); return; }
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
        });
        signal?.addEventListener('abort', abort, {once: true});
      },
      cancel() { if (!ended) { ended = true; clean(); native.cancel(id).catch(() => {}); } },
    });
    try {
      const result = await native.start(id, input);
      if (result?.error) throw Error(result.error);
      return new Response(body, {headers: {'Content-Type': 'text/event-stream'}});
    } catch (error) { ended = true; clean(); native.cancel(id).catch(() => {}); await body.cancel(); throw error; }
  }
  window.ANTSubscriptions = {open, refresh, response, ensureReady, label: activeLabel};
  document.addEventListener('DOMContentLoaded', () => {
    const run = fn => async () => { try { await fn(); } catch (error) { feedback(error.message); } };
    el('subscriptionShortcut').addEventListener('click', open);
    el('subscriptionWelcome').addEventListener('keydown', event => event.stopPropagation());
    el('providersSettings').addEventListener('keydown', event => {
      event.stopPropagation();
      if (event.key === 'Escape') { el('closeSettingsBtn').click(); el('subscriptionShortcut').focus(); }
    });
    document.querySelector('[data-tab="providers"]').addEventListener('click', run(async () => {
      if (el('providerConfigPanel').classList.contains('open')) closeProviderConfig();
      await refresh();
    }));
    el('subscriptionRefresh').addEventListener('click', run(refresh));
    el('subscriptionConnect').addEventListener('click', run(async () => {
      const id = el('subscriptionAccount').value;
      busy = true; feedback(''); render({});
      try {
        render(await call('connect', id));
        if (state.enabled) render(await call('settings', {primary: 'chatgpt'}));
        await refresh();
        if (state.enabled) {
          selectSubscription();
          if (!state.welcomeSeen) el('subscriptionWelcome').showModal();
        }
      } finally { busy = false; render({}); }
    }));
    el('subscriptionCancel').addEventListener('click', run(() => call('cancelLogin')));
    el('subscriptionDisconnect').addEventListener('click', run(async () => {
      const result = await call('disconnect'); render({...result, models: []}); feedback(result.warning || 'Disconnected from ChatGPT.');
    }));
    el('subscriptionAccount').addEventListener('change', run(async () => {
      const id = el('subscriptionAccount').value;
      if (id) { render({...await call('settings', {active: id}), models: []}); await refresh(); }
    }));
    el('subscriptionModel').addEventListener('change', run(async () => render(await call('settings', {model: el('subscriptionModel').value}))));
    el('subscriptionFallback').addEventListener('change', run(async () => {
      try { render(await call('settings', {fallback: el('subscriptionFallback').value})); feedback('Fallback preference saved.'); }
      catch (error) { render({}); throw error; }
    }));
    el('subscriptionRetry').addEventListener('click', run(async () => { render(await call('settings', {retry: true})); feedback('ChatGPT will be tried on your next question.'); }));
    el('subscriptionUse').addEventListener('click', run(async () => {
      render(await call('settings', {model: el('subscriptionModel').value, primary: 'chatgpt'}));
      selectSubscription();
      feedback('ChatGPT subscription selected for your next answer.');
    }));
    el('subscriptionWelcome').addEventListener('close', run(async () => render(await call('settings', {welcomeSeen: true}))));
    el('subscriptionDismiss').addEventListener('click', () => { el('subscriptionNotice').hidden = true; });
    el('subscriptionPrimary').addEventListener('change', run(async () => { render(await call('settings', {primary: el('subscriptionPrimary').value})); selectSubscription(); }));
    el('subscriptionCrossFallback').addEventListener('change', run(async () => render(await call('settings', {crossFallback: el('subscriptionCrossFallback').checked}))));
    const ollamaRun = fn => async event => {
      const selected = event?.target?.value;
      ollamaBusy = true; render({}); el('ollamaAccountFeedback').textContent = '';
      try { await fn(selected); } catch (error) { el('ollamaAccountFeedback').textContent = error.message; }
      finally { ollamaBusy = false; render({}); }
    };
    const stopPolling = () => { clearTimeout(pollTimer); pollTimer = null; };
    async function pollOllama(until) {
      if (!state.ollamaLoginPending) return;
      if (Date.now() >= until) { render({ollamaLoginPending: false}); await call('cancelOllama'); el('ollamaAccountFeedback').textContent = 'Connection timed out. Connect again to retry.'; return; }
      try {
        render(await call('refresh'));
        if (state.ollama?.enabled) { render({ollamaLoginPending: false}); el('ollamaAccountFeedback').textContent = 'Ollama connected. Select a model to use it.'; return; }
      } catch { /* A temporary local service failure is shown by the next refresh. */ }
      if (state.ollamaLoginPending) pollTimer = setTimeout(() => pollOllama(until), 2000);
    }
    el('ollamaAccountConnect').addEventListener('click', ollamaRun(async () => {
      stopPolling(); render(await call('connectOllama'));
      if (state.ollamaLoginPending) pollTimer = setTimeout(() => pollOllama(Date.now() + 180000), 2000);
    }));
    el('ollamaAccountCancel').addEventListener('click', ollamaRun(async () => { stopPolling(); render({...await call('cancelOllama'), ollamaLoginPending: false}); }));
    el('ollamaAccountDisconnect').addEventListener('click', ollamaRun(async () => { stopPolling(); render({...await call('disconnectOllama'), ollamaLoginPending: false}); }));
    el('ollamaAccountRefresh').addEventListener('click', ollamaRun(refresh));
    el('ollamaAccountModel').addEventListener('change', ollamaRun(async selected => render(await call('settings', {ollamaModel: selected}))));
    el('ollamaAccountUse').addEventListener('click', ollamaRun(async () => {
      render(await call('settings', {ollamaModel: el('ollamaAccountModel').value, primary: 'ollama-cloud'})); selectSubscription();
      el('ollamaAccountFeedback').textContent = 'Ollama account selected for your next answer.';
    }));
    el('ollamaAccountAdd').addEventListener('click', ollamaRun(async () => {
      const name = el('ollamaAccountModelName').value.trim();
      render(await call('addOllamaModel', name)); el('ollamaAccountFeedback').textContent = 'Cloud model added. Select it above.';
    }));
    el('ollamaAccountRetry').addEventListener('click', ollamaRun(async () => render(await call('settings', {retryOllama: true}))));
    for (const link of document.querySelectorAll('.ollama-account-usage, #ollamaAccountDownload')) link.addEventListener('click', event => {
      if (native) { event.preventDefault(); call(link.id === 'ollamaAccountDownload' ? 'ollamaDownload' : 'ollamaUsage').catch(error => { el('ollamaAccountFeedback').textContent = error.message; }); }
    });
    window.addEventListener('beforeunload', stopPolling);
    for (const link of document.querySelectorAll('.subscription-usage')) link.addEventListener('click', event => {
      if (native) { event.preventDefault(); call(link.href.startsWith('https://ollama.com/') ? 'ollamaUsage' : 'usage').catch(error => feedback(error.message)); }
    });
    refresh().catch(error => { render({}); feedback(error.message); });
  });
})();
