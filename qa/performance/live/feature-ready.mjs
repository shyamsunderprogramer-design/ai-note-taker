import {chromium} from '@playwright/test';
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
try{
 for(const page of browser.contexts().flatMap(c=>c.pages())){
  if(!/index.html|signin.html/.test(page.url()))continue;
  console.log(JSON.stringify(await page.evaluate(()=>({screen:location.pathname.split('/').pop(),compactBridge:typeof window.api?.setConversationCollapsed,hasToggle:!!document.getElementById('conversationToggle'),processing:typeof isProcessing==='boolean'?isProcessing:null,listening:typeof isListening==='boolean'?isListening:null,draftLength:document.getElementById('textInput')?.value.length||0}))));
 }
}finally{await browser.close()}
