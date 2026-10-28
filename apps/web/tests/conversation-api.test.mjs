import { test } from 'node:test';
import assert from 'node:assert/strict';

test('conversation requests use configured backend and bearer authentication', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    requests.push({ url, options });
    return new Response(JSON.stringify([]), { status: 200 });
  });
  const requests = [];
  globalThis.window = { API_BASE: 'http://127.0.0.1:8049' };
  globalThis.localStorage = { getItem: () => 'qa-token' };
  t.after(() => { delete globalThis.window; delete globalThis.localStorage; });
  const { API } = await import('../js/core/api.js');
  await API.getConversations();
  await API.loadConversation('a/b');
  assert.equal(await API.saveConversation({ title: 'QA', messages: [] }), true);
  assert.equal(requests.length, 3);
  for (const request of requests) {
    assert.ok(request.url.startsWith('http://127.0.0.1:8049/conversations'));
    assert.equal(request.options.headers.Authorization, 'Bearer qa-token');
  }
  assert.ok(requests[1].url.endsWith('/a%2Fb'));
  assert.equal(requests[2].options.method, 'POST');
});
