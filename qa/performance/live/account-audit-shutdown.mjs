// Quit the audit instance through its main-process inspector, preserving cleanup.
const port = Number(process.argv[2]);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Specify audit inspector port');
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const socket = new WebSocket(targets[0].webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
socket.addEventListener('message',event=>{const result=JSON.parse(event.data);if(result.result?.exceptionDetails)console.error(JSON.stringify(result.result.exceptionDetails));});
socket.send(JSON.stringify({id:1,method:'Runtime.evaluate',params:{expression:"process.mainModule.require('electron').app.isQuitting = true; process.mainModule.require('electron').app.quit()"}}));
await new Promise(resolve=>{socket.addEventListener('close',resolve,{once:true});setTimeout(resolve,3000);});
socket.close();
