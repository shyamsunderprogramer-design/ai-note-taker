/**
 * Regression tests for "no native macOS traffic lights in the main window".
 * Run with:
 *   node electron/tests/traffic-lights.test.js
 *
 * The main window is created with `frame: false` (frameless) and the
 * `trafficLightPosition` on darwin is set to off-screen coordinates so
 * the native red/yellow/green buttons never reach the user. The custom
 * HTML traffic lights in apps/web/index.html are the only controls
 * visible on every platform.
 *
 * Locks in:
 *  - PLATFORM === "darwin" branch sets trafficLightPosition to negative coords
 *  - The CSS rule that hid the HTML traffic lights on darwin is GONE
 *    (custom controls must show on macOS too)
 */
const { test } = require("node:test")
const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")

const MAIN_JS = path.join(__dirname, "..", "main.js")
const STYLE_CSS = path.join(__dirname, "..", "..", "apps", "web", "style.css")

const mainSrc = fs.readFileSync(MAIN_JS, "utf8")
const styleSrc = fs.readFileSync(STYLE_CSS, "utf8")

test("main.js pushes native darwin traffic lights off-screen", () => {
  // Find the darwin branch in createWindow that assigns titleBarStyle +
  // trafficLightPosition. There are two `if (PLATFORM === "darwin")`
  // blocks in main.js — the one we want is the first (window options),
  // not the later `setAlwaysOnTop` one. Anchor on `titleBarStyle`.
  const block = mainSrc.match(
    /if\s*\(\s*PLATFORM\s*===\s*"darwin"\s*\)\s*\{[\s\S]*?titleBarStyle[\s\S]*?\}/
  )
  assert.ok(block, "expected to find a `if (PLATFORM === \"darwin\")` block that sets titleBarStyle in createWindow")
  const code = block[0]
  assert.match(code, /titleBarStyle\s*=\s*"hidden"/,
    "titleBarStyle must still be 'hidden' so the title bar stays gone")
  const posMatch = code.match(/trafficLightPosition\s*=\s*\{([^}]+)\}/)
  assert.ok(posMatch, "trafficLightPosition must be set on darwin")
  const posBody = posMatch[1]
  // Both x and y must be negative numbers
  const xMatch = posBody.match(/x:\s*(-?\d+)/)
  const yMatch = posBody.match(/y:\s*(-?\d+)/)
  assert.ok(xMatch && yMatch, "trafficLightPosition must include x and y")
  assert.ok(Number(xMatch[1]) < 0, `trafficLightPosition.x must be negative, got ${xMatch[1]}`)
  assert.ok(Number(yMatch[1]) < 0, `trafficLightPosition.y must be negative, got ${yMatch[1]}`)
})

test("style.css no longer hides custom HTML traffic lights on darwin", () => {
  // We removed `body.platform-darwin .traffic-lights { display: none }`
  // so the custom HTML traffic lights are visible on every platform.
  assert.doesNotMatch(
    styleSrc,
    /body\.platform-darwin\s+\.traffic-lights\s*\{[^}]*display\s*:\s*none/,
    "custom HTML traffic lights must NOT be hidden on darwin anymore"
  )
})

test(".traffic-corner is positioned top-right and is the visible control", () => {
  // Sanity: the custom controls are pinned top-right and the rule that
  // hides them on darwin is gone, so on macOS the user sees the custom
  // red/yellow/green dots at top-right of the window.
  assert.match(styleSrc, /\.traffic-corner\s*\{[^}]*right:\s*10px/m,
    ".traffic-corner should be anchored 10px from the right")
})
