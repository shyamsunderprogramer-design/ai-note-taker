/* Build short synthetic resume/JD fixtures through the real app prompt function. */
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync(new URL('../../../apps/web/app.js', import.meta.url), 'utf8');
const start = source.indexOf('function buildInterviewPrompt(');
const end = source.indexOf('\n}', start) + 2;
if (start < 0 || end < start) throw new Error('App prompt function not found');
const context = {
  interviewContext: { active: false },
  resumeAnswerContext: { text: 'Alex built Python APIs at Acme. Alex added Redis caching, reducing measured latency from 900 to 120 milliseconds, and paired with Priya to test the change.' },
  jobDescriptionContext: 'Python platform engineer; Python, Redis, AWS certification, and Kubernetes are desired.',
  selectResumeContext: text => text, // This fixture is shorter than the app excerpt limit.
  question: process.argv[2] || '__QA_QUESTION__',
};
console.log(vm.runInNewContext(source.slice(start, end) + '\nbuildInterviewPrompt(question)', context));
