import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../app.js', import.meta.url), 'utf8');
const start = source.indexOf('// Reset model to auto if saved model belongs to a disabled provider');
const end = source.indexOf('// Right-click context menu', start);
assert.ok(start >= 0 && end > start);
const restore = source.slice(start, end);

for (const savedModel of ['openai-example', 'example:cloud']) {
  for (const enabled of [false, true, undefined]) {
    test(`${savedModel}: restoring a model respects provider enabled=${enabled}`, async () => {
      const writes = [];
      const modelSelect = {value: savedModel};
      const provider = savedModel.endsWith(':cloud') ? 'ollama-cloud' : 'openai';
      const scope = {
        savedModel, modelSelect,
        appSettings: {
          async get(key) { assert.equal(key, `provider_${provider}`); return {enabled}; },
          async set(...args) { writes.push(args); },
        },
        getBackendProviders: async () => ({[provider]: true}),
        window: {api: {hasApiKey: async () => ({hasKey: false})}},
      };
      await vm.runInNewContext(`(async () => { ${restore} })()`, scope);
      assert.equal(modelSelect.value, enabled === false ? 'auto' : savedModel);
      assert.deepEqual(writes, enabled === false ? [['model', 'auto']] : []);
    });
  }
}
