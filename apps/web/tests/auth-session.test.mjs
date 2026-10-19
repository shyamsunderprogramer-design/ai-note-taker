import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../js/core/auth-helper.js', import.meta.url), 'utf8');
function storage() {
  const values = new Map();
  return {getItem:k=>values.get(k) ?? null, setItem:(k,v)=>values.set(k,String(v)), removeItem:k=>values.delete(k)};
}
function setup({local=storage(), session=storage(), fetch=async()=>new Response('{}')}={}) {
  const window = {location:{href:'https://ant.test/signin.html',pathname:'/signin.html'}, fetch, dispatchEvent(){}};
  const context = vm.createContext({window, localStorage:local, sessionStorage:session,
    document:{addEventListener(){}}, Request, Response, Headers, URL, FormData, AbortSignal, Event, console});
  vm.runInContext(source, context);
  return {auth:window.AuthHelper, window, local, session};
}
const pair = {access_token:'access-one',refresh_token:'refresh-one',expires_in:86400};
const json = (body,status=200) => new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});

test('Remember me survives a fresh browser context; unchecked sessions do not', async()=>{
  for(const remember of [true,false]) {
    const s=setup({fetch:async()=>json(pair)});
    await s.auth.login('test-user','test-password',remember);
    assert.equal(s.auth.getToken(),'access-one');
    assert.equal(setup({local:s.local}).auth.getToken(),remember?'access-one':null);
    const saved=JSON.parse((remember?s.local:s.session).getItem(s.auth.SESSION_KEY));
    assert.equal(saved.remember,remember);
    assert.equal('password' in saved,false);
    assert.equal(saved.refresh_token,'refresh-one');
  }
});
test('unchecked login replaces a previously remembered login',async()=>{
  const s=setup({fetch:async()=>json(pair)});
  await s.auth.login('test','password',true);
  await s.auth.login('test','password',false);
  assert.equal(s.local.getItem(s.auth.SESSION_KEY),null);
  assert.equal(s.auth.getToken(),'access-one');
});
test('legacy tokens do not imply consent to a remembered session',()=>{
  const local=storage();local.setItem('ainotetaker_auth_token','legacy');
  local.setItem('ainotetaker_remember_user','test');
  const s=setup({local});assert.equal(s.auth.getToken(),null);
  assert.equal(local.getItem('ainotetaker_auth_token'),null);
});
test('concurrent unauthorized requests share renewal and retry with the new token',async()=>{
  let refreshes=0;
  const s=setup({fetch:async req=>{
    const url=typeof req==='string'?req:req.url;
    if(url.endsWith('/auth/refresh')) {refreshes++;await new Promise(r=>setTimeout(r,5));return json({access_token:'access-two',expires_in:86400});}
    return req.headers.get('Authorization')==='Bearer access-two'?json({ok:true}):json({},401);
  }});
  s.auth.setSession(pair,true);
  const responses=await Promise.all([s.auth.request('http://127.0.0.1:8000/auth/me'),s.auth.request('http://127.0.0.1:8000/auth/me')]);
  assert.deepEqual(responses.map(r=>r.status),[200,200]);assert.equal(refreshes,1);
  assert.equal(s.auth.getSession().remember,true);
});
test('refresh token rejection clears the session instead of looping',async()=>{
  let count=0;
  const s=setup({fetch:async()=>{count++;return json({},401)}});s.auth.setSession(pair,true);
  assert.equal((await s.auth.request('http://127.0.0.1:8000/auth/me')).status,401);
  assert.equal(count,2);assert.equal(s.auth.getToken(),null);
});
test('offline renewal preserves the remembered session for retry',async()=>{
  const s=setup({fetch:async()=>{throw Error('offline')}});
  s.auth.setSession({...pair,expires_at:1},true);
  await assert.rejects(s.auth.getValidToken(),/reach the ANT backend/);
  assert.equal(s.auth.getToken(),'access-one');
  assert.equal(await s.auth.isAuthRequired(),true);
});
test('a rejected proactive renewal returns the user to sign-in',async()=>{
  let prompts=0;
  const s=setup({fetch:async()=>json({},401)});
  s.auth.showLoginOverlay=()=>{prompts++};
  s.auth.setSession({...pair,expires_at:1},true);
  assert.equal((await s.auth.request('http://127.0.0.1:8000/auth/me')).status,401);
  assert.equal(s.auth.getToken(),null);assert.equal(prompts,1);
  await s.auth.request('http://127.0.0.1:8000/auth/me');
  assert.equal(prompts,1,'anonymous requests must not repeatedly prompt');
});
test('a delayed refresh cannot restore a signed-out or replaced session',async()=>{
  for(const replacement of [null,{...pair,access_token:'different-access',refresh_token:'different-refresh'}]) {
    let complete;
    const s=setup({fetch:()=>new Promise(r=>{complete=r})});s.auth.setSession(pair,true);
    const renewal=s.auth.refreshSession();
    s.auth.clearToken();if(replacement)s.auth.setSession(replacement,false);
    complete(json({access_token:'old-session-renewed',expires_in:86400}));
    assert.equal(await renewal,false);assert.equal(s.auth.getToken(),replacement?.access_token||null);
  }
});
test('logout clears persistent storage and invokes server revocation',async()=>{
  const calls=[];const s=setup({fetch:async(url,opts)=>{calls.push({url,opts});return json({})}});
  s.auth.setSession(pair,true);await s.auth.logout();
  assert.equal(s.auth.getToken(),null);assert.equal(calls[0].url,'http://127.0.0.1:8000/auth/logout');
  assert.equal(calls[0].opts.headers.Authorization,'Bearer access-one');
});
test('token injection uses the exact API origin, never a hostname substring',async()=>{
  const calls=[];const s=setup({fetch:async(...args)=>{calls.push(args);return json({})}});s.auth.setSession(pair);
  await s.auth.request('https://example.test/127.0.0.1:8000');
  assert.equal(calls[0][1].headers,undefined);
  assert.equal(s.auth.isApiUrl('http://127.0.0.1:80000/path'),false);
});
