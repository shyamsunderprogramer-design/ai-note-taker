const test = require('node:test')
const assert = require('node:assert/strict')
const vm = require('node:vm')
const fs = require('node:fs')
const path = require('node:path')

function loadStealth(platform = 'darwin') {
  const noop = () => {}
  const electron = {
    app: {}, Menu: { buildFromTemplate: () => [] },
    nativeImage: { createFromBuffer: () => ({}) },
    Tray: class { setToolTip() {} setContextMenu() {} on() {} destroy() {} },
  }
  const module = { exports: {} }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../stealth.js'), 'utf8'), {
    module, Buffer, process: { platform }, __dirname,
    require: name => name === 'electron' ? electron : name === 'electron-log/main' ? {info:noop,warn:noop,error:noop} : require(name),
  })
  return module.exports
}

test('capture protection toggles both directions and reports failures', () => {
  const stealth = loadStealth()
  let fail = false
  let protectedState = false
  const calls = []
  const noop = () => {}
  stealth.init({ hide:noop, isDestroyed:()=>false, setAlwaysOnTop:noop, setOpacity:noop,
    show:noop, focus:noop, moveTop:noop,
    isContentProtected:()=>protectedState,
    setContentProtection: value => { if (fail) throw new Error('unavailable'); protectedState=value;calls.push(value) },
  })
  assert.equal(stealth.setUndetectable(true), true)
  assert.equal(stealth.isUndetectable(), true)
  assert.equal(stealth.getProtectionState().limitation, 'macos-screencapturekit')
  assert.equal(stealth.getProtectionState().externallyVerified, false)
  assert.equal(stealth.setUndetectable(false), true)
  assert.equal(stealth.isUndetectable(), false)
  assert.deepEqual(calls, [true, false])
  fail = true
  assert.equal(stealth.setUndetectable(true), false)
  assert.equal(stealth.isUndetectable(), false)
})

test('Windows reads the OS setting; stale cached state cannot claim protection',()=>{
 const stealth=loadStealth('win32');let protectedState=false
 const noop=()=>{}
 stealth.init({hide:noop,isDestroyed:()=>false,setAlwaysOnTop:noop,
  setContentProtection:v=>protectedState=v,isContentProtected:()=>protectedState})
 assert.equal(stealth.enable(),true)
 assert.equal(stealth.getProtectionState().supported,true)
 protectedState=false
 assert.equal(stealth.isUndetectable(),false)
 assert.equal(stealth.enable(),true)
 assert.equal(stealth.isUndetectable(),true)
})

test('Linux reports unsupported capture exclusion instead of a successful flag',()=>{
 const stealth=loadStealth('linux');const noop=()=>{}
 stealth.init({hide:noop,isDestroyed:()=>false,setAlwaysOnTop:noop,setContentProtection:noop,isContentProtected:()=>false})
 assert.equal(stealth.enable(),false)
 assert.equal(stealth.getProtectionState().supported,false)
 assert.equal(stealth.isUndetectable(),false)
})

test('auxiliary windows inherit protection and partial failures remain visible',()=>{
 const stealth=loadStealth('win32');const noop=()=>{}
 const makeWindow=()=>{
  let state=false
  return {hide:noop,show:noop,focus:noop,moveTop:noop,isDestroyed:()=>false,setAlwaysOnTop:noop,
   setContentProtection:v=>state=v,isContentProtected:()=>state}
 }
 const main=makeWindow();const existing=makeWindow()
 stealth.init(main);stealth.registerWindow(existing)
 assert.equal(stealth.enable(),true)
 assert.equal(existing.isContentProtected(),true)
 const added=makeWindow();stealth.registerWindow(added)
 assert.equal(added.isContentProtected(),true)
 added.setContentProtection(false)
 assert.equal(stealth.getProtectionState().partial,true)
 assert.equal(stealth.isUndetectable(),false)
 assert.equal(stealth.enable(),true)
 assert.equal(stealth.disable(),true)
 assert.equal(existing.isContentProtected(),false)
 assert.equal(added.isContentProtected(),false)
})
