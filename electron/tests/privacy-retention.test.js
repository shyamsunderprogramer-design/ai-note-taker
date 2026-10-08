const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path')
const source=fs.readFileSync(path.join(__dirname,'../../apps/web/app.js'),'utf8')
function setup(privateSession,load=async()=>null){
 const saved=[];const scope=vm.createContext({window:{privateHistorySession:privateSession,api:{conversationLoad:load,conversationSave:async c=>{saved.push(c);return {...c,id:'saved'}}}},
  currentMessages:[{role:'user',text:'Sensitive private question'}],currentConversationId:'old',generateTitle:()=>'',getSelectedMode:()=>'',autoSSBtn:null,alwaysOnActive:false,
  ingestConversationToGraph:()=>{},console,Date})
 vm.runInContext(source.slice(source.indexOf('async function saveCurrentConversation()'),source.indexOf('async function ingestConversationToGraph')),scope)
 return {scope,saved}
}
test('private conversations never reach disk save or graph ingestion',async()=>{
 const s=setup(true);await s.scope.saveCurrentConversation();assert.equal(s.saved.length,0)
})
test('a privacy change during an asynchronous history read still blocks persistence',async()=>{
 let finish;const s=setup(false,()=>new Promise(r=>finish=r))
 const saving=s.scope.saveCurrentConversation();s.scope.window.privateHistorySession=true;finish(null)
 await saving;assert.equal(s.saved.length,0)
})
test('leaving a private conversation starts fresh instead of saving its contents',()=>{
 let callback;const messages=['private content'];const input={checked:false,addEventListener:(_,f)=>callback=f}
 const scope=vm.createContext({window:{},document:{getElementById:()=>input},startNewConversation:()=>messages.splice(0)})
 vm.runInContext(source.slice(source.indexOf('// Private chat retention'),source.indexOf('// Screenshot capture toggle')),scope)
 input.checked=true;callback();messages.push('private content');input.checked=false;callback()
 assert.equal(scope.window.privateHistorySession,false);assert.deepEqual(messages,[])
})
