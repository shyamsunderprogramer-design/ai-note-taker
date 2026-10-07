const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../apps/web/app.js'),'utf8');
test('panel follow-up cancels a pending answer and carries its question into the continuation',async()=>{
 const answers=[];let aborted=false,finished
 const busy={userQuestion:'How would you roll back a Kubernetes deployment?',controller:{abort(){aborted=true}},finish:status=>finished=status}
 const scope=vm.createContext({Promise,Set,setTimeout,Date,activeQuestion:busy,latestBotMessage:null,
 window:{unifiedSessionActive:true,liveSessionContext:{needsScreen:()=>false}},setProcessingUI(){},
 getQuestionScreenContext:()=>{throw Error('Unrelated OCR')},
 submitText:async(text,options)=>answers.push({text,options}),addErrorMessage:error=>{throw Error(error)}})
 vm.runInContext(source.slice(source.indexOf('let interviewQueueEpoch ='),source.indexOf('// Always-on mic toggle')),scope)
 await scope.queueInterviewQuestion({question:'What if the database migration cannot be reversed?',session_id:'remote',answer_id:2,prepared:true})
 assert.ok(aborted)
 assert.equal(finished,'Updated for panel follow-up')
 assert.equal(answers.length,1)
 assert.equal(answers[0].options.followupOf,busy.userQuestion)
 assert.match(answers[0].text,/database migration/)
})
test('general live question does not wait for unrelated OCR',async()=>{
 const answers=[];const scope=vm.createContext({Promise,Set,setTimeout,Date,activeQuestion:null,
 window:{unifiedSessionActive:true,liveSessionContext:{needsScreen:()=>false}},
 getQuestionScreenContext:()=>{throw Error('Unrelated OCR must be skipped')},
 submitText:async text=>answers.push(text),addErrorMessage:error=>{throw Error(error)}});
 vm.runInContext(source.slice(source.indexOf('let interviewQueueEpoch ='),source.indexOf('// Always-on mic toggle')),scope);
 await scope.queueInterviewQuestion({question:'How do you prevent this problem with Terraform?',session_id:'s',answer_id:1,prepared:true});
 assert.equal(answers.length,1);
});
test('spoken questions capture immediately, wait for ongoing answer, preserve order and deduplicate events',async()=>{
 const captures=[],answers=[];const busy={};const scope=vm.createContext({Promise,Set,setTimeout,Date,activeQuestion:busy,
 getQuestionScreenContext:async(_,force)=>{assert.equal(force,false);const context={image:'screen-'+captures.length};captures.push(context);return context},
 submitText:async(text,opts)=>answers.push({text,image:opts.screenContext.image}),addErrorMessage:e=>{throw Error(e)}});
 vm.runInContext(source.slice(source.indexOf('let interviewQueueEpoch ='),source.indexOf('// Always-on mic toggle')),scope);
 const a=scope.queueInterviewQuestion({question:'Complete this function',session_id:'s',answer_id:1});
 const b=scope.queueInterviewQuestion({question:'Why that approach?',session_id:'s',answer_id:2});
 scope.queueInterviewQuestion({question:'Complete this function',session_id:'s',answer_id:1});
 assert.equal(captures.length,2);await new Promise(r=>setTimeout(r,10));assert.equal(answers.length,0);
 scope.activeQuestion=null;await Promise.all([a,b]);assert.deepEqual(answers,[{text:'Complete this function',image:'screen-0'},{text:'Why that approach?',image:'screen-1'}]);
});
test('continuous spoken question works with screen context disabled',async()=>{
 const answers=[]; const scope=vm.createContext({Promise,Set,setTimeout,Date,activeQuestion:null,
 getQuestionScreenContext:async(_,force)=>{assert.equal(force,false);return {image:null,text:null}},
 submitText:async text=>answers.push(text),addErrorMessage:error=>{throw Error(error)}});
 vm.runInContext(source.slice(source.indexOf('let interviewQueueEpoch ='),source.indexOf('// Always-on mic toggle')),scope);
 await scope.queueInterviewQuestion({question:'How would you handle a disagreement?',session_id:'s',answer_id:1});
 assert.deepEqual(answers,['How would you handle a disagreement?']);
});
test('explicit spoken screen question still requires a successful capture',async()=>{
 const errors=[]; const scope=vm.createContext({Promise,Set,setTimeout,Date,activeQuestion:null,
 getQuestionScreenContext:async(_,force)=>{assert.equal(force,true);return {image:null,text:null}},
 submitText:async()=>{throw Error('Must not invent screen context')},addErrorMessage:error=>errors.push(error)});
 vm.runInContext(source.slice(source.indexOf('let interviewQueueEpoch ='),source.indexOf('// Always-on mic toggle')),scope);
 await scope.queueInterviewQuestion({question:'Explain the question on screen',session_id:'s',answer_id:1});
 assert.equal(errors.length,1);assert.match(errors[0],/Cannot see the screen/);
});
test('compact IPC shrinks and restores bounds without changing recording or chat',()=>{
 const main=fs.readFileSync(path.join(__dirname,'../main.js'),'utf8');let handler;let bounds={width:960,height:720};let min;
 const win={webContents:{},getBounds:()=>({...bounds}),isMaximized:()=>false,setMinimumSize:(w,h)=>min=[w,h],setSize:(w,h)=>bounds={width:w,height:h}};
 const scope=vm.createContext({win,MIN_WIDTH:640,MIN_HEIGHT:600,conversationExpandedBounds:null,ipcMain:{handle:(name,fn)=>handler=fn}});
 vm.runInContext(main.slice(main.indexOf('ipcMain.handle("window:conversation-collapsed"'),main.indexOf('ipcMain.handle("window:resize"')),scope);
 handler({sender:win.webContents},true,380);assert.deepEqual(bounds,{width:960,height:380});assert.equal(min[1],240);
 handler({sender:win.webContents},true,390);handler({sender:win.webContents},false);assert.deepEqual(bounds,{width:960,height:720});assert.equal(min[1],600);
});
