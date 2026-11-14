const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {envPath, updateProviderEnv} = require('../lib/provider-env');
function profile(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(),'ant-provider-env-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true})); return directory;
}
test('private local env preserves other keys, replaces duplicates, quotes literals, and removes only the selected key', t => {
  const dir=profile(t), filename=envPath(dir), key='test#key"with\\literal${HOME}';
  updateProviderEnv(dir,'GROQ_API_KEY','old-testing-key');
  fs.appendFileSync(filename,'# unrelated comment\nOPENAI_API_KEY="another-testing-key"\nexport GROQ_API_KEY=duplicate\n');
  assert.equal(updateProviderEnv(dir,'GROQ_API_KEY',key),filename);
  const text=fs.readFileSync(filename,'utf8');
  assert.equal(text.match(/GROQ_API_KEY/g).length,1);
  assert.ok(text.includes(`GROQ_API_KEY=${JSON.stringify(key)}`));
  assert.ok(text.includes('# unrelated comment'));
  if(process.platform!=='win32') assert.equal(fs.statSync(filename).mode & 0o777,0o600);
  updateProviderEnv(dir,'GROQ_API_KEY',null);
  assert.ok(!fs.readFileSync(filename,'utf8').includes('GROQ_API_KEY'));
  assert.ok(fs.readFileSync(filename,'utf8').includes('OPENAI_API_KEY'));
});
test('invalid credentials and settings cannot inject env entries; missing-file removal creates nothing', t=> {
  const dir=profile(t);
  for(const value of ['short','test-key\nOTHER=value','key with spaces','x'.repeat(4097)]) assert.throws(()=>updateProviderEnv(dir,'GROQ_API_KEY',value));
  assert.throws(()=>updateProviderEnv(dir,'JWT_SECRET_KEY','testing-value'));
  updateProviderEnv(dir,'GROQ_API_KEY',null);
  assert.equal(fs.existsSync(envPath(dir)),false);
});
test('symlinked or oversized files fail without touching another file', t=> {
  const dir=profile(t), filename=envPath(dir), target=path.join(dir,'unrelated');
  fs.mkdirSync(path.dirname(filename));fs.writeFileSync(target,'original');fs.symlinkSync(target,filename);
  assert.throws(()=>updateProviderEnv(dir,'GROQ_API_KEY','test-provider-key'));
  assert.equal(fs.readFileSync(target,'utf8'),'original');fs.unlinkSync(filename);
  fs.writeFileSync(filename,'x'.repeat(129*1024));
  assert.throws(()=>updateProviderEnv(dir,'GROQ_API_KEY','test-provider-key'));
});
