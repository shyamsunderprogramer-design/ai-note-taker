import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../app.js', import.meta.url), 'utf8');
const start = source.indexOf('function buildInterviewPrompt(');
const end = source.indexOf('\n}', start) + 2;
assert.ok(start >= 0 && end > start);

function builder(overrides = {}) {
  const context = vm.createContext({
    interviewContext: {active: false}, resumeAnswerContext: null,
    jobDescriptionContext: '', selectResumeContext: text => text, ...overrides,
  });
  vm.runInContext(source.slice(start, end), context);
  return context.buildInterviewPrompt;
}

test('ordinary questions request reasons and limitations in the initial answer', () => {
  const prompt = builder()('Should I use SQLite for local notes?');
  assert.match(prompt, /^Should I use SQLite for local notes\?/);
  assert.match(prompt, /first response/);
  assert.match(prompt, /Why and Why not sections/);
  assert.match(prompt, /do not invent objections/);
  assert.match(prompt, /Better alternative/);
  assert.match(prompt, /explicitly requests code only/);
});

test('resume context preserves automatic explanations without duplicating them', () => {
  const build = builder({resumeAnswerContext: {text: 'Alex built Python APIs.'}});
  const prompt = build('How would I design a queue?');
  assert.match(prompt, /Alex built Python APIs/);
  assert.match(prompt, /Automatic explanation/);
  assert.equal(build(prompt), prompt);
});

test('spoken mode explains limitations naturally; introductions keep their spoken format', () => {
  const build = builder();
  const spoken = build('Why use a queue?', {compact: true});
  assert.match(spoken, /main limitation/);
  assert.doesNotMatch(spoken, /Why and Why not sections/);
  const introduction = build('Tell me about yourself');
  assert.match(introduction, /Return only the words I could say/);
  assert.doesNotMatch(introduction, /Automatic explanation/);
});
