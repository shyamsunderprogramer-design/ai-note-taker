// Capture real app compositor frames and real spoken-question/provider timings.
import {chromium} from '@playwright/test'
import {execFile} from 'node:child_process'
import {promisify} from 'node:util'
import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
const run=promisify(execFile)
const directory=resolve(process.argv[2] || 'artifacts/technical-interview-2026-10-06')
await mkdir(directory+'/frames',{recursive:true})
const questions=[
 'A Kubernetes deployment has just gone live, and users report increased errors and latency. As the on call engineer, how would you investigate, decide whether to roll back, and communicate?',
 'How would you design a CI CD pipeline that tests a Docker image, checks security, and deploys safely to Kubernetes?',
 'Two engineers run Terraform at the same time and encounter a state lock. What should they do, and how would you prevent this problem?'
]
const topics=[/kubernetes|roll\s*back|rollout/i,/ci\s*[\/-]?\s*cd|pipeline|docker/i,/terraform|state lock/i]
for(let i=0;i<questions.length;i++) await run('/usr/bin/say',['-v','Samantha','-r','175','-o',`${directory}/question-${i+1}.aiff`,questions[i]])
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223')
let page,cdp,recording=false,index=0,origin,videoStart,previousMode,previousModel,previousStyle
const frames=[],writes=[],results=[],errors=[],speechEvents=[]
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
try {
 page=browser.contexts()[0].pages().find(p=>/index.html|signin.html/.test(p.url()))
 if(!page)throw Error('Desktop unavailable')
 page.on('websocket',socket=>{
  if(!socket.url().includes('/ws/transcribe'))return
  socket.on('framereceived',event=>{
   try{
    const data=JSON.parse(String(event.payload))
    if(data.type==='question')speechEvents.push({at:Date.now(),question:data.question,source:data.source,timing:data.timing})
   }catch{}
  })
 })
 await page.reload();await sleep(1500)
 if(page.url().includes('signin.html')){
  if(!process.env.ANT_QA_USERNAME || !process.env.ANT_QA_PASSWORD)throw Error('Set ANT_QA_USERNAME and ANT_QA_PASSWORD for an unsigned-in test session')
  await page.locator('#siUser').fill(process.env.ANT_QA_USERNAME);await page.locator('#siPass').fill(process.env.ANT_QA_PASSWORD);await page.locator('#siBtn').click();await page.waitForURL('**/index.html')
 }
 await page.waitForFunction(()=>typeof startNewConversation==='function')
 page.on('pageerror',e=>errors.push(e.message))
 await page.evaluate(()=>window.api.restoreWindow());await page.bringToFront()
 if(await page.evaluate(()=>window.unifiedSessionActive))await page.locator('#unifiedSessionBtn').click()
 const settings=await page.evaluate(()=>({mode:modeSelect.value,model:modelSelect.value,style:responseStyleSelect.value}))
 previousMode=settings.mode;previousModel=settings.model;previousStyle=settings.style
 await page.evaluate(()=>startNewConversation())
 await page.locator('#modelSelect').selectOption('auto')
 await page.evaluate(()=>{responseStyleSelect.value='spoken';responseStyleSelect.dispatchEvent(new Event('change',{bubbles:true}));document.dispatchEvent(new Event('ant:conversation-opened'));})
 cdp=await page.context().newCDPSession(page)
 cdp.on('Page.screencastFrame',event=>{
  cdp.send('Page.screencastFrameAck',{sessionId:event.sessionId}).catch(()=>{})
  if(!recording)return
  const at=event.metadata.timestamp
  origin??=at
  const file=`frame-${String(index++).padStart(6,'0')}.jpg`
  frames.push({file,at})
  writes.push(writeFile(directory+'/frames/'+file,Buffer.from(event.data,'base64')))
 })
 videoStart=Date.now();recording=true
 await cdp.send('Page.startScreencast',{format:'jpeg',quality:75,maxWidth:1120,maxHeight:1440,everyNthFrame:4})
 await page.locator('#unifiedSessionBtn').click()
 await page.waitForFunction(()=>window.unifiedSessionActive&&isListening)
 await sleep(2500)
 for(let i=0;i<questions.length;i++){
  const before=await page.locator('#chatArea .chat-message.assistant').count()
  const row={question:questions[i],method:i===1?'spoken, automatic detection':'spoken, empty Enter',audioStartSeconds:(Date.now()-videoStart)/1000}
  console.log(`Question ${i+1}: playing spoken interview scenario`)
  await run('/usr/bin/afplay',[`${directory}/question-${i+1}.aiff`])
  const end=Date.now();row.questionEndedSeconds=(end-videoStart)/1000
  if(i!==1){await page.locator('#textInput').fill('');await page.locator('#textInput').press('Enter')}
  let first=null,complete=null,lastText='',state
  const deadline=Date.now()+80000
  while(Date.now()<deadline){
   state=await page.evaluate(({before})=>{
    const nodes=[...document.querySelectorAll('#chatArea .chat-message.assistant')]
    const last=nodes.length>before?nodes.at(-1):null
    const content=last?.querySelector('.msg-content')||last?.querySelector('.msg-bubble')
    return {count:nodes.length,text:content?.innerText||'',processing:isProcessing,active:window.unifiedSessionActive,asked:[...document.querySelectorAll('#chatArea .chat-message.user .msg-bubble')].at(-1)?.innerText||'',turns:window.liveSessionContext.turns.slice(-4)}
   },{before})
   if(state.count>before && topics[i].test(state.asked) && topics[i].test(state.text) && !/^(?:Preparing|Thinking|Connecting|Checking|Switching|Continuing)[\s.…]/i.test(state.text)){
    first??=Date.now();lastText=state.text
    await page.evaluate(()=>{const n=[...document.querySelectorAll('#chatArea .chat-message.assistant')].at(-1);n?.scrollIntoView({block:'start',behavior:'instant'});})
   }
   if(first&&!state.processing){complete=Date.now();break}
   await sleep(150)
  }
  row.firstVisibleAfterSpeechSeconds=first?(first-end)/1000:null
  row.completedAfterSpeechSeconds=complete?(complete-end)/1000:null
  row.answer=lastText;row.completed=!!complete&&!/Answer incomplete|No answer was generated|AI response failed/.test(lastText)
  row.recognizedQuestion=state?.asked||''
  row.matchedInterviewQuestion=topics[i].test(row.recognizedQuestion)&&topics[i].test(lastText)
  row.passed=row.completed&&row.matchedInterviewQuestion
  row.listeningStayedActive=state?.active;row.capturedSources=[...new Set(state?.turns.map(t=>t.source)||[])]
  results.push(row)
  console.log(JSON.stringify({question:i+1,firstVisible:row.firstVisibleAfterSpeechSeconds,completed:row.completedAfterSpeechSeconds,success:row.passed,sources:row.capturedSources}))
  await sleep(5000)
 }
 await page.locator('#unifiedSessionBtn').click()
 await page.evaluate(()=>saveCurrentConversation())
 await sleep(1500)
 const messageCounts = {
  questions:await page.locator('#chatArea .chat-message.user').count(),
  answers:await page.locator('#chatArea .chat-message.assistant').count(),
 }
 recording=false;await cdp.send('Page.stopScreencast');await Promise.all(writes)
 const duration=(Date.now()-videoStart)/1000
 if(frames.length<2)throw Error('No usable app video frames captured')
 const lines=[]
 for(let i=0;i<frames.length;i++){
  lines.push(`file 'frames/${frames[i].file}'`)
  const gap=i+1<frames.length?frames[i+1].at-frames[i].at:.5
  lines.push(`duration ${Math.max(.001,gap).toFixed(6)}`)
 }
 lines.push(`file 'frames/${frames.at(-1).file}'`)
 await writeFile(directory+'/frames.txt',lines.join('\n'))
 const audioArgs=[],filters=[]
 results.forEach((row,i)=>{audioArgs.push('-i',`${directory}/question-${i+1}.aiff`);filters.push(`[${i+1}:a]adelay=${Math.round(row.audioStartSeconds*1000)}:all=1[a${i}]`)})
 filters.push(results.map((_,i)=>`[a${i}]`).join('')+`amix=inputs=${results.length}:normalize=0,apad[audio]`)
 await run('/opt/homebrew/bin/ffmpeg',['-y','-f','concat','-safe','0','-i',directory+'/frames.txt',...audioArgs,'-filter_complex',filters.join(';'),'-map','0:v','-map','[audio]','-vf','scale=1120:1440:force_original_aspect_ratio=decrease,pad=1120:1440:(ow-iw)/2:(oh-ih)/2,fps=15','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-t',String(duration),'-movflags','+faststart',directory+'/technical-interview.mp4'],{timeout:120000,maxBuffer:3000000})
 const report={results,errors,messageCounts,speechEvents,video:'technical-interview.mp4',frameCount:frames.length,durationSeconds:duration,startedAt:new Date(videoStart).toISOString(),passed:results.every(r=>r.passed)&&messageCounts.questions===questions.length&&messageCounts.answers===questions.length,limits:'Simulated spoken interview in real Electron app. Video records app compositor frames with real timestamps; question audio is aligned from the same files played live. No AI responses/transcripts mocked. Audio source labels are not verified people. Timing starts when spoken playback ends, includes transcription, queueing, Enter and generation. Pass checks topic relevance, completion and absence of duplicate messages; it is not a technical correctness grade. Not a Zoom/Meet remote-call test.'}
 await writeFile(directory+'/timings.json',JSON.stringify(report,null,2))
 await writeFile(directory+'/README.md',`# Technical interview recording\n\nWatch [technical-interview.mp4](technical-interview.mp4).\n\n${report.limits}\n\n| Question | First visible after speech | Complete after speech | Relevant completed answer |\n|---|---:|---:|---|\n${results.map((r,i)=>`| ${i+1} | ${r.firstVisibleAfterSpeechSeconds??'not observed'} s | ${r.completedAfterSpeechSeconds??'not observed'} s | ${r.passed} |`).join('\n')}\n\nFull answers, recognized questions and source labels: timings.json.\n`)
 console.log(JSON.stringify({directory,results:results.map(r=>({first:r.firstVisibleAfterSpeechSeconds,complete:r.completedAfterSpeechSeconds,passed:r.passed})),duration,frames:frames.length}))
}finally{
 recording=false
 await cdp?.send('Page.stopScreencast').catch(()=>{})
 if(page){await page.evaluate(()=>{if(window.unifiedSessionActive)window.stopUnifiedSession()}).catch(()=>{})
  if(previousMode)await page.locator('#modeSelect').selectOption(previousMode).catch(()=>{})
  if(previousModel)await page.locator('#modelSelect').selectOption(previousModel).catch(()=>{})
  if(previousStyle)await page.evaluate(s=>{responseStyleSelect.value=s;responseStyleSelect.dispatchEvent(new Event('change',{bubbles:true}))},previousStyle).catch(()=>{})}
 await browser.close()
}
