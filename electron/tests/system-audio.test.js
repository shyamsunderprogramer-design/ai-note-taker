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

test("settles exactly once so the user is not warned repeatedly", () => {
  const probe = new SilenceProbe({ sampleRate: 16000, probeMs: 100 })
  assert.strictEqual(probe.push(silence(3200)), "silent")
  assert.strictEqual(probe.push(silence(3200)), null)
  assert.strictEqual(probe.push(signal(3200)), null)
})

test("odd-length chunks do not read past the buffer", () => {
  const probe = new SilenceProbe({ sampleRate: 16000, probeMs: 100 })
  assert.doesNotThrow(() => probe.push(Buffer.alloc(1)))
})

test("the capture binary is resolvable from the repo", () => {
  assert.ok(resolveBinary(), "audiotee binary not found — capture cannot start")
})
