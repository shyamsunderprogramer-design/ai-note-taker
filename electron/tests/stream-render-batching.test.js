const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../renderer/app.js'),'utf8');
const frame=data=>'data: '+JSON.stringify(data)+'\n\n';

function setup(packets, beforeRead=()=>{}, startedAt) {
 const renders=[],saved=[],statuses=[];
 const ticket={controller:new AbortController(),startedAt};
 let reads=0;
 const scope=vm.createContext({Date,TextDecoder,Uint8Array,setTimeout,clearTimeout,
  activeQuestion:ticket,latestBotMessage:null,API_BASE:'http://qa',
  isCurrentQuestion:t=>scope.activeQuestion===t&&!t.controller.signal.aborted,
  setProcessingUI(){},suppressAutoSave:false,currentMessages:saved,debouncedSave(){},
  streamMessage(){scope.latestBotMessage={bubble:{},element:{classList:{remove(){}},appendChild(){}}}},
  document:{createElement:()=>{const node={setAttribute(){},textContent:''};statuses.push(node);return node}},
  recoveryCandidates:async()=>['qa:local'],resumeContextReady:Promise.resolve(),jobDescriptionReady:Promise.resolve(),
  modelSelect:{value:'qa:local'},isModelDisabled:()=>false,getModelProvider:()=>null,
  getContextMessages:()=>[],window:{},buildInterviewPrompt:q=>q,
  getSelectedMode:()=> 'instant',getSelectedResponseStyle:()=> 'concise',getSelectedTemperature:()=>0,
  setBubbleText:(_bubble,text,streaming=false)=>renders.push({text,streaming}),scrollChat(){},showSummarizeButton(){},
  addErrorMessage:message=>{throw Error(message)},
  fetch:async()=>({ok:true,body:{getReader:()=>({
   async read(){beforeRead(reads,renders,scope);const text=packets[reads++];return text===undefined?{done:true}:{value:new TextEncoder().encode(text),done:false}},
   async cancel(){},releaseLock(){}
  })}})
 });
 vm.runInContext(source.slice(source.indexOf('async function streamRecoveringAnswer('),source.indexOf('async function streamAIResponse(')),scope);
 return {run:()=>scope.streamRecoveringAnswer('Question',null,ticket),renders,saved,statuses};
}

test('displayed response duration includes work before the model request',async()=>{
 const s=setup([frame({type:'chunk',content:'Answer.'})+frame({type:'done'})],()=>{},Date.now()-2000);
 await s.run();
 assert(parseFloat(s.statuses[0].textContent)>=2,'capture and OCR time must be included');
});

test('a network batch renders once and is visible before waiting for another packet',async()=>{
 const text='Some answer text. '.repeat(100);
 const s=setup([Array.from(text,char=>frame({type:'chunk',content:char})).join(''),frame({type:'done'})],(read,renders)=>{
  if(read===1) { assert.equal(renders.length,1); assert.deepEqual(renders[0],{text,streaming:true}); }
 });
 await s.run();
 assert.deepEqual(s.renders,[{text,streaming:true},{text,streaming:false}]);
 assert.equal(s.saved[0].text,text);
});

test('split SSE frames and unicode retain every character in order',async()=>{
 const event=frame({type:'chunk',content:'Answer: café ✓'});
 const s=setup([event.slice(0,19),event.slice(19),frame({type:'chunk',content:' complete.'})+frame({type:'done'})]);
 await s.run();
 assert.deepEqual(s.renders,[{text:'Answer: café ✓',streaming:true},{text:'Answer: café ✓ complete.',streaming:false}]);
});

test('reset and terminal error cannot replay a stale buffered answer',async()=>{
 const s=setup([frame({type:'chunk',content:'Old draft'})+frame({type:'reset'})+frame({type:'chunk',content:'New partial'})+frame({type:'error',message:'Connection ended'})]);
 await s.run();
 assert.equal(s.renders.at(-1).text,'New partial');
 assert.equal(s.renders.at(-1).streaming,false);
 assert.equal(s.saved[0].incomplete,true);
 assert.match(s.saved[0].text,/New partial/);
 assert.doesNotMatch(s.saved[0].text,/Old draft/);
});
