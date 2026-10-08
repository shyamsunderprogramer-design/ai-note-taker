/**
 * stealth.js - Platform stealth/screen-capture-protection module
 *
 * Features:
 * - Stealth mode: minimal UI + tray
 * - Screen capture protection: hide from Zoom/Teams/WebEx/OBS via multiple techniques
 * - Cross-platform: Windows, macOS, Linux support
 *
 * Usage:
 *   stealth.init(window)           - Initialize with Electron BrowserWindow
 *   stealth.enable()              - Enable stealth + platform capture protection
 *   stealth.disable()             - Disable stealth
 *   stealth.isEnabled()           - Check stealth state
 *   stealth.isUndetectable()      - Check if capture protection is active
 */

const { app, Tray, Menu, nativeImage, screen, ipcMain } = require("electron")
const log = require("electron-log/main")
const logger = log
const path = require("path")
const fs = require("fs")

const protectedWindows = new Set()
let _window = null
let _tray = null
let _enabled = false
let _undetectable = false
let _protectionInterval = null

const PLATFORM = process.platform
const IS_WINDOWS = PLATFORM === "win32"
const IS_MAC = PLATFORM === "darwin"
const IS_LINUX = PLATFORM === "linux"

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
    { label: "Restore Window", click: () => disable() },
    { type: "separator" },
    { label: "Exit", click: () => app.quit() }
  ])

  _tray.setContextMenu(contextMenu)
  _tray.on("click", () => disable())

  logger.info("[Stealth] Tray created")
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
  if (!_window || _window.isDestroyed()) return

  if (!IS_WINDOWS && !IS_MAC) throw new Error("Capture exclusion is unsupported on this platform")

  // Request the OS capture-exclusion setting; this does not verify external recorders.
  try {
    for (const window of liveWindows()) {
      window.setContentProtection(true)
      if (!window.isContentProtected?.()) throw new Error("OS capture-exclusion setting was not applied")
    }
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
  if (!_window || _window.isDestroyed()) return

  // Remove content protection
  try {
    for (const window of liveWindows()) window.setContentProtection(false)
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
  if (!_window) {
    logger.warn("[Stealth] No window")
    return false
  }

  if (_enabled && isUndetectable()) return true

  logger.info("[Stealth] Enabling platform stealth...")

  try {
    createTray()

    // Apply all protection methods
    applyPlatformProtection()

    // Note: Protection is applied once - no interval to prevent blinking

    // Re-assert always-on-top (must match ensureTopmost level — "monitor" on Windows)
    if (IS_WINDOWS) {
      _window.setAlwaysOnTop(true, "monitor", 2147483647)
    } else if (IS_MAC) {
      _window.setAlwaysOnTop(true, "floating", 999)
    } else {
      _window.setAlwaysOnTop(true)
    }

    _enabled = true
    _undetectable = true
    logger.info("[Stealth] Platform stealth enabled")
    return true
  } catch (e) {
    destroyTray()
    logger.error("[Stealth] Enable error:", e.message)
    return false
  }
}

/**
 * Disable stealth mode
 */
function disable() {
  if (!_window) {
    logger.warn("[Stealth] No window")
    return false
  }

  if (!_enabled && !isUndetectable()) return true

  logger.info("[Stealth] Disabling stealth...")

  try {
    // Stop protection interval
    if (_protectionInterval) {
      clearInterval(_protectionInterval)
      _protectionInterval = null
    }

    destroyTray()
    removePlatformProtection()

    // Restore always-on-top
    if (IS_WINDOWS) {
      _window.setAlwaysOnTop(true, "normal")
    } else if (IS_MAC) {
      _window.setAlwaysOnTop(true, "floating", 999)
    } else {
      _window.setAlwaysOnTop(true)
    }

    // Bring window to front
    _window.show()
    _window.focus()
    _window.moveTop()

    _enabled = false
    _undetectable = false
    logger.info("[Stealth] Stealth disabled")
    return true
  } catch (e) {
    logger.error("[Stealth] Disable error:", e.message)
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
  try { return !!(_window && !_window.isDestroyed() && liveWindows().every(window => window.isContentProtected?.())) }
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
function registerWindow(window) {
  if (protectedWindows.has(window)) return
  protectedWindows.add(window)
  window.once?.("closed", () => protectedWindows.delete(window))
  if (_enabled && (IS_WINDOWS || IS_MAC)) window.setContentProtection(true)
}

function getProtectionState() {
  const supported = IS_WINDOWS || IS_MAC
  return {enabled:_enabled, undetectable:isUndetectable(), supported,
    platform:PLATFORM, partial:liveWindows().some(window => window.isContentProtected?.()) && !isUndetectable(), limitation:IS_MAC ? "macos-screencapturekit" : supported ? null : "unsupported-platform", externallyVerified:false}
}

module.exports = {
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
