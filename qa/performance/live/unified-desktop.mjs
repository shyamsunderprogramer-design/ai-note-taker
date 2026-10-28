// Real signed-in desktop; no mocked capture, transcription or provider responses.
import {chromium} from '@playwright/test'
import {execFile} from 'node:child_process'
import {promisify} from 'node:util'
import {mkdir,writeFile} from 'node:fs/promises'
import assert from 'node:assert/strict'
const run=promisify(execFile), directory='/tmp/ant-unified-live'
await mkdir(directory,{recursive:true})
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223')
try {
 const page=browser.contexts()[0].pages().find(p=>p.url().endsWith('index.html'))
 if(!page)throw Error('Signed-in desktop is missing')
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 if(await page.evaluate(()=>window.unifiedSessionActive)) await page.locator('#unifiedSessionBtn').click()
 await page.evaluate(()=>startNewConversation())
 await page.locator('#unifiedSessionBtn').click()
 await page.waitForTimeout(3000)
 const started=await page.evaluate(()=>({active:window.unifiedSessionActive,status:document.getElementById('unifiedSessionStatus').innerText}))
 await page.screenshot({path:directory+'/listening.png'})
 if(!started.active)throw Error('Live helper did not start: '+started.status)
 // Typed Enter exercises the actual UI and backend while capture stays active.
 const start=Date.now()
 await page.locator('#textInput').fill('Explain Kubernetes, Docker and CI/CD in three short sentences I can say naturally. Do not claim personal work experience.')
 await page.locator('#textInput').press('Enter')
 await page.waitForFunction(()=>typeof isProcessing!=='undefined'&&!isProcessing,{},{timeout:90000})
 const typed=await page.evaluate(()=>({active:window.unifiedSessionActive,text:document.getElementById('chatArea').innerText}))
 typed.elapsedSeconds=(Date.now()-start)/1000
 await page.screenshot({path:directory+'/typed-answer.png'})
 // OS speech playback enters the real system-audio bridge; no injected transcript.
 await run('/usr/bin/say',['-r','145','What is a CI CD pipeline?'])
 await page.waitForTimeout(18000)
 const speech=await page.evaluate(()=>({active:window.unifiedSessionActive,status:document.getElementById('unifiedSessionStatus').innerText,transcript:document.getElementById('unifiedSessionTranscript').textContent,turns:window.liveSessionContext.turns,chat:document.getElementById('chatArea').innerText}))
 await page.locator('#unifiedSessionPanel details').evaluateAll(nodes=>nodes.forEach(node=>node.open=true))
 await page.screenshot({path:directory+'/live-speech.png'})
 await page.locator('#unifiedSessionBtn').click()
 const passed=typed.active && speech.active && speech.turns.some(turn=>/CI CD pipeline/i.test(turn.text)) && /CI\/CD pipeline/.test(speech.chat) && errors.length===0
 const report={passed,started,typed,speech,errors,limits:'Real desktop, backend, microphone request and OS speech playback. Captured source labels determine whether microphone or remote audio actually worked. Response badges exclude speech recognition latency. This is not a real remote call.'}
 await writeFile(directory+'/report.json',JSON.stringify(report,null,2))
 console.log(JSON.stringify(report,null,2))
 assert.equal(passed,true,'Live capture or answer verification failed')
}finally{await browser.close()}
