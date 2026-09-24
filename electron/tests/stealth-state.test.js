const test = require('node:test')
const assert = require('node:assert/strict')
const vm = require('node:vm')
const fs = require('node:fs')
const path = require('node:path')

function loadStealth() {
  const noop = () => {}
  const electron = {
    app: {}, Menu: { buildFromTemplate: () => [] },
    nativeImage: { createFromBuffer: () => ({}) },
    Tray: class { setToolTip() {} setContextMenu() {} on() {} destroy() {} },
  }
  const module = { exports: {} }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../stealth.js'), 'utf8'), {
    module, Buffer, process: { platform: 'darwin' }, __dirname,
    require: name => name === 'electron' ? electron : name === 'electron-log/main' ? {info:noop,warn:noop,error:noop} : require(name),
  })
  return module.exports
}

test('capture protection toggles both directions and reports failures', () => {
  const stealth = loadStealth()
  let fail = false
  const calls = []
  const noop = () => {}
  stealth.init({ hide:noop, isDestroyed:()=>false, setAlwaysOnTop:noop, setOpacity:noop,
    show:noop, focus:noop, moveTop:noop,
    setContentProtection: value => { if (fail) throw new Error('unavailable'); calls.push(value) },
  })
  assert.equal(stealth.setUndetectable(true), true)
  assert.equal(stealth.isUndetectable(), true)
  assert.equal(stealth.setUndetectable(false), true)
  assert.equal(stealth.isUndetectable(), false)
  assert.deepEqual(calls, [true, false])
  fail = true
  assert.equal(stealth.setUndetectable(true), false)
  assert.equal(stealth.isUndetectable(), false)
})
