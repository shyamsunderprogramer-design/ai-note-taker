import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const source = fs.readFileSync(new URL('../js/core/overlay-connection.js', import.meta.url), 'utf8');
function setup(base) {
  const sockets = [], timers = new Map(), statuses = [];
  const window = { API_BASE: base, addEventListener() {} };
  class Socket {
    constructor(url) { this.url = url; this.readyState = 0; sockets.push(this); }
    close() { this.readyState = 3; this.onclose?.({ code: 1000 }); }
  }
  let id = 0;
  vm.runInNewContext(source, { window, URL, WebSocket: Socket,
    localStorage: { getItem: () => 'test token&value' },
    setTimeout: fn => { timers.set(++id, fn); return id; }, clearTimeout: key => timers.delete(key) });
  const connection = window.createOverlayConnection({ onStatus: (...args) => statuses.push(args), onMessage() {} });
  return { connection, sockets, timers, statuses };
}
for (const [base, expected] of [['http://127.0.0.1:8046','ws://127.0.0.1:8046'], ['https://example.test/api','wss://example.test/api']]) {
  test(`overlay uses configured backend ${base} and encoded authentication`, () => {
    const { connection, sockets, statuses } = setup(base);
    connection.connect(); connection.connect();
    assert.equal(sockets.length, 1);
    const url = new URL(sockets[0].url);
    assert.equal(url.origin + url.pathname, expected + '/ws/transcribe');
    assert.equal(url.searchParams.get('token'), 'test token&value');
    sockets[0].onmessage({ data: JSON.stringify({ type: 'auth_ok' }) });
    assert.equal(statuses.at(-1)[0], 'connected');
  });
}
test('auth rejection stops retry; unloading clears pending reconnect', () => {
  const { connection, sockets, timers, statuses } = setup('http://127.0.0.1:8046');
  connection.connect(); sockets[0].onclose({ code: 4001 });
  assert.equal(timers.size, 0);
  assert.match(statuses.at(-1)[1], /Sign in/);
  connection.connect(); sockets[1].onclose({ code: 1006 });
  assert.equal(timers.size, 1);
  connection.stop();
  assert.equal(timers.size, 0);
});
