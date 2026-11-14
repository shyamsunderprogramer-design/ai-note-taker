/**
 * stealth.js - Platform stealth/screen-capture-protection module
 *
 * Features:
 * - Stealth mode: minimal UI + tray
 * - Window-wide OS capture exclusion on Windows and macOS
 * - macOS ScreenCaptureKit can bypass exclusion; Linux is unsupported
 *
 * Usage:
 *   stealth.init(window)           - Initialize with Electron BrowserWindow
 *   stealth.enable()              - Enable stealth + platform capture protection
 *   stealth.disable()             - Disable stealth
 *   stealth.isEnabled()           - Check stealth state
 *   stealth.isUndetectable()      - Check if capture protection is active
 */

const { app, Tray, Menu, nativeImage } = require("electron")
const log = require("electron-log/main")
const logger = log
const path = require("path")
const fs = require("fs")

const protectedWindows = new Set()
let _window = null
let _tray = null
let _enabled = false
let stateListener = null

const PLATFORM = process.platform
const IS_WINDOWS = PLATFORM === "win32"
const IS_MAC = PLATFORM === "darwin"

// Native Windows API for maximum protection (optional, falls back to Electron API)
let windowsApi = null
if (IS_WINDOWS) {
  try {
    // Try to load native module for direct Windows API access
    const addonPath = path.join(__dirname, "native", "protection.node")
    if (fs.existsSync(addonPath)) {
      windowsApi = require(addonPath)
      logger.info("[Stealth] Native Windows protection module loaded")
    }
  } catch (e) {
    logger.info("[Stealth] Native module not available, using Electron API fallback")
  }
}

/**
 * Initialize with Electron BrowserWindow
 * @param {BrowserWindow} window
 */
function init(window) {
  if (!window || typeof window.hide !== "function") {
    throw new Error("[Stealth] Invalid BrowserWindow")
  }
  _window = window
  registerWindow(window)
  logger.info("[Stealth] Module initialized (platform mode)")
}

/**
 * Create a minimal transparent 16x16 tray icon
 */
function createTrayIcon() {
  const size = 16
  const stride = size * 4
  const buffer = Buffer.alloc(size * stride)

  // Blue dot
  for (let y = 6; y <= 9; y++) {
    for (let x = 6; x <= 9; x++) {
      const idx = y * stride + x * 4
      buffer[idx] = 59
      buffer[idx + 1] = 130
      buffer[idx + 2] = 246
      buffer[idx + 3] = 180
    }
  }

  return nativeImage.createFromBuffer(buffer, {
    width: size,
    height: size,
    scaleFactor: 1.0
  })
}

/**
 * Create system tray
 */
function createTray() {
  if (_tray) return

  const icon = createTrayIcon()
  _tray = new Tray(icon)
  _tray.setToolTip("ANT (AI Note Taker) — Click to restore")

  const contextMenu = Menu.buildFromTemplate([
    { label: "Restore Window", click: restoreWindow },
    { type: "separator" },
    { label: "Exit", click: () => app.quit() }
  ])

  _tray.setContextMenu(contextMenu)
  _tray.on("click", restoreWindow)

  logger.info("[Stealth] Tray created")
}

function restoreWindow() {
  if (!_window || _window.isDestroyed()) return
  if (_enabled && !protectWindow(_window)) return
  _window.show()
  _window.focus()
}

/**
 * Destroy system tray
 */
function destroyTray() {
  if (_tray) {
    _tray.destroy()
    _tray = null
    logger.info("[Stealth] Tray destroyed")
  }
}

/**
 * Apply platform screen capture protection
 */
function applyPlatformProtection() {
  if (!IS_WINDOWS && !IS_MAC) throw new Error("Capture exclusion is unsupported on this platform")

  // Request the OS capture-exclusion setting; this does not verify external recorders.
  try {
    // Attempt every window even if an earlier one fails.
    const results = liveWindows().map(protectWindow)
    if (!results.length || results.some(result => !result)) throw new Error("OS capture-exclusion setting was not applied to every window")
    logger.info("[Stealth] Content protection enabled")
  } catch (e) {
    logger.warn("[Stealth] Content protection failed:", e.message)
    throw e
  }

  // Method 2: Windows native API (if available)
  if (IS_WINDOWS && windowsApi?.excludeFromCapture) {
    try {
      const hwnd = _window.getNativeWindowHandle().readInt32LE(0)
      windowsApi.excludeFromCapture(hwnd)
      logger.info("[Stealth] Windows native protection applied")
    } catch (e) {
      logger.warn("[Stealth] Native Windows protection failed:", e.message)
    }
  }

  // Opacity and window height do not establish capture protection.

}

/**
 * Remove platform protection
 */
function removePlatformProtection() {
  // Remove content protection
  try {
    const failures = []
    for (const window of liveWindows()) {
      try {
        window.setContentProtection(false)
        if (window.isContentProtected?.()) throw new Error("OS capture exclusion remains enabled")
      } catch (error) { failures.push(error) }
    }
    if (failures.length) throw failures[0]
  } catch (e) {
    logger.warn("[Stealth] Remove content protection failed:", e.message)
    throw e
  }

  // Restore native protection on Windows
  if (IS_WINDOWS && windowsApi?.restoreCapture) {
    try {
      const hwnd = _window.getNativeWindowHandle().readInt32LE(0)
      windowsApi.restoreCapture(hwnd)
    } catch (e) {
      logger.warn("[Stealth] Restore native Windows capture failed:", e.message)
    }
  }


  // Restore window level on macOS
  if (IS_MAC) {
    try {
      _window.setAlwaysOnTop(true, "normal")
    } catch (e) {
      // Ignore
    }
  }
}

/**
 * Enable stealth mode with platform screen capture protection
 */
function enable() {
  if (!_window || _window.isDestroyed()) {
    logger.warn("[Stealth] No window")
    return false
  }

  logger.info("[Stealth] Enabling platform stealth...")

  // Retain the user's protection intent even if one OS call fails. New windows
  // must still inherit it, and failed windows must remain hidden.
  if (IS_WINDOWS || IS_MAC) _enabled = true

  try {
    // Apply all protection methods
    applyPlatformProtection()

    // Tray availability is independent of OS capture exclusion.
    try { createTray() } catch (error) { logger.warn("[Stealth] Tray unavailable:", error.message) }

    // Note: Protection is applied once - no interval to prevent blinking

    // Re-assert always-on-top (must match ensureTopmost level — "monitor" on Windows)
    if (IS_WINDOWS) {
      _window.setAlwaysOnTop(true, "monitor", 2147483647)
    } else if (IS_MAC) {
      _window.setAlwaysOnTop(true, "floating", 999)
    } else {
      _window.setAlwaysOnTop(true)
    }

    publishState()
    logger.info("[Stealth] Platform stealth enabled")
    return true
  } catch (e) {
    logger.error("[Stealth] Enable error:", e.message)
    publishState()
    return false
  }
}

/**
 * Disable stealth mode
 */
function disable() {
  if (!_enabled && !liveWindows().some(window => window.isContentProtected?.())) return true

  logger.info("[Stealth] Disabling stealth...")

  try {
    removePlatformProtection()
    _enabled = false
    destroyTray()

    // Restore always-on-top
    if (_window && !_window.isDestroyed() && IS_WINDOWS) {
      _window.setAlwaysOnTop(true, "normal")
    } else if (_window && !_window.isDestroyed() && IS_MAC) {
      _window.setAlwaysOnTop(true, "floating", 999)
    } else if (_window && !_window.isDestroyed()) {
      _window.setAlwaysOnTop(true)
    }

    // Bring window to front
    restoreWindow()
    publishState()
    logger.info("[Stealth] Stealth disabled")
    return true
  } catch (e) {
    if (_enabled) liveWindows().forEach(protectWindow)
    logger.error("[Stealth] Disable error:", e.message)
    publishState()
    return false
  }
}

/**
 * Toggle stealth mode
 */
function toggle() {
  return _enabled ? disable() : enable()
}

/**
 * Check if stealth is enabled
 */
function isEnabled() {
  return _enabled
}

/**
 * Check if screen capture protection is active
 */
function isUndetectable() {
  try { return !!((IS_WINDOWS || IS_MAC) && liveWindows().length && liveWindows().every(window => window.isContentProtected?.())) }
  catch { return false }
}

/**
 * Set undetectable state directly (for backward compatibility)
 */
function setUndetectable(enabled) {
  return enabled ? enable() : disable()
}

/**
 * Toggle screen capture protection
 */
function toggleUndetectable() {
  return toggle()
}

function liveWindows() { return [...protectedWindows].filter(window => !window.isDestroyed()) }

function protectWindow(window) {
  try {
    if (!window.isContentProtected?.()) window.setContentProtection(true)
    if (!window.isContentProtected?.()) throw new Error("OS capture exclusion was not applied")
    return true
  } catch (error) {
    // A failed request must not leave sensitive content visible.
    try { window.hide() } catch { /* Window may have closed during the request. */ }
    logger.error("[Stealth] Window hidden after protection failed:", error.message)
    return false
  }
}

function publishState() {
  try { stateListener?.(getProtectionState()) }
  catch (error) { logger.warn("[Stealth] State notification failed:", error.message) }
}

function onStateChanged(listener) { stateListener = listener }

// Called before constructing even the splash window. No native handles or tray
// are needed to restore the intent; registration applies it synchronously.
function restore(enabled) {
  _enabled = !!enabled && (IS_WINDOWS || IS_MAC)
}

function registerWindow(window) {
  if (protectedWindows.has(window)) return
  protectedWindows.add(window)
  // Native show/restore events can arrive after the method returns (and after
  // presentation). Check BEFORE calling Electron, including rapid hide/show.
  for (const method of ["show", "showInactive", "restore", "maximize", "setFullScreen"]) {
    if (typeof window[method] !== "function") continue
    const original = window[method].bind(window)
    window[method] = (...args) => {
      if (_enabled && !window.isDestroyed() && !protectWindow(window)) {
        publishState()
        return
      }
      return original(...args)
    }
  }
  window.once?.("closed", () => { protectedWindows.delete(window); publishState() })
  const enforce = () => {
    if (_enabled && !window.isDestroyed()) protectWindow(window)
    publishState()
  }
  for (const event of ["show", "restore", "enter-full-screen", "leave-full-screen"]) window.on?.(event, enforce)
  for (const event of ["did-start-navigation", "did-finish-load"]) window.webContents?.on?.(event, enforce)
  enforce()
}

function getProtectionState() {
  const supported = IS_WINDOWS || IS_MAC
  return {enabled:_enabled, undetectable:isUndetectable(), supported,
    platform:PLATFORM, partial:(_enabled || liveWindows().some(window => window.isContentProtected?.())) && !isUndetectable(), limitation:IS_MAC ? "macos-screencapturekit" : supported ? null : "unsupported-platform", externallyVerified:false}
}

module.exports = {
  restore,
  onStateChanged,
  getProtectionState,
  registerWindow,
  init,
  enable,
  disable,
  toggle,
  isEnabled,
  isUndetectable,
  setUndetectable,
  toggleUndetectable,
  destroyTray
}
