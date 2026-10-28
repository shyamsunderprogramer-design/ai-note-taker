import { chromium } from '@playwright/test';
import fs from 'node:fs';
const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');
try {
 const page=browser.contexts().flatMap(c=>c.pages()).find(p=>/index.html/.test(p.url()));
 if (!process.argv.includes('--followup')) {
 const state=await page.evaluate(()=>({busy:isProcessing||isListening,draft:document.getElementById('textInput').value,key:document.getElementById('configApiKeyInput').value,provider:activeProvider}));
 if(state.busy) throw new Error('Active conversation: reload deferred');
 await page.reload();
 await page.waitForFunction(()=>typeof buildInterviewPrompt==='function' && typeof isProcessing==='boolean');
 await page.evaluate(s=>{document.getElementById('textInput').value=s.draft;if(s.key){openProviderConfig(s.provider);document.getElementById('configApiKeyInput').value=s.key;}},state);
 state.key='';
 await page.evaluate(()=>window.api.restartBackend());
 for(let i=0;i<40;i++) {const ready=await page.evaluate(async()=>{try{return (await fetch(`${API_BASE}/health`,{signal:AbortSignal.timeout(1000)})).ok}catch{return false}});if(ready)break;await new Promise(r=>setTimeout(r,500));}
 }
 const result=await page.evaluate(async(followup)=>{
   const prompt=followup === 'routing' ? 'clear explanation please' : followup ? '/human can you explain clear and detailed' : 'Explain the Kubernetes cluster from the previous answer more clearly and in detail. Use five numbered sections: what a cluster is, control plane, worker nodes, a local practice setup, and verification. Give an example command where relevant. This is a learning question, not a personal interview answer.';
   let image=null;
   if(followup === 'routing'){const c=document.createElement('canvas');c.width=600;c.height=140;const x=c.getContext('2d');x.fillStyle='white';x.fillRect(0,0,600,140);x.fillStyle='black';x.font='20px sans-serif';x.fillText('Practice topic: on-call rotations',20,55);image=c.toDataURL('image/png').split(',')[1];}
   const candidates=followup === 'routing' ? await recoveryCandidates('auto',image) : ['google-gemini-3-8-flash','groq-gpt-oss-120b'];
   const history=followup === 'routing' ? [{role:'user',text:'How do you manage on-call rotations?'},{role:'assistant',text:'Schedule primary and backup engineers, arrange handoffs, and define escalation rules.'}] : [{role:'user',text:'What is a Kubernetes cluster?'},{role:'assistant',text:'A cluster is a group of machines with a control plane and worker nodes.'}];
   const started=performance.now();let first=null;let answer='';const events=[];
   const response=await fetch(`${API_BASE}/stream-recover`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${localStorage.getItem('ainotetaker_auth_token')}`},body:JSON.stringify({query:prompt,candidates,image_b64:image,mode:'instant',style:'detailed',messages:history})});
   if(!response.ok)return {status:response.status};
   const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
   while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop();for(const line of lines){if(!line.startsWith('data:'))continue;try{const e=JSON.parse(line.slice(5));if(e.content){first??=performance.now()-started;answer+=e.content;}if(['done','error','recovery'].includes(e.type))events.push(e);}catch{}}}
   return {candidates,firstTextMs:Math.round(first),totalMs:Math.round(performance.now()-started),answer,events,immediateRendering:!setBubbleText.toString().includes('setTimeout')};
 },process.argv.includes('--routing') ? 'routing' : process.argv.includes('--followup'));
 fs.writeFileSync('/tmp/ant-response-depth.json',JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));
}finally{await browser.close();}
