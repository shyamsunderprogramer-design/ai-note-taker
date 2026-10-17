const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,'../../apps/web/app.js'),'utf8');
const start = source.indexOf('function getContextMessages()');
const end = source.indexOf('\nfunction setProcessingUI(',start);
function select(messages,budget,turns=10) {
  const scope = {currentMessages:messages,getSelectedContextLength:()=>turns,getSelectedTokenLimit:()=>budget,estimateTokens:text=>text.split(' ').length,tokenCounter:null};
  return JSON.parse(JSON.stringify(vm.runInNewContext(source.slice(start,end)+'\ngetContextMessages()',scope)));
}
test('latest correction survives when older context fills the budget',()=>{
  const old={role:'user',text:'The deadline is Friday and Maya owns this entire project'};
  const reply={role:'assistant',text:'Understood Friday'};
  const correction={role:'user',text:'Correction deadline Tuesday'};
  assert.deepEqual(select([old,reply,correction],5),[reply,correction]);
});
test('selected turns remain in chronological order',()=>{
  const messages=[{role:'user',text:'First'},{role:'assistant',text:'Second'},{role:'user',text:'Third'}];
  assert.deepEqual(select(messages,20),messages);
  assert.equal(select(messages,20,0),null);
});
