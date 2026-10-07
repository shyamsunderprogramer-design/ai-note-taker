const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../../apps/web/app.js'),'utf8');
test('duplicate pending text is ignored while a distinct question still replaces it',async()=>{
 let release;const pending=new Promise(resolve=>release=resolve);let starts=0;const messages=[];
 const scope=vm.createContext({activeQuestion:null,window:{speechSynthesis:{cancel(){}}},
 modelSelect:{value:'auto'},recoveryCandidates:async()=>[],
 beginQuestion(){starts++;return scope.activeQuestion={};},isCurrentQuestion:t=>scope.activeQuestion===t,
 setProcessingUI(){},getQuestionScreenContext:()=>pending,streamMessage:(r,t)=>messages.push(t),
 answerWithScreenContext:async()=>{},clearPendingOcr(){},addErrorMessage(){}});
 vm.runInContext(source.slice(source.indexOf('async function submitText('),source.indexOf('// SUBMIT AUDIO')),scope);
 const first=scope.submitText('same question');await scope.submitText(' same question ');assert.equal(starts,1);
 const next=scope.submitText('different question');assert.equal(starts,2);
 release({});await Promise.all([first,next]);assert.deepEqual(messages,['different question']);
});
test('AI shortcuts submit drafts and do not interrupt an active answer with an empty screen request',async()=>{
 const handlers={};const calls=[];
 const scope=vm.createContext({window:{api:{onTriggerAI:f=>handlers.ai=f,onTriggerAIScreen:f=>handlers.screen=f}},
 textInput:{value:'hi'},isProcessing:true,activeQuestion:{},alwaysOnTranscriptionBuffer:'',alwaysOnActive:false,
 submitText:async(...args)=>calls.push(args),autoSendToAI:async()=>{throw Error('Unexpected voice submission');}});
 vm.runInContext(source.slice(source.indexOf('if (window.api?.onTriggerAI)'),source.indexOf('// Backend status monitoring')),scope);
 await handlers.ai();assert.equal(calls.length,1);assert.equal(calls[0][0],'hi');assert.equal(scope.textInput.value,'');
 await handlers.ai();await handlers.screen();assert.equal(calls.length,1);
 scope.isProcessing=false;await handlers.screen();assert.equal(calls.length,2);assert.equal(calls[1][1].forceScreen,true);
});
test('greeting answers directly without capturing the screen or consulting resume context',async()=>{
 const messages=[];const saved=[];
 const scope=vm.createContext({activeQuestion:null,window:{speechSynthesis:{cancel(){}}},
 beginQuestion(){return scope.activeQuestion={};},isCurrentQuestion:t=>scope.activeQuestion===t,
 setProcessingUI(){},streamMessage:(role,text)=>messages.push({role,text}),
 getQuestionScreenContext:()=>{throw Error('Greeting must not capture the screen')},
 suppressAutoSave:false,currentMessages:saved,debouncedSave(){}});
 vm.runInContext(source.slice(source.indexOf('async function submitText('),source.indexOf('// SUBMIT AUDIO')),scope);
 await scope.submitText('hi');assert.equal(messages.length,2);assert.equal(messages[1].text,'Hi! What would you like help with?');
 assert.equal(scope.activeQuestion,null);assert.equal(saved.length,1);
});
