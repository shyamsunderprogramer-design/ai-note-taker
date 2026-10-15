/**
 * Tests for the interviewer-channel capture helper.
 * Run with:
 *   node electron/tests/system-audio.test.js
 *
 * The behaviour worth locking in is the permission trap: when macOS has not
 * granted "System Audio Recording", a Core Audio tap does not fail — it
 * delivers perfectly-formed silence. If that goes undetected the user sees an
 * assist that produces nothing and explains nothing, which is precisely the
 * failure this project spent 2026-09-11 diagnosing. SilenceProbe converts it
 * into an explicit signal, so these tests guard that conversion.
 */

const test = require("node:test")
const assert = require("node:assert")
const { SystemAudioCapture, SilenceProbe, resolveBinary } = require("../lib/system-audio")
const { EventEmitter } = require("node:events")
const vm = require("node:vm")
const fs = require("node:fs")
const path = require("node:path")

test("late close and PCM from a stopped helper cannot overwrite its replacement", () => {
  const children = []
  const spawn = () => {
    const child = new EventEmitter()
    child.stdout = new EventEmitter(); child.stderr = new EventEmitter()
    child.killed = false; child.kill = () => { child.killed = true }
    children.push(child)
    return child
  }
  const module = {exports:{}}
  const filename = path.join(__dirname, "../lib/system-audio.js")
  vm.runInNewContext(fs.readFileSync(filename, "utf8"), {
    module, Buffer, __dirname:path.dirname(filename), process:{platform:"darwin"},
    require: name => name === "child_process" ? {spawn} : require(name),
  })
  const capture = new module.exports.SystemAudioCapture()
  const received = []
  capture.on("data", b => received.push(b))
  capture.start(); capture.stop(); capture.start()
  children[0].stdout.emit("data", Buffer.from([1,0]))
  children[0].emit("close")
  assert.equal(capture.proc, children[1])
  children[1].stdout.emit("data", Buffer.from([2,0]))
  assert.equal(received.length, 1)
  capture.stop()
  assert.ok(children.every(child => child.killed))
})

test("process capture rejects invalid filters before starting audio", () => {
  for (const includeProcesses of [null, "123", [0], [-1], [1.5], [NaN], ["123"]]) {
    assert.throws(() => new SystemAudioCapture({ includeProcesses }), TypeError)
  }
})

test("process capture copies the requested filter independently of caller mutation", () => {
  const pids = [123, 456]
  const capture = new SystemAudioCapture({ includeProcesses: pids })
  pids.length = 0
  assert.deepStrictEqual(capture.includeProcesses, [123, 456])
  assert.deepStrictEqual(new SystemAudioCapture().includeProcesses, [])
})

const silence = (bytes) => Buffer.alloc(bytes)

function signal(bytes, amplitude = 8000) {
  const buf = Buffer.alloc(bytes)
  for (let i = 0; i + 1 < bytes; i += 2) buf.writeInt16LE(amplitude, i)
  return buf
}

test("stays undecided while it has too little audio to judge", () => {
  const probe = new SilenceProbe({ sampleRate: 16000, probeMs: 1000 })
  assert.strictEqual(probe.push(silence(1000)), null)
})

test("reports silence once enough silent audio has arrived", () => {
  const probe = new SilenceProbe({ sampleRate: 16000, probeMs: 100 })
  // 100ms at 16kHz/16-bit = 3200 bytes
  assert.strictEqual(probe.push(silence(3200)), "silent")
})

test("reports ok as soon as any real signal appears", () => {
  const probe = new SilenceProbe({ sampleRate: 16000, probeMs: 1000 })
  assert.strictEqual(probe.push(signal(320)), "ok")
})

test("a late arriving signal still beats the silence verdict", () => {
  const probe = new SilenceProbe({ sampleRate: 16000, probeMs: 200 })
  assert.strictEqual(probe.push(silence(3000)), null)
  assert.strictEqual(probe.push(signal(400)), "ok")
})

test("warns once for silence and recognizes later audio without restarting", () => {
  const probe = new SilenceProbe({ sampleRate: 16000, probeMs: 100 })
  assert.strictEqual(probe.push(silence(3200)), "silent")
  assert.strictEqual(probe.push(silence(3200)), null)
  assert.strictEqual(probe.push(signal(3200)), "ok")
  assert.strictEqual(probe.push(signal(3200)), null)
})

test("odd-length chunks do not read past the buffer", () => {
  const probe = new SilenceProbe({ sampleRate: 16000, probeMs: 100 })
  assert.doesNotThrow(() => probe.push(Buffer.alloc(1)))
})

test("the capture binary is resolvable from the repo", () => {
  assert.ok(resolveBinary(), "audiotee binary not found — capture cannot start")
})
