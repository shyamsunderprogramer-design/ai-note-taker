/**
 * Regression tests for the opacity slider headroom (10–150).
 * Run with:
 *   node electron/tests/opacity-slider.test.js
 *
 * The slider in apps/web/index.html (id="opacitySlider") used to be
 * hard-capped at max=100. That meant the user could never get a
 * darker glass than the CSS-at-100% values. The slider was extended
 * to max=150 so the user can crank past 100% — 10–100 still maps to
 * Electron window opacity (0.10–1.00), 100–150 is CSS-only "darker
 * glass" headroom.
 *
 * Locks in:
 *  - Slider max is 150
 *  - updateGlassOpacity() does NOT call overlay:set-opacity when f>1
 *    (would be clamped to 1.0 and snap the slider back to 100)
 *  - onOpacityChanged listener does NOT overwrite a slider value >100
 *    (same reason — IPC event only carries 0.1–1.0)
 *  - The CSS variable scaling still works at f=1.5 (tested by reading
 *    the source for the right coefficients)
 */
const { test } = require("node:test")
const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")

const HTML = path.join(__dirname, "..", "..", "apps", "web", "index.html")
const APP_JS = path.join(__dirname, "..", "..", "apps", "web", "app.js")

const htmlSrc = fs.readFileSync(HTML, "utf8")
const appSrc = fs.readFileSync(APP_JS, "utf8")

test("opacitySlider max is 150 (was 100, extended for darker glass)", () => {
  // The slider element lives in index.html. We don't want max=100 to
  // silently come back — the user explicitly asked for more headroom.
  const m = htmlSrc.match(/id="opacitySlider"[^>]*>/)
  assert.ok(m, "expected an <input id=\"opacitySlider\"> element in index.html")
  assert.match(m[0], /\bmax="150"/,
    `opacitySlider must have max="150", got: ${m[0]}`)
  assert.match(m[0], /\bmin="10"/,
    "opacitySlider must keep min=10")
})

test("updateGlassOpacity skips backend sync when slider > 100", () => {
  // The bug we'd regress to: when f>1.0 the renderer still calls
  // window.api.invoke("overlay:set-opacity", f) which the backend
  // clamps to 1.0 and echoes back, snapping the slider from 150 to 100.
  // Lock in the guard.
  const fn = appSrc.match(/function\s+updateGlassOpacity\s*\([^)]*\)\s*\{[\s\S]*?\n\}/)
  assert.ok(fn, "expected to find updateGlassOpacity() in app.js")
  assert.match(fn[0], /f\s*<=\s*1\.0/,
    "updateGlassOpacity must guard the backend sync with f <= 1.0 so " +
      "values >100 don't echo back as 1.0 and snap the slider")
})

test("onOpacityChanged listener does not overwrite slider value > 100", () => {
  // Same reason: IPC event carries 0.1-1.0 only. If the user is at
  // slider=140 and a hotkey fires, we must NOT reset the slider to
  // e.g. 100. Lock in the early-return guard.
  const block = appSrc.match(/onOpacityChanged\(\s*\(overlayOpacity\)\s*=>\s*\{[\s\S]*?\}\s*\}\)/)
  assert.ok(block, "expected the onOpacityChanged callback in app.js")
  assert.match(block[0], /currentSlider\s*>\s*100/,
    "the callback must early-return when currentSlider > 100 so IPC " +
      "events from hotkeys don't clobber the CSS-only headroom")
})

test("--hero-opacity is clamped to 1 even when slider > 100", () => {
  // --hero-opacity is multiplied directly into the hero image alpha.
  // Going past 1.0 would be a no-op visually but cosmetically wrong;
  // other CSS uses that var as a real opacity. Math.min(1, f) keeps
  // it sane.
  const fn = appSrc.match(/function\s+updateGlassOpacity\s*\([^)]*\)\s*\{[\s\S]*?\n\}/)
  assert.ok(fn, "expected to find updateGlassOpacity() in app.js")
  assert.match(fn[0], /--hero-opacity["']?\s*,\s*Math\.min\(1,\s*f\)/,
    "hero-opacity must be clamped to 1 with Math.min(1, f)")
})
