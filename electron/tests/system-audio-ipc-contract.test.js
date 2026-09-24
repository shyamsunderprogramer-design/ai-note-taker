/**
 * The renderer talks to the native audio tap only through preload. A name
 * mismatch there fails SILENTLY at runtime — `window.api.startSystemAudio`
 * would simply be undefined and the interviewer channel would never start,
 * with no error anywhere. These tests read the real files and assert the
 * three sides agree.
 */

const test = require("node:test")
const assert = require("node:assert")
const fs = require("fs")
const path = require("path")

const read = (p) => fs.readFileSync(path.join(__dirname, "..", p), "utf8")
const preload = read("preload.js")
const main = read("main.js")
const renderer = fs.readFileSync(
  path.join(__dirname, "..", "..", "apps", "web", "app.js"), "utf8"
)

const RENDERER_CALLS = [
  "startSystemAudio",
  "stopSystemAudio",
  "onSystemAudioData",
  "onSystemAudioSilent",
  "onSystemAudioError",
]

test("every system-audio method the renderer calls is exposed by preload", () => {
  for (const name of RENDERER_CALLS) {
    assert.ok(
      renderer.includes(`api.${name}`) || renderer.includes(`api?.${name}`),
      `renderer never calls ${name} — stale test or dead preload surface`
    )
    assert.ok(preload.includes(`${name}:`), `preload does not expose ${name}`)
  }
})

test("preload invoke channels have matching main-process handlers", () => {
  for (const channel of ["system-audio:start", "system-audio:stop"]) {
    assert.ok(preload.includes(`"${channel}"`), `preload missing ${channel}`)
    assert.ok(
      main.includes(`ipcMain.handle("${channel}"`),
      `main.js has no handler for ${channel}`
    )
  }
})

test("main-process push channels are all listened for in preload", () => {
  for (const channel of ["system-audio:data", "system-audio:silent", "system-audio:error"]) {
    assert.ok(main.includes(`"${channel}"`), `main.js never sends ${channel}`)
    assert.ok(preload.includes(`"${channel}"`), `preload never listens for ${channel}`)
  }
})

test("the renderer converts the tap's int16 PCM before sending float32", () => {
  // The socket reads float32 (np.frombuffer(dtype=np.float32)); the tap emits
  // int16. Skipping the conversion produces noise, not an error.
  assert.ok(renderer.includes("pcm16ToFloat32"))
  assert.ok(renderer.includes("getInt16"))
})

test("the interviewer socket is tagged source=system", () => {
  // The backend's channel-ownership gate keys on this exact value.
  assert.ok(renderer.includes("/ws/transcribe?source=system"))
})
