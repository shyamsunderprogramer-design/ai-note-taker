const {test}=require('node:test'),assert=require('node:assert/strict')
const {configureRuntimePrivacy}=require('../lib/runtime-privacy')
for(const packaged of [false,true])test(`normal launch disables debugging (packaged=${packaged})`,()=>{
 const removed=[];let closed=false
 const app={isPackaged:packaged,commandLine:{removeSwitch:v=>removed.push(v)}}
 assert.equal(configureRuntimePrivacy({app,env:{},inspector:{close:()=>closed=true}}).localQA,false)
 assert.ok(removed.includes('remote-debugging-port'));assert.ok(removed.includes('remote-debugging-pipe'));assert.ok(closed)
})
test('explicit local QA binds debugging to loopback; packaged builds ignore QA opt-in',()=>{
 const flags=[];const app={isPackaged:false,commandLine:{appendSwitch:(...args)=>flags.push(args),removeSwitch:()=>{}}}
 assert.equal(configureRuntimePrivacy({app,env:{ANT_ENABLE_LOCAL_QA:'1'}}).localQA,true)
 assert.deepEqual(flags,[['remote-debugging-address','127.0.0.1']])
 app.isPackaged=true
 assert.equal(configureRuntimePrivacy({app,env:{ANT_ENABLE_LOCAL_QA:'1'}}).localQA,false)
})
