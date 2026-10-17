import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../app.js', import.meta.url), 'utf8');
const quiet = {log() {}, error() {}};

for (const action of ['accept', 'dismiss']) {
  test(`failed suggestion ${action} does not alter the card`, async () => {
    let queried = false;
    const scope = vm.createContext({console: quiet, API_BASE: 'http://example.invalid',
      fetch: async () => ({ok: false, status: 500}),
      document: {querySelector() { queried = true; throw Error('failed feedback must leave the card alone'); }},
    });
    const start = source.indexOf('async function acceptAgentSuggestion(');
    const end = source.indexOf('// END AI AGENTS FRAMEWORK', start);
    assert.ok(end > start, 'feedback handlers must have a bounded extraction');
    vm.runInContext(source.slice(start, end), scope);
    await scope[`${action}AgentSuggestion`]('synthetic-feedback');
    assert.equal(queried, false);
  });
}

for (const ok of [false, true]) {
  test(`model download ${ok ? 'acknowledgment indicates started' : 'failure keeps the input and permits retry'}`, async () => {
    let click;
    let refreshed = 0;
    const input = {value: 'synthetic-model'};
    const button = {addEventListener(_, handler) { click = handler; }, disabled: false};
    const status = {textContent: '', style: {}};
    const scope = {console: quiet, ollamaPullBtn: button, ollamaPullInput: input, ollamaPullStatus: status,
      window: {api: {pullOllamaModel: async () => ({ok, json: async () => ok ? {status: 'pull_started'} : {error: {code: 'INTERNAL_ERROR'}}})}},
      loadLocalOllamaModels: async () => { refreshed++; },
    };
    const start = source.indexOf('// === Ollama Model Pull Handler ===');
    const end = source.indexOf('// === Race Toggle Rendering ===', start);
    vm.runInNewContext(source.slice(start, end), scope);
    await click();
    assert.equal(button.disabled, false);
    assert.equal(button.textContent, 'Pull');
    if (ok) {
      assert.match(status.textContent, /Download started/);
      assert.doesNotMatch(status.textContent, /Successfully pulled/);
      assert.equal(refreshed, 1);
    } else {
      assert.match(status.textContent, /Failed/);
      assert.equal(input.value, 'synthetic-model');
      assert.equal(refreshed, 0);
    }
  });
}
