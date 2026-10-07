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
test('screen request without a capture is explicit instead of invented',async()=>{
 const s=setup(false);await assert.rejects(s.run('answerWithScreenContext("Answer the question on screen",{})'),/No screen context/);assert.deepEqual(s.calls,[]);
});
test('all-visible and singular question scopes are defined and refreshed',async()=>{
 const s=setup();await s.run('getQuestionScreenContext().then(c=>answerWithScreenContext("Answer all visible questions",c))');
 assert.match(s.calls[1],/each readable question in order/);assert.match(s.calls[1],/ask which number instead of guessing/);
 await s.run('getQuestionScreenContext()');assert.equal(s.calls.filter(x=>x==='capture').length,2);
});

function submissionScope(captureFails) {
 const messages=[]; const errors=[]; const ticket={controller:{signal:undefined}};
 const scope=vm.createContext({window:{speechSynthesis:{cancel(){}}},beginQuestion:()=>ticket,
 modelSelect:{value:'auto'},recoveryCandidates:async()=>['groq-gpt-oss-120b'],
 isCurrentQuestion:()=>true,setProcessingUI(){},getQuestionScreenContext:async()=>{if(captureFails)throw Error('capture failed');return {};},
 streamMessage:(role,text)=>messages.push({role,text}),answerWithScreenContext:async()=>{throw Error('answer failed');},
 addErrorMessage:e=>errors.push(e),clearPendingOcr(){},activeQuestion:ticket,FormData,
 textInput:{value:''},partialTranscriptText:'',API_BASE:'http://test',speakerDiarizationEnabled:false,
 localStorage:{getItem:()=>null},fetch:async()=>({ok:true,json:async()=>({text:'Spoken question'})})});
 vm.runInContext(source.slice(source.indexOf('async function submitText('),source.indexOf('// START / STOP LISTENING')),scope);
 return {scope,messages,errors};
}
for(const audio of [false,true]) for(const captureFails of [false,true]) {
 test(`${audio?'spoken':'typed'} question is saved once when ${captureFails?'capture':'answer'} fails`,async()=>{
  const s=submissionScope(captureFails);
  if(audio)s.scope.audioBlob=new Blob(['test']);
  await vm.runInContext(audio?'submitAudio(audioBlob)':'submitText("Typed question")',s.scope);
  assert.equal(s.messages.length,1);assert.equal(s.messages[0].text,audio?'Spoken question':'Typed question');
  assert.deepEqual(s.errors,[captureFails?'capture failed':'answer failed']);
 });
}

test('saved screen context preserves metadata without saving image bytes',()=>{
 const restored=[];
 const scope=vm.createContext({window:{},Event,document:{dispatchEvent(){}},interviewQueueEpoch:0,activeQuestion:null,chatArea:{innerHTML:''},currentMessages:[],currentConversationId:null,suppressAutoSave:false,
 autoSSBtn:null,autoSSDot:null,alwaysOnBtn:null,alwaysOnDot:null,alwaysOnActive:false,
 addMessage:(...args)=>restored.push(args),hideSummarizeButton(){},renderHistoryList(){},scrollChat(){}});
 vm.runInContext(source.slice(source.indexOf('function loadConversationIntoUI('),source.indexOf('function clearConversation(')),scope);
 vm.runInContext('loadConversationIntoUI({id:"qa",messages:[{role:"user",text:"Question",timestamp:123,captureMetadata:{status:"captured",capturedAt:100,displayId:2}}]})',scope);
 assert.equal(restored[0][2].captureMetadata.displayId,2);
 assert.equal(scope.currentMessages[0].captureMetadata.capturedAt,100);
 assert.equal('screenshotB64' in scope.currentMessages[0],false);
});
test('screen metadata label distinguishes failures and captured context',()=>{
 const scope=vm.createContext({});
 vm.runInContext(source.slice(source.indexOf('function renderCaptureMetadata('),source.indexOf('function addMessage(')),scope);
 const label={textContent:'You',title:''};scope.label=label;
 vm.runInContext('renderCaptureMetadata(label,{status:"failed"})',scope);
 assert.match(label.textContent,/Screen capture failed/);
 label.textContent='You';vm.runInContext('renderCaptureMetadata(label,{status:"captured",capturedAt:100,displayId:2})',scope);
 assert.match(label.textContent,/Screen context/);assert.match(label.title,/Display 2/);assert.match(label.title,/not stored/);
});

test('explicit screen request captures fresh context even with automatic capture off',async()=>{
 const s=setup(false);await s.run('getQuestionScreenContext(null,true)');
 assert.deepEqual(s.calls,['capture']);
});

test('ambiguous singular screen question is clarified before inference',async()=>{
 const s=setup(false);s.scope.addMessage=(role,text)=>s.calls.push({role,text});s.scope.setProcessingUI=()=>{};
 await s.run('answerWithScreenContext("Answer the question on screen",{text:"1. What is 7 + 8?\\n2. What is the capital of France?"})');
 assert.equal(s.calls.length,1);assert.equal(s.calls[0].role,'assistant');assert.match(s.calls[0].text,/Which number/);
 assert.equal(s.run('screenQuestionClarification("Answer question 2 on screen","1. What?\\n2. Why?")'),null);
 assert.equal(s.run('screenQuestionClarification("Answer all visible questions","1. What?\\n2. Why?")'),null);
 assert.equal(s.run('screenQuestionClarification("Answer the question on screen","1. Install the app\\n2. Start the app")'),null);
});

test('automatic spoken question captures a fresh screen instead of a stale attachment',async()=>{
 const s=setup(false);s.scope.pendingOcrScreenshot='old-screen';s.scope.pendingOcrText='Old code';
 await s.run('getQuestionScreenContext(null,true)');assert.equal(s.calls[0],'capture');
});
