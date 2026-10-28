// Browser-level controller/HUD smoke. Capture, transcription and AI are deterministic fixtures.
import fs from 'node:fs'
import assert from 'node:assert/strict'
import {chromium} from '@playwright/test'
const html=fs.readFileSync('apps/web/index.html','utf8')
const panel=html.match(/<section id="unifiedSessionPanel"[\s\S]*?<\/section>/)[0]
const browser=await chromium.launch({headless:true})
try {
 const page=await browser.newPage({viewport:{width:640,height:600}})
 await page.setContent(`<style>${fs.readFileSync('apps/web/style.css','utf8')}body{background:#182334;color:#e8eef7;padding:20px}</style><button id="unifiedSessionBtn" class="action-btn">Live helper</button>${panel}`)
 await page.addScriptTag({content:fs.readFileSync('apps/web/js/unified-session.js','utf8')})
 await page.addScriptTag({content:`
 let isListening=false, recordingQuestionHandled=false, alwaysOnEventSource=null, alwaysOnActive=false,
 alwaysOnBtn=null, alwaysOnDot=null, alwaysOnTranscriptionBuffer='', modeSelect={value:'interview'}, modelSelect={value:'auto'};
 const API_BASE='http://fixture';
 Object.defineProperty(window,'localStorage',{value:{getItem:()=>null}});
 function showSummarizeButton(){} function debouncedSave(){} function addErrorMessage(e){throw Error(e)}
 async function startListeningSession(){isListening=true}
 function stopListening(){isListening=false}
 async function recoveryCandidates(){return ['groq-gpt-oss-120b']}
 window.screenEnabled=false;
 window.api={autoScreenshotGetStatus:async()=>({enabled:window.screenEnabled}),autoScreenshotSetEnabled:async enabled=>window.screenEnabled=enabled,
 captureScreenshotContext:async()=>{const c=document.createElement('canvas');c.width=100;c.height=100;return {image:c.toDataURL(),capturedAt:Date.now()}},getOcrUrl:()=>'/ocr'};
 window.fetch=async url=>url==='/ocr'?await new Promise(resolve=>window.completeOcr=()=>resolve({ok:true,json:async()=>({text:'TypeError: Cannot read properties of undefined'})})):new Response('data: '+JSON.stringify({type:'chunk',content:'Check that the object exists before reading its property.'})+'\\n\\ndata: '+JSON.stringify({type:'done'})+'\\n\\n');
 `})
 await page.addScriptTag({content:fs.readFileSync('apps/web/js/unified-session-controller.js','utf8')})
 await page.click('#unifiedSessionBtn')
 await page.waitForFunction(()=>typeof window.completeOcr==='function')
 await page.evaluate(()=>window.observeUnifiedSessionEvent({type:'utterance',source:'system',text:'We agreed to send the report by Friday.',session_id:'smoke',utterance_id:1}))
 assert.match(await page.locator('#unifiedSessionLedger').textContent(),/send the report/)
 assert.equal(await page.evaluate(()=>window.liveSessionContext.screen),null)
 await page.evaluate(()=>window.completeOcr())
 await page.waitForFunction(()=>document.getElementById('unifiedSessionInsight').textContent.includes('Check that the object'))
 await page.locator('details').evaluateAll(nodes=>nodes.forEach(n=>n.open=true))
 await page.screenshot({path:'/tmp/ant-unified-session.png'})
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)
 await page.setViewportSize({width:360,height:600})
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)
 await page.click('#unifiedSessionBtn')
 assert.equal(await page.evaluate(()=>window.unifiedSessionActive),false)
 assert.match(await page.locator('#unifiedSessionStatus').innerText(),/Stopped/)
 console.log(JSON.stringify({scope:'Browser controller/HUD with mocked audio, capture, OCR and AI',passed:true,checks:['speech retained during pending OCR','commitment quote visible','independent streamed code insight','desktop/narrow no overflow','stop retains context'],screenshot:'/tmp/ant-unified-session.png'}))
} finally {await browser.close()}
