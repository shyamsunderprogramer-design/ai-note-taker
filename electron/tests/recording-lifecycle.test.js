const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../apps/web/app.js'),'utf8');
function setup() {
  const recorders=[],streams=[],errors=[],notices=[],submitted=[];
  class Recorder extends EventTarget {
    constructor(stream){super();this.stream=stream;this.state='inactive';this.mimeType='audio/webm';recorders.push(this)}
    start(){this.state='recording'}
    stop(){this.state='inactive'}
    data(bytes){const event=new Event('dataavailable');event.data=new Blob([Buffer.alloc(bytes)]);this.dispatchEvent(event)}
    stopped(){this.dispatchEvent(new Event('stop'))}
  }
  const scope=vm.createContext({window:{},MediaRecorder:Recorder,Blob,Date,console,
    navigator:{mediaDevices:{getUserMedia:async()=>{const track={stopped:false,stop(){this.stopped=true}};const stream={getTracks:()=>[track]};streams.push(stream);return stream}}},
    isStarting:false,isListening:false,isBackendReady:true,recordingQuestionHandled:false,
    mediaStream:null,mediaRecorder:null,prewarmedMicStream:null,
    setListeningUI:value=>{scope.isListening=value},setProcessingUI(){},startWaveform(){},stopWaveform(){},
    startStreamingTranscription(){},stopStreamingTranscription(){},autoGenerateMeetingNotes(){},
    addErrorMessage:e=>errors.push(e),showToast:e=>notices.push(e),submitAudio:async blob=>submitted.push(blob.size),
  });
  vm.runInContext(source.slice(source.indexOf('async function startListeningSession()'),source.indexOf('// PRE-WARM VOICE RESOURCES')),scope);
  return {scope,recorders,streams,errors,notices,submitted};
}
test('a late stop event cannot consume chunks or stop the next microphone stream',async()=>{
  const s=setup();await s.scope.startListeningSession();s.recorders[0].data(1024);s.scope.stopListening();
  await s.scope.startListeningSession();s.recorders[1].data(2048);
  s.recorders[0].stopped();assert.equal(s.scope.mediaRecorder,s.recorders[1]);
  assert.equal(s.streams[1].getTracks()[0].stopped,false);assert.deepEqual(s.submitted,[]);
  s.scope.stopListening();s.recorders[1].stopped();assert.deepEqual(s.submitted,[2048]);assert.deepEqual(s.errors,[]);
});
test('a quick empty stop explains the short recording without blaming macOS permissions',async()=>{
  const s=setup();await s.scope.startListeningSession();s.scope.stopListening();s.recorders[0].stopped();
  assert.deepEqual(s.errors,[]);assert.deepEqual(s.submitted,[]);assert.match(s.notices[0],/too short/);
});
test('stopping live helper does not replay its recorder or produce an empty recording error',async()=>{
  const s=setup();s.scope.window.unifiedSessionActive=true;
  s.scope.window.stopUnifiedSession=()=>{s.scope.window.unifiedSessionActive=false};
  await s.scope.startListeningSession();s.scope.stopListening();s.recorders[0].stopped();
  assert.deepEqual(s.errors,[]);assert.deepEqual(s.notices,[]);assert.deepEqual(s.submitted,[]);
});
test('permission rejection leaves recording off and cleans up',async()=>{
  const s=setup();s.scope.navigator.mediaDevices.getUserMedia=async()=>{const error=Error('denied');error.name='NotAllowedError';throw error};
  await s.scope.startListeningSession();assert.equal(s.scope.isListening,false);assert.equal(s.scope.isStarting,false);
  assert.match(s.errors[0],/Microphone access denied/);assert.equal(s.recorders.length,0);
});
