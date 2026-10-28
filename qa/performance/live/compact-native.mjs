import {_electron as electron} from '@playwright/test';
import {mkdtemp,writeFile,readFile,mkdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';import {resolve,join} from 'node:path';import assert from 'node:assert/strict';
const dir=await mkdtemp(join(tmpdir(),'ant-compact-'));const out=resolve('qa/performance/results/2026-10-04-two-tasks');await mkdir(out,{recursive:true});
const source=await readFile('electron/main.js','utf8');const handler=source.slice(source.indexOf('ipcMain.handle("window:conversation-collapsed"'),source.indexOf('ipcMain.handle("window:resize"'));
await writeFile(join(dir,'preload.cjs'),`const {contextBridge,ipcRenderer}=require('electron');contextBridge.exposeInMainWorld('api',{setConversationCollapsed:(...args)=>ipcRenderer.invoke('window:conversation-collapsed',...args)});`);
await writeFile(join(dir,'main.cjs'),`const {app,BrowserWindow,ipcMain}=require('electron');let win;let conversationExpandedBounds=null;const MIN_WIDTH=640,MIN_HEIGHT=600;${handler}\napp.whenReady().then(()=>{win=new BrowserWindow({width:960,height:720,minWidth:640,minHeight:600,webPreferences:{preload:${JSON.stringify(join(dir,'preload.cjs'))}}});win.loadURL('about:blank')});`);
const app=await electron.launch({args:[join(dir,'main.cjs')]});
try{
 const page=await app.firstWindow();await page.setContent('<style>body{margin:0}header{height:160px}#conversationPanel[hidden]{display:none}</style><div id="settingsPanel"></div><div id="historyPanel"></div><header>ANT compact window test — listening stays active</header><button id="conversationToggle" aria-expanded="true">Hide conversation</button><div id="conversationPanel"><p>Preserved answer</p></div>');
 await page.addScriptTag({content:await readFile('apps/web/js/conversation-panel.js','utf8')});
 const initial=await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].getSize());
 await page.locator('#conversationToggle').click();await page.waitForFunction(()=>innerHeight<400);
 const compact=await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].getSize());assert.ok(compact[1]<initial[1]);
 await page.screenshot({path:join(out,'native-compact.png')});
 await page.evaluate(()=>document.getElementById('settingsPanel').classList.add('open'));
 await page.waitForFunction(()=>innerHeight>=600);
 assert.equal(await page.locator('#conversationPanel').isVisible(),false);
 await page.evaluate(()=>document.getElementById('settingsPanel').classList.remove('open'));
 await page.waitForFunction(()=>innerHeight<400);

 await page.evaluate(()=>document.getElementById('historyPanel').classList.add('open'));
 await page.waitForFunction(()=>innerHeight>=600);
 assert.equal(await page.locator('#conversationPanel').isVisible(),false);
 await page.evaluate(()=>document.getElementById('historyPanel').classList.remove('open'));
 await page.waitForFunction(()=>innerHeight<400);
 await page.evaluate(()=>document.dispatchEvent(new Event('ant:conversation-opened')));
 await page.waitForFunction(()=>innerHeight>=600);
 assert.equal(await page.locator('#conversationPanel').isVisible(),true);

 const restored=await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].getSize());assert.deepEqual(restored,initial);
 assert.equal(await page.locator('#conversationPanel').innerText(),'Preserved answer');
 await writeFile(join(out,'native-size.json'),JSON.stringify({initial,compact,restored},null,2));console.log(JSON.stringify({passed:true,initial,compact,restored}));
}finally{await app.close()}
