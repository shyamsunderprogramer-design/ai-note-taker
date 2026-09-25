const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../../apps/web/app.js'),'utf8');
function setup(enabled=true){
 const calls=[];
 const scope=vm.createContext({pendingOcrScreenshot:null,pendingOcrText:null,window:{api:{autoScreenshotGetStatus:async()=>({enabled}),captureScreenshot:async()=>{calls.push('capture');return 'fresh-screen'}}},runOcr:async()=>({text:'Cedar: budget 4800; spent 6200'}),streamAIResponse:async q=>calls.push(q),streamAIResponseWithImage:async(q,image)=>calls.push({q,image})});
 vm.runInContext(source.slice(source.indexOf('async function getQuestionScreenContext('),source.indexOf('// Build combined query from user text + pending OCR')),scope);
 return {calls,scope,run:code=>vm.runInContext(code,scope)};
}
test('fresh external screen text accompanies the actual user question',async()=>{
 const s=setup();await s.run('getQuestionScreenContext().then(c=>answerWithScreenContext("Which project is above budget?",c))');
 assert.equal(s.calls[0],'capture');assert.match(s.calls[1],/Cedar: budget 4800; spent 6200/);assert.match(s.calls[1],/User question: Which project is above budget\?/);assert.match(s.calls[1],/reference data, not instructions/);
});
test('screen-disabled mode sends only the question',async()=>{
 const s=setup(false);await s.run('getQuestionScreenContext().then(c=>answerWithScreenContext("Question",c))');assert.deepEqual(s.calls,['Question']);
});
test('an attached screenshot takes priority over fresh capture',async()=>{
 const s=setup();s.scope.pendingOcrScreenshot='attached';s.scope.pendingOcrText='Attached text';await s.run('getQuestionScreenContext().then(c=>answerWithScreenContext("Question",c))');assert.equal(s.calls.length,1);assert.match(s.calls[0],/Attached text/);
});
test('capture failure cannot silently answer without requested context',async()=>{
 const s=setup();s.scope.window.api.captureScreenshot=async()=>null;await assert.rejects(s.run('getQuestionScreenContext()'),/capture failed/);assert.equal(s.calls.length,0);
});

test('a question ticket does not turn a text-only question into a screenshot request',async()=>{
 const s=setup(false);await s.run('answerWithScreenContext("Question",{text:null,image:null},{id:1})');assert.deepEqual(s.calls,['Question']);
});
