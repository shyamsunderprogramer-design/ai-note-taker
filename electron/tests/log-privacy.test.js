const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path')
const {redact}=require('../lib/log-redaction')
function load(diagnostics,packaged){
 let dirs=0;const log={initialize(){},hooks:[],transports:{file:{},console:{}}};const module={exports:{}}
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../lib/logger.js'),'utf8'),{module,process:{env:diagnostics?{ANT_DIAGNOSTICS:'1'}:{}},
 require:name=>name==='electron-log/main'?log:name==='electron'?{app:{isPackaged:packaged,getPath:()=>'/profile'}}:name==='fs'?{mkdirSync:()=>dirs++}:name==='./log-redaction'?{redact}:require(name)})
 module.exports.configureBackendCrashLog();return {log,dirs}
}
test('normal dev and packaged launches never enable diagnostic file transport',()=>{
 for(const packaged of [false,true]){const {log,dirs}=load(false,packaged);assert.equal(log.transports.file.level,false);assert.equal(dirs,0)}
})
test('explicit diagnostics remain bounded and redact credentials before all transports',()=>{
 const {log,dirs}=load(true,true);assert.equal(log.transports.file.level,'error');assert.equal(dirs,1)
 const data=log.hooks[0]({data:['/ws/transcribe?token=private-token&source=system',{password:'private-password',authorization:'Bearer private-key'}]}).data
 assert.ok(!JSON.stringify(data).includes('private-token'));assert.ok(!JSON.stringify(data).includes('private-password'));assert.ok(!JSON.stringify(data).includes('private-key'))
 assert.equal(log.transports.file.maxSize,100*1024)
})
test('serialized credentials and JWTs are redacted without removing status details',()=>{
 const value=redact('HTTP 401 {"api_key":"private-key"} Bearer private-token eyJheader.payload.signature')
 assert.ok(value.includes('HTTP 401'));assert.ok(!value.includes('private-key'));assert.ok(!value.includes('private-token'));assert.ok(!value.includes('eyJheader'))
})
