// Real ASR/LLM integration: candidate PCM on mic socket, native remote playback.
// The separate synthetic mic input avoids speaker playback leaking into both channels.
import {chromium} from '@playwright/test'
import {execFile} from 'node:child_process'
import {promisify} from 'node:util'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
const run=promisify(execFile),sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const directory=resolve(process.argv[2]||'artifacts/panel-followup-2026-10-07')
await mkdir(directory,{recursive:true})
const original='A Kubernetes deployment increases errors and latency. How would you investigate and recover?'
const candidate='I would first compare error rates with the previous deployment, check rollout status and logs, and confirm whether the service is degraded. If the release is the cause, I would roll back the application while preserving the database changes and verify recovery.'
const followup='What if the database migration cannot be rolled back?'
for(const [name,text,voice] of [['original',original,'Samantha'],['candidate',candidate,'Daniel'],['followup',followup,'Samantha']]){
 await run('/usr/bin/say',['-v',voice,'-r','150','-o',`${directory}/${name}.aiff`,text])
}
await run('/opt/homebrew/bin/ffmpeg',['-y','-i',`${directory}/candidate.aiff`,'-ar','16000','-ac','1','-f','f32le',`${directory}/candidate.pcm`])
const pcm=await readFile(`${directory}/candidate.pcm`)
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223')
const page=browser.contexts()[0].pages().find(p=>/index.html/.test(p.url()))
const requests=[];let streaming=false
page.on('request',request=>{
 if(!request.url().endsWith('/stream-recover'))return
 const body=request.postDataJSON()
 requests.push({at:Date.now(),carriedOriginal:/Kubernetes deployment/i.test(body.query),
  panelFollowup:body.query.includes('[Panel follow-up]'),
  provisionalCandidate:body.query.includes('provisional speech')&&body.query.includes('rollout status'),
  candidateSpeaking:streaming,mode:body.mode,style:body.style})
})
try{
 if(await page.evaluate(()=>window.unifiedSessionActive))await page.locator('#unifiedSessionBtn').click()
 await page.evaluate(()=>startNewConversation())
 await page.locator('#modelSelect').selectOption('auto')
 await page.evaluate(()=>{responseStyleSelect.value='spoken';responseStyleSelect.dispatchEvent(new Event('change',{bubbles:true}))})
 await page.locator('#unifiedSessionBtn').click()
 await page.waitForFunction(()=>isListening&&systemAudioWs?.readyState===WebSocket.OPEN)
 await page.evaluate(()=>{window.qaMicProcess=streamProcessor.onaudioprocess;streamProcessor.onaudioprocess=()=>{}})
 await run('/usr/bin/afplay',[`${directory}/original.aiff`])
 await page.waitForFunction(()=>document.querySelectorAll('#chatArea .chat-message.assistant').length===1&&!isProcessing)
 streaming=true
 const inject=(async()=>{
  for(let offset=0;offset<pcm.length;offset+=6400){
   const chunk=pcm.subarray(offset,offset+6400).toString('base64')
   await page.evaluate(encoded=>{
    const bytes=Uint8Array.from(atob(encoded),character=>character.charCodeAt(0))
    if(transcribeWs?.readyState===WebSocket.OPEN)transcribeWs.send(bytes.buffer)
   },chunk)
   await sleep(100)
  }
  streaming=false
 })()
 await sleep(3500)
 const started=Date.now()
 await run('/usr/bin/afplay',[`${directory}/followup.aiff`])
 const ended=Date.now()
 await page.waitForFunction(()=>document.querySelectorAll('#chatArea .chat-message.assistant').length===2&&!isProcessing)
 const completed=Date.now()
 await inject
 await sleep(1000)
 const state=await page.evaluate(()=>({
  answers:[...document.querySelectorAll('#chatArea .chat-message.assistant .msg-bubble')].map(node=>node.innerText),
  userQuestions:document.querySelectorAll('#chatArea .chat-message.user').length,
  transcript:window.liveSessionContext.transcript.map(turn=>({source:turn.source,text:turn.text})),
  active:window.unifiedSessionActive,
 }))
 const followupRequest=requests.find(request=>request.panelFollowup)
 const passed=state.active&&state.userQuestions===2&&state.answers.length===2&&!!followupRequest?.candidateSpeaking
   &&followupRequest.carriedOriginal&&followupRequest.provisionalCandidate&&/migration|database/i.test(state.answers[1])
 await page.screenshot({path:`${directory}/panel-followup.png`})
 const report={passed,original,candidate,followup,requests,state,followupCompleteAfterSpeechMs:completed-ended,
  limits:'Real Electron app, native remote capture and real ASR/LLM. Synthetic candidate PCM injected on existing microphone WebSocket; no ASR or AI response mocked. Distinct sources are not named/verified people. Not a Zoom/Meet call. Timing includes generation completion, not first token.'}
 await writeFile(`${directory}/results.json`,JSON.stringify(report,null,2))
 console.log(JSON.stringify({passed,requests,completeMs:completed-ended,questions:state.userQuestions,answers:state.answers.length}))
 if(!passed)process.exitCode=1
}finally{
 await page.evaluate(()=>{if(streamProcessor&&window.qaMicProcess)streamProcessor.onaudioprocess=window.qaMicProcess;delete window.qaMicProcess;window.stopUnifiedSession();saveCurrentConversation()}).catch(()=>{})
 await browser.close()
}
