import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
function worker({ offline = false, cached, cacheControl = '' } = {}) {
  const handlers = {}, writes = [], deleted = [];
  const fresh = { status: 200, type: 'basic', headers: new Headers({ 'Cache-Control': cacheControl }), clone() { return this; } };
  const cache = { match: async () => cached, put: async (...args) => writes.push(args) };
  vm.runInNewContext(source, {
    self: { location: { origin: 'https://ant.test' }, addEventListener: (name, handler) => { handlers[name] = handler; }, clients: { claim() {} } },
    caches: { open: async () => cache, keys: async () => ['ant-cache-v3', 'ant-cache-v4', 'unrelated'], delete: async name => deleted.push(name) },
    fetch: async () => { if (offline) throw new Error('offline'); return fresh; },
    URL, Response, console,
  });
  async function request(path, options = {}) {
    let response;
    const pending = [];
    handlers.fetch({ request: new Request(new URL(path, 'https://ant.test'), options),
      respondWith: value => { response = value; }, waitUntil: value => pending.push(value) });
    const result = await response;
    await Promise.all(pending);
    return result;
  }
  return { request, fresh, writes, handlers, deleted };
}

test('private API and cross-origin requests bypass caching', async () => {
  const sw = worker();
  for (const path of ['/auth/me', '/api/notes', '/conversations', 'https://other.test/app.js']) {
    assert.equal(await sw.request(path), undefined);
  }
  assert.equal(await sw.request('/app.js', { headers: { Authorization: 'Bearer test' } }), undefined);
  assert.equal(await sw.request('/app.js', { method: 'POST' }), undefined);
  assert.equal(sw.writes.length, 0);
});

test('online requests refresh cached scripts', async () => {
  const sw = worker({ cached: { stale: true } });
  assert.equal(await sw.request('/app.js?v=103'), sw.fresh);
  assert.equal(sw.writes.length, 1);
});

test('private and no-store responses are never cached', async () => {
  for (const cacheControl of ['private', 'no-store']) {
    const sw = worker({ cacheControl });
    assert.equal(await sw.request('/app.js'), sw.fresh);
    assert.equal(sw.writes.length, 0);
  }
});

test('offline assets use cache or a network error, never HTML fallback', async () => {
  const cached = { body: 'script' };
  assert.equal(await worker({ offline: true, cached }).request('/app.js'), cached);
  assert.equal((await worker({ offline: true }).request('/app.js')).type, 'error');
});

test('activation preserves unrelated caches', async () => {
  const sw = worker();
  let completion;
  sw.handlers.activate({ waitUntil: value => { completion = value; } });
  await completion;
  assert.deepEqual(sw.deleted, ['ant-cache-v3']);
});
