const {test}=require('node:test'), assert=require('node:assert/strict')
const fs=require('node:fs'), vm=require('node:vm'), path=require('node:path')
const read=name=>fs.readFileSync(path.join(__dirname,'../../apps/web/js',name),'utf8')
function setup({microphone=true,capture=null,ocr=null}={}) {
 const elements=new Map(), calls=[]
 let screenEnabled=false
 function element(id) { if(!elements.has(id)) elements.set(id,{textContent:'',hidden:true,disabled:false,handlers:{},attrs:{},classList:{remove(){}},setAttribute(k,v){this.attrs[k]=v},addEventListener(k,fn){this.handlers[k]=fn}});return elements.get(id) }
 const scope=vm.createContext({Date,Promise,Uint8Array,AbortController,AbortSignal,TextDecoder,setTimeout,clearTimeout,
 setInterval:fn=>{calls.push('timer');return 1},clearInterval:()=>calls.push('timer stopped'),
 document:{getElementById:element,createElement:()=>({getContext:()=>({drawImage(){},getImageData:()=>({data:new Uint8Array(64*36*4)})})})},
 Image:class {decode(){return Promise.resolve()}},localStorage:{getItem:()=>null},
 api:{autoScreenshotGetStatus:async()=>({enabled:screenEnabled}),autoScreenshotSetEnabled:async value=>{screenEnabled=value;calls.push(['screen',value])},captureScreenshotContext:capture||(async()=>({image:'image',capturedAt:Date.now()})),getOcrUrl:()=>'/ocr'},
 fetch:ocr||(async()=>({ok:true,json:async()=>({text:'Current slide'})})),speechSynthesis:{cancel(){}},addEventListener(){},
 modeSelect:{value:'interview'},modelSelect:{value:'auto'},isListening:false,alwaysOnEventSource:null,alwaysOnActive:false,alwaysOnBtn:null,alwaysOnDot:null,recordingQuestionHandled:false,alwaysOnTranscriptionBuffer:'',API_BASE:'http://qa',
 showSummarizeButton(){},debouncedSave:()=>calls.push('save'),addErrorMessage:e=>calls.push(['error',e])})
 scope.window=scope
 scope.startListeningSession=async()=>{scope.isListening=microphone;calls.push('mic started')}
 scope.stopListening=()=>{scope.isListening=false;calls.push('mic stopped')}
 vm.runInContext(read('unified-session.js'),scope)
 vm.runInContext(read('unified-session-controller.js'),scope)
 return {scope,calls,elements,click:()=>element('unifiedSessionBtn').handlers.click()}
}
test('one control starts shared capture and stop restores settings',async()=>{
 const s=setup();await s.click();await new Promise(resolve=>setImmediate(resolve))
 assert.equal(s.scope.unifiedSessionActive,true)
 assert.equal(s.scope.modeSelect.value,'adaptive')
 assert.equal(s.elements.get('unifiedSessionBtn').attrs['aria-pressed'],'true')
 s.scope.observeUnifiedSessionEvent({type:'utterance',source:'system',text:'We agreed to send the report.'})
 assert.equal(s.scope.liveSessionContext.turns.length,1)
 assert.match(s.elements.get('unifiedSessionLedger').textContent,/send the report/)
 await s.click()
 assert.equal(s.scope.unifiedSessionActive,false)
 assert.equal(s.scope.isListening,false)
 assert.equal(s.scope.modeSelect.value,'interview')
 assert.ok(s.calls.some(call=>Array.isArray(call)&&call[0]==='screen'&&call[1]===false))
 assert.equal(s.scope.liveSessionContext.turns.length,1)
})
test('Enter uses raw speech activity and waits for pending ASR without replaying an old question',async()=>{
 const s=setup();await s.click();let cuts=0,submits=0
 s.scope.cutLiveQuestion=()=>{cuts++;return true};s.scope.submitText=()=>submits++
 s.scope.observeUnifiedSessionEvent({type:'activity',source:'mic',speaking:true,transcribing:0})
 s.scope.requestUnifiedHelp();assert.equal(cuts,1);assert.equal(submits,0)
 s.scope.observeUnifiedSessionEvent({type:'activity',source:'mic',speaking:false,transcribing:1})
 s.scope.requestUnifiedHelp();assert.equal(submits,0)
 await s.click()
})
test('same question heard by microphone and system audio produces one answer',async()=>{
 const s=setup();await s.click();const questions=[]
 const dispatch=async data=>questions.push(data.question)
 await Promise.all([
  s.scope.bufferUnifiedQuestion({question:'How do you build a CI CD pipeline?',source:'mic',session_id:'m',answer_id:1},dispatch),
  s.scope.bufferUnifiedQuestion({question:'How do you build a CI/CD pipeline?',source:'system',session_id:'r',answer_id:1},dispatch)
 ])
 assert.equal(questions.length,1)
 await s.click()
})
test('the observed Terraform lock/log disagreement still produces one answer',async()=>{
 const s=setup();await s.click();const questions=[]
 const dispatch=async data=>questions.push(data.question)
 await Promise.all([
  s.scope.bufferUnifiedQuestion({question:'Two engineers run Terraform at the same time and encounter a state log. What should they do?',source:'mic',session_id:'m',answer_id:1},dispatch),
  s.scope.bufferUnifiedQuestion({question:'Two engineers run Terraform at the same time and encounter a state lock. What should they do?',source:'system',session_id:'r',answer_id:1},dispatch)
 ])
 assert.equal(questions.length,1)
 assert.match(questions[0], /state lock/)
 await s.click()
})
test('a slow answer cannot expire deduplication of simultaneous audio questions',async()=>{
 const s=setup();let now=1000
 s.scope.Date=class extends Date {static now(){return now}}
 await s.click();const questions=[]
 const dispatch=async data=>{questions.push(data.question);now+=30000}
 await Promise.all([
  s.scope.bufferUnifiedQuestion({question:'How does Terraform state locking work?',source:'mic',session_id:'m',answer_id:1},dispatch),
  s.scope.bufferUnifiedQuestion({question:'How does Terraform state locking work?',source:'system',session_id:'r',answer_id:1},dispatch)
 ])
 assert.equal(questions.length,1)
 await s.click()
})
test('denied microphone rolls back session and does not replay a recording',async()=>{
 const s=setup({microphone:false});await s.click()
 assert.equal(s.scope.unifiedSessionActive,false)
 assert.equal(s.scope.recordingQuestionHandled,true)
 assert.equal(s.scope.modeSelect.value,'interview')
 assert.ok(s.calls.some(call=>Array.isArray(call)&&call[0]==='error'))
})
test('speech observations arrive without waiting for screen OCR',async()=>{
 let resolveOcr
 const s=setup({ocr:()=>new Promise(resolve=>resolveOcr=resolve)})
 await s.click();await new Promise(resolve=>setImmediate(resolve))
 s.scope.observeUnifiedSessionEvent({type:'utterance',source:'mic',text:'Please send the notes by Friday.'})
 assert.equal(s.scope.liveSessionContext.turns.length,1)
 assert.equal(s.scope.liveSessionContext.screen,null)
 await s.click()
 resolveOcr({ok:true,json:async()=>({text:'Stale screen'})})
 await new Promise(resolve=>setImmediate(resolve))
 assert.equal(s.scope.liveSessionContext.screen,null)
})
test('missing screen permission keeps microphone available and reports degraded state',async()=>{
 const s=setup({capture:async()=>({image:null})});await s.click();await new Promise(resolve=>setImmediate(resolve))
 assert.equal(s.scope.isListening,true)
 assert.match(s.elements.get('unifiedSessionStatus').textContent,/screen unavailable/)
 await s.click()
})

test('final speech from stopped sockets is retained but cannot leak into a new conversation',async()=>{
 const s=setup(), socket={}
 s.scope.transcribeWs=socket;s.scope.interviewQueueEpoch=1
 await s.click();await s.click()
 s.scope.observeUnifiedSessionEvent({type:'utterance',text:'Last spoken sentence.',source:'mic'},socket)
 assert.equal(s.scope.liveSessionContext.turns.length,1)
 s.scope.observeUnifiedSessionEvent({type:'utterance',text:'Unrelated old socket.',source:'mic'},{})
 assert.equal(s.scope.liveSessionContext.turns.length,1)
 s.scope.interviewQueueEpoch=2
 s.scope.observeUnifiedSessionEvent({type:'utterance',text:'Must not enter a new conversation.',source:'mic'},socket)
 assert.equal(s.scope.liveSessionContext.turns.length,1)
})

test('manual help uses finished speech or cuts a pending utterance without stopping audio',async()=>{
 const s=setup(), submitted=[]
 s.scope.submitText=text=>submitted.push(text)
 let cuts=0;s.scope.cutLiveQuestion=()=>{cuts++;return true}
 await s.click()
 s.scope.observeUnifiedSessionEvent({type:'utterance',source:'system',text:'Explain a cluster.'})
 s.scope.requestUnifiedHelp()
 assert.deepEqual(submitted,['Explain a cluster.']);assert.equal(s.scope.isListening,true)
 s.scope.observeUnifiedSessionEvent({type:'partial',source:'system',text:'And how would you configure it'})
 s.scope.requestUnifiedHelp()
 assert.equal(cuts,1);assert.equal(submitted.length,1);assert.equal(s.scope.isListening,true)
 await s.click()
})

test('rapid spoken correction produces one revised question',async()=>{
 const s=setup(), dispatched=[]
 await s.click()
 s.scope.observeUnifiedSessionEvent({type:'utterance',source:'system',text:'Do you know Kubernetes, Docker, CS85?'})
 const dispatch=async data=>dispatched.push(data.question)
 const first=s.scope.bufferUnifiedQuestion({question:'Do you know Kubernetes, Docker, CS85?',session_id:'s',answer_id:1},dispatch)
 const second=s.scope.bufferUnifiedQuestion({question:'CI CD pipeline',session_id:'s',answer_id:2},dispatch)
 await Promise.all([first,second])
 assert.equal(dispatched.length,1);assert.match(dispatched[0],/Kubernetes, Docker, CI\/CD/)
 assert.doesNotMatch(dispatched[0],/CS85/)
 await s.click()
})
test('stopping clears pending speech rather than dispatching it into another session',async()=>{
 const s=setup(), dispatched=[]
 await s.click()
 const pending=s.scope.bufferUnifiedQuestion({question:'Explain CI CD pipeline',session_id:'s',answer_id:1},async data=>dispatched.push(data))
 await s.click();await pending
 assert.equal(dispatched.length,0)
})

test('recent remote question prevents room speech from replacing it while retaining microphone history',async()=>{
 const s=setup();await s.click();const answers=[]
 s.scope.observeUnifiedSessionEvent({type:'utterance',source:'system',text:'How do you prevent duplicate payments?'})
 s.scope.observeUnifiedSessionEvent({type:'utterance',source:'mic',text:'What sir? They have different flavors.'})
 await s.scope.bufferUnifiedQuestion({question:'What sir? They have different flavors.',source:'tab',session_id:'m',answer_id:1},async data=>answers.push(data.question))
 assert.equal(answers.length,0)
 assert.equal(s.scope.liveSessionContext.transcript.length,2)
 let now=Date.now()+6000;s.scope.Date=class extends Date {static now(){return now}}
 await s.scope.bufferUnifiedQuestion({question:'Can you explain idempotency?',source:'tab',session_id:'m',answer_id:2},async data=>answers.push(data.question))
 assert.equal(answers.length,1)
 await s.click()
})

test('Enter and automatic question detection share deduplication even after the first answer completes',async()=>{
 const s=setup();await s.click();const questions=[]
 const dispatch=async data=>questions.push(data.question)
 await Promise.all([
  s.scope.bufferUnifiedQuestion({question:'How do you prevent duplicate payments?',source:'manual',manual:true,session_id:'manual-help',answer_id:1},dispatch),
  s.scope.bufferUnifiedQuestion({question:'How do you prevent duplicate payments?',source:'system',session_id:'r',answer_id:1},dispatch)
 ])
 await s.scope.bufferUnifiedQuestion({question:'How do you prevent duplicate payments?',source:'system',session_id:'r',answer_id:2},dispatch)
 assert.equal(questions.length,1)
 await s.click()
})

test('empty Enter routes retained speech through the shared question queue',async()=>{
 const s=setup();await s.click();const queued=[]
 s.scope.queueInterviewQuestion=data=>queued.push(data)
 s.scope.submitText=()=>{throw Error('Must not bypass deduplication')}
 s.scope.observeUnifiedSessionEvent({type:'utterance',source:'system',text:'How do you prevent duplicate charges?'})
 s.scope.requestUnifiedHelp()
 assert.equal(queued.length,1)
 assert.equal(queued[0].manual,true)
 assert.equal(queued[0].question,'How do you prevent duplicate charges?')
 await s.click()
})
