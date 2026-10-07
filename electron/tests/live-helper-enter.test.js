const {test}=require('node:test'), assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm'), path=require('node:path')
const source=fs.readFileSync(path.join(__dirname,'../../apps/web/app.js'),'utf8')
function setup({text='',focusButton=false}={}) {
 const calls=[]
 let handler
 const input={tagName:'TEXTAREA',value:text}
 const scope=vm.createContext({window:{unifiedSessionActive:true,requestUnifiedHelp:()=>calls.push('help')},
 document:{activeElement:focusButton?{tagName:'BUTTON'}:input,addEventListener:(_,fn)=>handler=fn},
 textInput:input,isListening:true,isProcessing:false,activeQuestion:null,submitText:text=>calls.push(text),
 stopListening:()=>{scope.isListening=false;calls.push('stop')},listenBtn:{click:()=>calls.push('toggle')}})
 const start=source.indexOf('document.addEventListener("keydown", (e) => {')
 const end=source.indexOf('// HELPERS',start)
 vm.runInContext(source.slice(start,end),scope)
 return {calls,scope,input,press:()=>handler({key:'Enter',preventDefault:()=>{if(!calls.includes('prevented'))calls.push('prevented')}})}
}
test('empty Enter requests help without stopping continuous listening',()=>{
 const s=setup();s.press();assert.equal(s.scope.isListening,true);assert.deepEqual(s.calls,['prevented','help'])
})
test('typed Enter sends text while continuous listening remains active',()=>{
 const s=setup({text:'Explain what they said'});s.press();assert.equal(s.scope.isListening,true)
 assert.deepEqual(s.calls,['prevented','Explain what they said']);assert.equal(s.input.value,'')
})
test('Enter after clicking Live helper cannot activate the focused stop button',()=>{
 const s=setup({focusButton:true});s.press();assert.equal(s.scope.isListening,true);assert.deepEqual(s.calls,['prevented','help'])
})

test('Enter cuts only the active remote question when microphone has simultaneous room speech',()=>{
 const sent=[];const scope=vm.createContext({window:{preferRemoteLiveQuestion:()=>true},WebSocket:{OPEN:1},console:{log(){}},
 transcribeWs:{readyState:1,send:()=>sent.push('mic')},systemAudioWs:{readyState:1,send:()=>sent.push('remote')}})
 vm.runInContext(source.slice(source.indexOf('function cutLiveQuestion()'),source.indexOf('/** Render a live-assist message')),scope)
 assert.equal(scope.cutLiveQuestion(),true)
 assert.deepEqual(sent,['remote'])
 scope.window.preferRemoteLiveQuestion=()=>false
 scope.cutLiveQuestion();assert.deepEqual(sent,['remote','mic','remote'])
})
