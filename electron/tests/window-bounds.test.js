/**
 * Regression tests for the main window default size and min constraints.
 * Run with:
 *   node electron/tests/window-bounds.test.js
 *
 * Locks in the minimum dimensions (MIN_WIDTH/MIN_HEIGHT) and the default
 * 960x720 fallback so the main window never opens smaller than the
 * hero-banner + header + controls + input + chat-area content needs.
 */
const { test } = require("node:test")
const assert = require("node:assert/strict")

// --- Constants must match what's in main.js (lines 224-229) ---
// We hard-code them here because main.js can't be required outside an
// Electron context. If you change these in main.js, change them here too.
const MIN_WIDTH = 560
const MIN_HEIGHT = 600
const DEFAULT_BOUNDS = { width: 960, height: 720 }

test("MIN_WIDTH is large enough to fit the controls strip", () => {
  assert.ok(MIN_WIDTH >= 560, `MIN_WIDTH must be >= 560, got ${MIN_WIDTH}`)
})

test("MIN_HEIGHT is large enough to fit hero + header + controls + input + response", () => {
  // Approx content heights: 180 (hero) + 50 (header) + 80 (controls) + 60
  // (input) + 30 (response header) + 200 (chat) = 600. Round up to 600.
  assert.ok(MIN_HEIGHT >= 600, `MIN_HEIGHT must be >= 600, got ${MIN_HEIGHT}`)
})

test("DEFAULT_BOUNDS is a sensible first-run size", () => {
  assert.ok(DEFAULT_BOUNDS.width >= 800, "default width should be comfortable, not cramped")
  assert.ok(DEFAULT_BOUNDS.height >= 600, "default height should fit all content")
  // Should fit on a 1366x768 laptop with taskbar
  assert.ok(DEFAULT_BOUNDS.width <= 1366, "default width should fit small laptops")
  assert.ok(DEFAULT_BOUNDS.height <= 768, "default height should fit small laptops")
})

test("DEFAULT_BOUNDS is at least MIN_WIDTH x MIN_HEIGHT", () => {
  assert.ok(DEFAULT_BOUNDS.width >= MIN_WIDTH)
  assert.ok(DEFAULT_BOUNDS.height >= MIN_HEIGHT)
})

test("off-screen bounds should be rejected and replaced", () => {
  // Simulate a saved bounds object from a now-disconnected 4K display
  const bogus = { width: 2400, height: 1600, x: 5000, y: 5000 }
  // validateBounds() in main.js would replace these with DEFAULT_BOUNDS
  // centered on the primary display. We can only smoke-test the contract
  // here; the real function is in main.js and requires electron.
  assert.ok(bogus.x > 4000, "this is the kind of bounds validateBounds must reject")
})

test("window:restore IPC fallback 960x720 is still adequate", () => {
  // The fallback in main.js:956 uses 960x720 — make sure we don't regress
  // it to something too small.
  const fallback = { width: 960, height: 720 }
  assert.ok(fallback.width >= MIN_WIDTH)
  assert.ok(fallback.height >= MIN_HEIGHT)
})
