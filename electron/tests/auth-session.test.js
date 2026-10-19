const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {pathToFileURL} = require('node:url');
const {backendSigningSecret, createAuthSessionStore, createSessionRefresher, isAppFrame} = require('../lib/auth-session');

function fixture(t) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'ant-session-test-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const safeStorage={isEncryptionAvailable:()=>true,getSelectedStorageBackend:()=> 'gnome_libsecret',encryptString:s=>Buffer.from(s).map(b=>b^0x5a),decryptString:b=>Buffer.from(b.map(v=>v^0x5a)).toString()};
  return {directory,safeStorage};
}
const session={access_token:'test-access',refresh_token:'test-refresh',expires_at:123456789,remember:true};
test('desktop checked sessions survive restart, unchecked sessions are only in memory',t=>{
  const f=fixture(t);const first=createAuthSessionStore(f);first.set(session);
  assert.ok(!fs.readFileSync(path.join(f.directory,'remembered-session.bin')).includes('test-access'));
  const second=createAuthSessionStore(f);assert.deepEqual(second.get(),session);
  second.set({...session,remember:false});assert.equal(second.get().access_token,'test-access');
  assert.equal(createAuthSessionStore(f).get(),null);
});
test('clearing a desktop session prevents restoration by a new process',t=>{
  const f=fixture(t);const store=createAuthSessionStore(f);store.set(session);store.clear();
  assert.equal(store.get(),null);assert.equal(createAuthSessionStore(f).get(),null);
});
test('missing secure storage rejects persistence but still permits a session login',t=>{
  const f=fixture(t);f.safeStorage.isEncryptionAvailable=()=>false;
  const store=createAuthSessionStore(f);assert.throws(()=>store.set(session),/Secure storage/);
  store.set({...session,remember:false});assert.equal(store.get().access_token,'test-access');
});
test('Linux basic_text is not accepted as protected persistence',t=>{
  const f=fixture(t);f.platform='linux';f.safeStorage.getSelectedStorageBackend=()=> 'basic_text';
  assert.throws(()=>createAuthSessionStore(f).set(session),/Secure storage/);
});
test('a temporarily unavailable keychain does not discard a remembered session',t=>{
  const f=fixture(t);createAuthSessionStore(f).set(session);
  f.safeStorage.isEncryptionAvailable=()=>false;const store=createAuthSessionStore(f);
  assert.throws(()=>store.get(),/Unlock/);f.safeStorage.isEncryptionAvailable=()=>true;
  assert.deepEqual(store.get(),session);
});
test('backend signing key persists across instances, honors configuration and rejects corruption',t=>{
  const f=fixture(t);const key=backendSigningSecret(f.directory);
  assert.match(key,/^[a-f0-9]{64}$/);assert.equal(backendSigningSecret(f.directory),key);
  assert.equal(backendSigningSecret(f.directory,'configured-secret'),'configured-secret');
  if(process.platform!=='win32')assert.equal(fs.statSync(path.join(f.directory,'jwt-secret')).mode&0o777,0o600);
  fs.writeFileSync(path.join(f.directory,'jwt-secret'),'broken');
  assert.throws(()=>backendSigningSecret(f.directory),/Invalid saved/);
});
test('authentication IPC only accepts the main frame of a bundled app page',()=>{
  const root=path.resolve('/tmp/renderer');
  const event=url=>{const mainFrame={url};return {senderFrame:mainFrame,sender:{mainFrame}}};
  assert.equal(isAppFrame(event(pathToFileURL(path.join(root,'index.html')).href),root),true);
  assert.equal(isAppFrame(event('https://example.test/index.html'),root),false);
  assert.equal(isAppFrame(event(pathToFileURL(path.join(root,'../other.html')).href),root),false);
  const child=event(pathToFileURL(path.join(root,'index.html')).href);child.senderFrame={...child.senderFrame};
  assert.equal(isAppFrame(child,root),false);
});
test('desktop windows share one renewal and preserve the persistence choice',async t=>{
  const store=createAuthSessionStore(fixture(t));store.set({...session,remember:false});
  let calls=0;
  const refresh=createSessionRefresher(store,async(url,options)=>{
    calls++;assert.equal(url,'http://127.0.0.1:8000/auth/refresh');
    assert.equal(options.body.get('refresh_token'),session.refresh_token);
    await new Promise(resolve=>setTimeout(resolve,5));
    return Response.json({access_token:'renewed',expires_in:86400});
  });
  assert.deepEqual(await Promise.all([refresh(),refresh()]),[true,true]);
  assert.equal(calls,1);assert.equal(store.get().access_token,'renewed');
  assert.equal(store.get().remember,false);
});
test('desktop renewal cannot restore a signed-out session',async t=>{
  const store=createAuthSessionStore(fixture(t));store.set(session);
  let complete;
  const refresh=createSessionRefresher(store,()=>new Promise(resolve=>{complete=resolve}));
  const pending=refresh();store.clear();complete(Response.json({access_token:'renewed'}));
  assert.equal(await pending,false);assert.equal(store.get(),null);
});
test('desktop renewal retains credentials when offline but clears revoked sessions',async t=>{
  const store=createAuthSessionStore(fixture(t));store.set(session);
  await assert.rejects(createSessionRefresher(store,async()=>{throw Error('offline')})(),/reach the ANT backend/);
  assert.deepEqual(store.get(),session);
  assert.equal(await createSessionRefresher(store,async()=>new Response('',{status:401}))(),false);
  assert.equal(store.get(),null);
});
