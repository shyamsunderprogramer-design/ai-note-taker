const test = require('node:test')
const assert = require('node:assert/strict')
const vm = require('node:vm')
const fs = require('node:fs')
const path = require('node:path')

function loadStealth(platform = 'darwin', hooks = {}) {
  const noop = () => {}
  const electron = {
    app: {}, Menu: { buildFromTemplate: () => [] },
    nativeImage: { createFromBuffer: () => ({}) },
    Tray: class { setToolTip() {} setContextMenu() {} on(event, handler) { hooks[event] = handler } destroy() {} },
  }
  const module = { exports: {} }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../stealth.js'), 'utf8'), {
    module, Buffer, process: { platform }, __dirname,
    require: name => name === 'electron' ? electron : name === 'electron-log/main' ? {info:noop,warn:noop,error:noop} : require(name),
  })
  return module.exports
}

function lifecycleWindow() {
  const {EventEmitter} = require('node:events')
  const window = new EventEmitter()
  window.webContents = new EventEmitter()
  window.protected = false
  window.visible = false
  window.isDestroyed = () => false
  window.isContentProtected = () => window.protected
  window.setContentProtection = value => { window.protected = value }
  window.hide = () => { window.visible = false }
  window.show = () => { window.visible = true; window.emit('show') }
  window.focus = window.moveTop = window.setAlwaysOnTop = () => {}
  return window
}

test('saved protection applies before the first window is initialized', () => {
  const stealth = loadStealth()
  stealth.restore(true)
  const splash = lifecycleWindow()
  stealth.registerWindow(splash)
  assert.equal(splash.isContentProtected(), true)
  const main = lifecycleWindow()
  stealth.init(main)
  assert.equal(main.isContentProtected(), true)
})

test('navigation, restore and fullscreen retain protection without scroll timers', () => {
  const stealth = loadStealth()
  const main = lifecycleWindow()
  stealth.init(main)
  stealth.enable()
  for (const event of ['show', 'restore', 'enter-full-screen', 'leave-full-screen']) {
    main.protected = false
    main.emit(event)
    assert.equal(main.protected, true, event)
  }
  for (const event of ['did-start-navigation', 'did-finish-load']) {
    main.protected = false
    main.webContents.emit(event)
    assert.equal(main.protected, true, event)
  }
})

test('a failed window is hidden, other windows are protected, and disable clears partial state', () => {
  const stealth = loadStealth()
  const main = lifecycleWindow(), broken = lifecycleWindow(), last = lifecycleWindow()
  stealth.init(main)
  broken.setContentProtection = () => { throw Error('OS rejected protection') }
  stealth.registerWindow(broken)
  stealth.registerWindow(last)
  broken.show()
  assert.equal(stealth.enable(), false)
  assert.equal(broken.visible, false)
  assert.equal(last.protected, true)
  assert.equal(stealth.getProtectionState().enabled, true)
  assert.equal(stealth.getProtectionState().partial, true)
  broken.setContentProtection = value => { broken.protected = value }
  assert.equal(stealth.disable(), true)
  assert.equal(main.protected, false)
  assert.equal(last.protected, false)
})

test('failed protection on a new window does not throw or allow it to remain visible', () => {
  const stealth = loadStealth()
  const main = lifecycleWindow(), added = lifecycleWindow()
  stealth.init(main)
  stealth.enable()
  added.setContentProtection = () => { throw Error('unavailable') }
  assert.doesNotThrow(() => stealth.registerWindow(added))
  added.show()
  assert.equal(added.visible, false)
  assert.equal(stealth.getProtectionState().partial, true)
})

test('restoring from the tray keeps protection enabled', () => {
  const hooks = {}, stealth = loadStealth('darwin', hooks), main = lifecycleWindow()
  stealth.init(main)
  stealth.enable()
  main.hide()
  hooks.click()
  assert.equal(main.visible, true)
  assert.equal(main.protected, true)
  assert.equal(stealth.isEnabled(), true)
})

test('native visibility methods check protection before display, without waiting for events', () => {
  const stealth = loadStealth(), main = lifecycleWindow(), displayed = []
  for (const method of ['show', 'showInactive', 'restore', 'maximize', 'setFullScreen']) {
    main[method] = () => { displayed.push(method); assert.equal(main.protected, true) }
  }
  stealth.init(main)
  stealth.enable()
  for (const method of ['show', 'showInactive', 'restore', 'maximize', 'setFullScreen']) {
    main.protected = false
    main[method](true)
  }
  assert.equal(displayed.length, 5)
  main.protected = false
  main.setContentProtection = () => { throw Error('unavailable') }
  main.show()
  assert.equal(displayed.length, 5, 'failed protection must prevent the native show call')
})

test('protection changes notify every renderer and closing the primary leaves auxiliary protection intact', () => {
  const stealth = loadStealth(), main = lifecycleWindow(), aux = lifecycleWindow(), states = []
  stealth.onStateChanged(state => states.push(state))
  stealth.init(main)
  stealth.registerWindow(aux)
  stealth.enable()
  assert.equal(states.at(-1).undetectable, true)
  main.isDestroyed = () => true
  main.emit('closed')
  assert.equal(states.at(-1).undetectable, true)
  assert.equal(stealth.disable(), true)
  assert.equal(aux.protected, false)
  assert.equal(states.at(-1).enabled, false)
})

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
