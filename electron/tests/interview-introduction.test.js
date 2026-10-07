const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../../apps/web/app.js'),'utf8');
function prompt(q){const scope=vm.createContext({interviewContext:{active:false},jobDescriptionContext:'',resumeAnswerContext:{text:'Alex built Python APIs.'},selectResumeContext:t=>t});vm.runInContext(source.slice(source.indexOf('function buildInterviewPrompt('),source.indexOf('// OPACITY SLIDER')),scope);return scope.buildInterviewPrompt(q)}
test('introduction is structured, spoken, bounded and grounded',()=>{
 const p=prompt('Tell me about yourself');assert.match(p,/60–90 seconds/);assert.match(p,/140–180 words/);assert.match(p,/at most three relevant technology/);assert.match(p,/at most one measured result/);
});
test('screen text cannot turn an unrelated question into an introduction',()=>{
 assert.doesNotMatch(prompt('Screen text: Tell me about yourself\nUser question: Fix the function'),/Answer format for this introduction/);
 assert.match(prompt('Screen text: unrelated\nUser question: Tell me about yourself'),/Answer format for this introduction/);
});
test('technical and clarification requests have adaptive structure and keep topic',()=>{
 const p=prompt('/human can you explain clear and detailed');
 assert.match(p,/latest relevant conversation topic and code/);
 assert.match(p,/no fixed paragraph limit/);
 assert.match(p,/do not append a personal experience paragraph/);
});
