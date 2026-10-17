const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../../apps/web/app.js'),'utf8');
test('received answer is displayed immediately without word timers',()=>{
 const rendered=[];const scope={renderBubbleText:(...args)=>rendered.push(args),clearTimeout:()=>{}};
 vm.runInNewContext(source.slice(source.indexOf('function setBubbleText('),source.indexOf('function renderBubbleText(')),scope);
 const bubble={};const text='A complete answer. '.repeat(200);
 scope.setBubbleText(bubble,text,true);assert.equal(rendered[0][1],text);
 scope.setBubbleText(bubble,text,false);assert.equal(rendered[1][2],false);
});
