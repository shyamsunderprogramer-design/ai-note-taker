const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const renderer=fs.readFileSync(path.join(__dirname,'../renderer/app.js'),'utf8');
const subscriptions=fs.readFileSync(path.join(__dirname,'../renderer/js/subscriptions.js'),'utf8');
function setup(state) {
 const calls=[],errors=[],messages=[];
 const scope=vm.createContext({window:{api:{subscriptions:{status:async()=>({value:state})}}},document:{addEventListener(){}},
  activeQuestion:null,modelSelect:{value:'subscription'},
  beginQuestion(){return scope.activeQuestion={}},isCurrentQuestion:t=>scope.activeQuestion===t,
  setProcessingUI:value=>calls.push(['processing',value]),recoveryCandidates:async()=>['subscription'],
  getQuestionScreenContext:async()=>{calls.push(['capture']);return {}},
  streamMessage:(role,text,options)=>messages.push({role,text,options}),
  answerWithScreenContext:async()=>calls.push(['answer']),addErrorMessage:e=>errors.push(e),clearPendingOcr(){}});
 vm.runInContext(subscriptions,scope);
 vm.runInContext(renderer.slice(renderer.indexOf('async function submitText('),renderer.indexOf('// SUBMIT AUDIO')),scope);
 return {scope,calls,errors,messages,run:()=>scope.submitText('What is 2 + 2?')};
}
test('an unconnected ChatGPT selection reports the connection error before screen capture',async()=>{
 const s=setup({primary:'chatgpt',enabled:false});await s.run();
 assert.equal(s.calls.some(([name])=>name==='capture'||name==='answer'),false);
 assert.match(s.errors[0],/Connect.*ChatGPT.*Providers/);
 assert.equal(s.messages.length,1);
 assert.equal(s.messages[0].options?.captureMetadata,null);
 assert.equal(s.scope.activeQuestion,null);
 assert.deepEqual(s.calls.at(-1),['processing',false]);
});
test('connected ChatGPT and Ollama account routes retain normal answer preparation',async()=>{
 for(const state of [{primary:'chatgpt',enabled:true},{primary:'ollama-cloud',enabled:false}]) {
  const s=setup(state);await s.run();
  assert.deepEqual(s.calls.filter(([name])=>name==='capture'||name==='answer'),[['capture'],['answer']]);
  assert.deepEqual(s.errors,[]);
 }
});
test('API-key models do not depend on account preflight',async()=>{
 const s=setup({enabled:false});s.scope.modelSelect.value='groq-qwen3-8-27b';await s.run();
 assert(s.calls.some(([name])=>name==='answer'));assert.deepEqual(s.errors,[]);
});
