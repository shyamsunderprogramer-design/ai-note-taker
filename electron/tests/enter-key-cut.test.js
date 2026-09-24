const test = require("node:test")
const assert = require("node:assert")
const fs = require("fs")
const path = require("path")

const app = fs.readFileSync(
  path.join(__dirname, "..", "..", "apps", "web", "app.js"), "utf8"
)

test("Enter toggles recording instead of only cutting a question", () => {
  const start = app.indexOf("Enter elsewhere = toggle listening")
  const handler = app.slice(start, app.indexOf("// HELPERS", start))
  assert.ok(handler.includes("stopListening()"))
  assert.ok(handler.includes("listenBtn.click()"))
  assert.ok(!handler.includes("cutLiveQuestion()"))
})

test("the cut is sent as a control message both channels understand", () => {
  assert.ok(app.includes('JSON.stringify({ type: "cut" })'))
})

test("the cut reaches every open channel, since either may hold the question", () => {
  const fn = app.slice(app.indexOf("function cutLiveQuestion()"))
  assert.ok(fn.includes("transcribeWs") && fn.includes("systemAudioWs"))
})

test("cutting only targets sockets that are actually open", () => {
  const fn = app.slice(app.indexOf("function cutLiveQuestion()"))
  assert.ok(fn.includes("WebSocket.OPEN"))
})

test("closing a session waits for answers already in flight", () => {
  // Audio stops immediately; the socket lingers only to receive what it asked
  // for. Closing instantly is what discarded the hints.
  assert.ok(app.includes("SUGGESTION_GRACE_MS"))
  const grace = app.match(/const SUGGESTION_GRACE_MS = (\d+)/)
  assert.ok(grace && Number(grace[1]) >= 4000, "grace window too short to land an answer")
})

test("the committed answer lands in the chat, not the side panel", () => {
  // It rendered into the suggestions panel until 2026-09-12 and the user did
  // not see it: attention is on the conversation, not a side panel.
  const fn = app.slice(app.indexOf("function renderStreamedAnswer"))
  const body = fn.slice(0, fn.indexOf("\n}"))
  assert.ok(body.includes("addMessage("), "answers no longer reach the chat")
  assert.ok(!body.includes("suggestionsContent"), "answers went back to the side panel")
})

test("the streamed answer rewrites one bubble instead of adding a second", () => {
  const fn = app.slice(app.indexOf("function renderStreamedAnswer"))
  const body = fn.slice(0, fn.indexOf("\n}"))
  assert.ok(body.includes("setBubbleText"), "the full answer no longer updates the bubble")
  assert.ok(body.includes("liveAnswerBubbles"), "no identity tracking between the two sends")
})

test("saved history keeps the full answer, not the opening fragment", () => {
  const fn = app.slice(app.indexOf("function renderStreamedAnswer"))
  assert.ok(fn.slice(0, fn.indexOf("\n}")).includes("entry.text = data.text"))
})

test("rolling previews stay in the side panel", () => {
  // They rewrite a single slot every couple of seconds; a chat log would turn
  // that into a wall of near-duplicate messages.
  const fn = app.slice(app.indexOf("function renderPreviewHint"))
  assert.ok(fn.slice(0, fn.indexOf("\n}")).includes("suggestionsContent"))
})
