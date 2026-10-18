const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

test('desktop API calls renew an expired login before attaching authorization',async()=>{
  let api, renewals=0;
  let session={access_token:'expired',refresh_token:'refresh',expires_at:1};
  const calls=[];
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../preload.js'),'utf8'),{
    window:{},console,Date,
    require:name=>{
      assert.equal(name,'electron');
      return {contextBridge:{exposeInMainWorld:(name,value)=>{api=value}},
        ipcRenderer:{
          sendSync:()=>({value:session}),
          invoke:async channel=>{
            assert.equal(channel,'auth:session:refresh');renewals++;
            session={...session,access_token:'renewed',expires_at:Date.now()+86400000};
            return {value:true};
          },
        }};
    },
    fetch:async(url,options)=>{calls.push({url,options});return Response.json({ok:true})},
  });
  await api.setMode('fast');
  await api.exportConversation({messages:[]});
  assert.equal(renewals,1);
  assert.ok(calls.every(call=>call.options.headers.Authorization==='Bearer renewed'));
  assert.equal(calls[1].options.headers['Content-Type'],'application/json');
});
