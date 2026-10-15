/**
 * Regression tests for "the AI conversation window scrolls".
 * Run with:
 *   node electron/tests/chat-scroll.test.js
 *
 * The .shell sets `-webkit-app-region: drag` so the user can move the
 * window by clicking-and-dragging anywhere on the chrome. That property
 * is INHERITED, so any scrollable area inside .shell needs an explicit
 * `-webkit-app-region: no-drag` override — otherwise the OS swallows
 * the mouse wheel + click events for window dragging and scroll stops
 * working.
 *
 * Locks in:
 *  - .chat-area has -webkit-app-region: no-drag
 *  - .response-area has -webkit-app-region: no-drag (parent of .chat-area)
 *  - .chat-area still has overflow-y: auto (the actual scroll container)
 *  - .chat-area still has min-height: 0 (lets it shrink inside flex column)
 */
const { test } = require("node:test")
const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")

const STYLE_CSS = path.join(__dirname, "..", "..", "apps", "web", "style.css")
const styleSrc = fs.readFileSync(STYLE_CSS, "utf8")

/** Extract the body of the first matching CSS rule. */
function ruleBody(src, selector) {
  // Escape regex specials in the selector (dots, brackets, etc).
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const re = new RegExp(`^${escaped}\\s*\\{([^}]*)\\}`, "m")
  const m = src.match(re)
  return m ? m[1] : null
}

test(".chat-area has -webkit-app-region: no-drag so mouse wheel scrolls", () => {
  const body = ruleBody(styleSrc, ".chat-area")
  assert.ok(body, "expected a .chat-area rule in style.css")
  assert.match(
    body,
    /-webkit-app-region\s*:\s*no-drag/,
    ".chat-area MUST override the inherited drag region from .shell — " +
      "otherwise the OS consumes wheel events for window dragging"
  )
})

test(".response-area has -webkit-app-region: no-drag", () => {
  const body = ruleBody(styleSrc, ".response-area")
  assert.ok(body, "expected a .response-area rule in style.css")
  assert.match(
    body,
    /-webkit-app-region\s*:\s*no-drag/,
    ".response-area MUST also be no-drag so the chat area's no-drag " +
      "isn't fighting a drag parent"
  )
})

test(".chat-area is still a vertical scroll container", () => {
  const body = ruleBody(styleSrc, ".chat-area")
  assert.ok(body, "expected a .chat-area rule in style.css")
  assert.match(body, /overflow-y\s*:\s*auto/,
    ".chat-area must keep overflow-y: auto")
  assert.match(body, /min-height\s*:\s*0/,
    ".chat-area must keep min-height: 0 so it can shrink inside .response-area")
  assert.match(body, /flex\s*:\s*1/,
    ".chat-area must keep flex: 1 to fill remaining space in .response-area")
})
