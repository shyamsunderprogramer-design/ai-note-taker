// Isolated provider probe: actual selected ChatGPT account, synthetic text only.
// Close the normal app first: this probe may renew its encrypted account token.
// Does not change provider/model preferences or send user context.
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process');
(async()=>{
 const root=path.resolve(__dirname,'../../..');
 const output=await fs.mkdtemp(path.join(os.tmpdir(),'ant-subscription-latency-'));
 await fs.writeFile(path.join(output,'package.json'),JSON.stringify({name:'ai-note-taker',main:'main.cjs'}));
 await fs.writeFile(path.join(output,'main.cjs'),`
 const {app,safeStorage}=require('electron'),fs=require('node:fs'),path=require('node:path');
 app.setPath('userData',${JSON.stringify(path.join(output,'profile'))});
 app.whenReady().then(async()=>{
  try {
   const {createVault,createSubscriptionAuth,RESOURCE}=require(${JSON.stringify(path.join(root,'electron/lib/subscription-auth'))});
   const {createSubscriptionService}=require(${JSON.stringify(path.join(root,'electron/lib/subscriptions'))});
   const directory=path.join(app.getPath('appData'),'ai-note-taker','ai-note-taker-data','auth');
   if(!fs.existsSync(path.join(directory,'subscriptions.bin')))throw Error('No existing account storage');
   const vault=createVault(directory,safeStorage),data=vault.get(),account=data.accounts.find(a=>a.id===data.active);
   if(!account?.access_token)throw Error('Connect ChatGPT in the normal app before probing');
   const auth=createSubscriptionAuth({vault});
   let variant='default',row,selected;
   const service=createSubscriptionService({auth,fetch:async(url,options)=>{
    if(url.endsWith('/responses')) {
     const body=JSON.parse(options.body);
     if(variant!=='default')body.reasoning={effort:variant};
     options={...options,body:JSON.stringify(body)};
     row.requestMs=performance.now()-row.started;
    }
    const response=await fetch(url,options);
    if(url.endsWith('/models')) {
     const catalog=await response.clone().json();
     selected=catalog.models.find(m=>m.slug===account.model)||catalog.models.find(m=>m.visibility==='list');
     console.log(JSON.stringify({selectedModel:selected?.slug,modelMetadata:Object.fromEntries(Object.entries(selected||{}).filter(([key])=>/reason|effort|default|supported|latency/.test(key)))}));
    } else if(url.endsWith('/responses'))row.headersMs=performance.now()-row.started;
    return response;
   }});
   await service.models();
   const rows=[];
   for(const effort of ['default','low']) {
    variant=effort;row={effort,started:performance.now(),firstTextMs:null,answer:''};
    try { await service.stream({query:'What is 2 + 2? Answer briefly.',messages:[]},event=>{
     if(event.type==='chunk'){if(row.firstTextMs===null)row.firstTextMs=performance.now()-row.started;row.answer+=event.content}
    },AbortSignal.timeout(45000)); }catch(error){row.error=error.message}
    row.completeMs=performance.now()-row.started;delete row.started;rows.push(row);console.log(JSON.stringify(row));
   }
   fs.writeFileSync(${JSON.stringify(path.join(output,'results.json'))},JSON.stringify(rows,null,2));
  }catch(error){console.error(error.message);process.exitCode=1}finally{app.exit(process.exitCode||0)}
 });
 `);
 const child=spawn(require('electron'),[output],{stdio:'inherit'});
 child.on('exit',code=>{console.log('Artifacts: '+output);process.exitCode=code||0});
})().catch(e=>{console.error(e.message);process.exitCode=1});
