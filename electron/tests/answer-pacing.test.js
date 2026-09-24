const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../../apps/web/app.js'), 'utf8');
function setup() {
  const timers = [], renders = [];
  const bubble = { isConnected: true, dataset: {}, closest: () => true };
  const scope = vm.createContext({ bubble, normalizeAnswerText: s => s,
    renderBubbleText: (b, text, cursor) => renders.push({ text, cursor }), scrollChat() {},
    setTimeout: (fn, delay) => { assert.equal(delay, 125); timers.push(fn); return timers.length; } });
  vm.runInContext(source.slice(source.indexOf('const ANSWER_WORD_INTERVAL_MS'), source.indexOf('function renderBubbleText(')), scope);
  return { bubble, renders, timers, send: (text, streaming) => {
    scope.text = text; scope.streaming = streaming;
    vm.runInContext('setBubbleText(bubble, text, streaming)', scope);
  }, tick: () => timers.shift()?.() };
}
test('a completed burst continues revealing one word per display interval', () => {
  const s = setup();
  s.send('One two three four five.', true);
  s.send('One two three four five.', false);
  assert.equal(s.renders.length, 0);
  for (let i = 0; i < 4; i++) s.tick();
  assert.equal(s.renders.at(-1).text, 'One two three four ');
  assert.equal(s.renders.at(-1).cursor, true);
  assert.equal(s.bubble.dataset.fullText, 'One two three four five.');
  s.tick();
  assert.deepEqual(s.renders.at(-1), { text: 'One two three four five.', cursor: false });
  assert.equal(s.timers.length, 0);
});
test('chunk updates share one timer and removed messages stop rendering', () => {
  const s = setup(); s.send('One', true); s.send('One two', true);
  assert.equal(s.timers.length, 1);
  s.bubble.isConnected = false; s.tick();
  assert.equal(s.renders.length, 0); assert.equal(s.timers.length, 0);
});
test('saved messages render immediately and a paused stream resumes', () => {
  const s = setup(); s.send('Saved answer', false);
  assert.equal(s.renders[0].text, 'Saved answer');
  s.send('New', true); s.tick();
  assert.equal(s.timers.length, 0);
  s.send('New answer', true); s.send('New answer', false); s.tick();
  assert.equal(s.renders.at(-1).text, 'New answer');
  assert.equal(s.renders.at(-1).cursor, false);
});
