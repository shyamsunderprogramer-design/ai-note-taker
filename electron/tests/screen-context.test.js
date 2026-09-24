const {test}=require('node:test');
const assert=require('node:assert/strict');
const {createScreenCapture}=require('../lib/screen-context');
test('all visible app windows are hidden during capture and restored on failure',async()=>{
 const windows=[true,false].map(focused=>({visible:true,isDestroyed:()=>false,isVisible(){return this.visible},isFocused:()=>focused,hide(){this.visible=false},showInactive(){this.visible=true},focus(){this.focused=true}}));
 const capture=createScreenCapture({BrowserWindow:{getAllWindows:()=>windows},screen:{getCursorScreenPoint:()=>({x:0,y:0}),getDisplayNearestPoint:()=>({id:2})},delay:async()=>{},desktopCapturer:{getSources:async()=>{assert.ok(windows.every(w=>!w.visible));throw Error('capture failure')}}});
 await assert.rejects(capture(),/capture failure/);assert.ok(windows.every(w=>w.visible));assert.ok(windows[0].focused);
});
test('captures the pointer display and serializes simultaneous requests',async()=>{
 let active=0;
 const capture=createScreenCapture({BrowserWindow:{getAllWindows:()=>[]},screen:{getCursorScreenPoint:()=>({x:0,y:0}),getDisplayNearestPoint:()=>({id:2})},delay:async()=>{},desktopCapturer:{getSources:async()=>{assert.equal(++active,1);await new Promise(r=>setTimeout(r,2));active--;return [1,2].map(id=>({display_id:String(id),thumbnail:{isEmpty:()=>false,toJPEG:()=>Buffer.from(String(id))}}))}}});
 assert.deepEqual(await Promise.all([capture(),capture()]),['Mg==','Mg==']);
});
test('native exclusion captures without hiding windows or changing focus',async()=>{
 const capture=createScreenCapture({BrowserWindow:{getAllWindows:()=>{throw Error('Must not touch window visibility')}},screen:{getCursorScreenPoint:()=>({x:0,y:0}),getDisplayNearestPoint:()=>({id:7})},nativeCapture:async id=>{assert.equal(id,7);return 'native-image'}});
 assert.equal(await capture(),'native-image');
});
test('native failure does not fall back to blinking hide/show capture',async()=>{
 const capture=createScreenCapture({BrowserWindow:{getAllWindows:()=>{throw Error('Must not hide windows')}},screen:{getCursorScreenPoint:()=>({x:0,y:0}),getDisplayNearestPoint:()=>({id:7})},nativeCapture:async()=>{throw Error('Screen permission unavailable')}});
 await assert.rejects(capture(),/Screen permission unavailable/);
});
