import {chromium} from '@playwright/test';
const b=await chromium.connectOverCDP('http://127.0.0.1:9223');
try{
 const p=b.contexts().flatMap(c=>c.pages()).find(p=>/index.html/.test(p.url()));
 const state=await p.evaluate(()=>{
  if(isProcessing||isListening)throw new Error('Active conversation; reload deferred');
  return {messages:currentMessages,id:currentConversationId,draft:textInput.value,key:configApiKeyInput.value,provider:activeProvider,collapsed:conversationPanel.hidden,auto:!!autoSSBtn?.classList.contains('active'),mic:alwaysOnActive};
 });
 await p.reload();await p.waitForFunction(()=>typeof loadConversationIntoUI==='function'&&typeof toggleHistoryPanel==='function');
 await p.evaluate(s=>{
  if(s.messages.length)loadConversationIntoUI({id:s.id,messages:s.messages,isAutoScreenshot:s.auto,isAlwaysOnMic:s.mic});
  textInput.value=s.draft;
  if(s.key){openProviderConfig(s.provider);configApiKeyInput.value=s.key;}
 },state);
 state.key='';state.messages=[];
 await p.waitForTimeout(300);
 await p.evaluate(()=>{if(!document.getElementById('conversationPanel').hidden)document.getElementById('conversationToggle').click();});
 await p.waitForTimeout(300);
 const compact=await p.evaluate(()=>innerHeight);
 await p.evaluate(()=>{if(!historyPanel.classList.contains('open'))toggleHistoryPanel();});
 await p.waitForFunction(()=>innerHeight>=600);
 await p.waitForTimeout(700);
 console.log(JSON.stringify(await p.evaluate(compact=>{const list=document.getElementById('historyList');list.scrollTop=list.scrollHeight;return {compactHeight:compact,historyHeight:innerHeight,historyOpen:historyPanel.classList.contains('open'),conversationHidden:document.getElementById('conversationPanel').hidden,listHeight:list.clientHeight,contentHeight:list.scrollHeight,scrollTop:list.scrollTop,itemCount:list.querySelectorAll('.history-item').length};},compact)));
 await p.bringToFront();
}finally{await b.close()}
