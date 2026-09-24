const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../../apps/web/app.js'), 'utf8');
function setup() {
  const events = {}, frames = new Map(); let frameId = 0;
  const chat = {scrollTop: 200, scrollHeight: 400, clientHeight: 200,
    addEventListener: (name, fn) => events[name] = fn,
    scrollTo: ({top}) => { chat.scrollTop = Math.min(top, chat.scrollHeight - chat.clientHeight); }};
  const scope = vm.createContext({ chatArea: chat,
    requestAnimationFrame: fn => {frames.set(++frameId, fn);return frameId;},
    cancelAnimationFrame: id => frames.delete(id) });
  vm.runInContext(source.slice(source.indexOf('let followChatOutput = true'), source.indexOf('function addMessage(')), scope);
  const tick = time => {const pending=[...frames.values()];frames.clear();pending.forEach(fn=>fn(time));};
  return {chat, events, frames, tick, run: code => vm.runInContext(code, scope)};
}
test('a burst of text follows at a bounded reading speed instead of jumping', () => {
  const s = setup(); s.chat.scrollHeight = 1000; s.events.scroll();
  s.run('scrollChat()'); for(let i=0;i<=60;i++)s.tick(i*1000/60);
  assert.ok(s.chat.scrollTop > 229 && s.chat.scrollTop < 232);
});
test('scrolling up stops queued motion even when still near the bottom', () => {
  const s = setup(); s.chat.scrollHeight=700; s.run('scrollChat()');
  s.events.wheel({deltaY:-10}); s.chat.scrollTop=490; s.events.scroll(); s.tick(20);
  assert.equal(s.chat.scrollTop,490); assert.equal(s.frames.size,0);
});
test('explicit new question resumes following and cancels old animation', () => {
  const s=setup();s.chat.scrollHeight=700;s.run('scrollChat()');
  s.events.wheel({deltaY:-50});s.run('scrollChat(false,true)');
  assert.equal(s.chat.scrollTop,500);assert.equal(s.frames.size,0);
});
test('background frame delay does not produce a large jump', () => {
  const s=setup();s.chat.scrollHeight=1000;s.run('scrollChat()');s.tick(0);
  const before=s.chat.scrollTop;s.tick(10000);
  assert.ok(s.chat.scrollTop-before <= 1.51);
});
