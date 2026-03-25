/**
 * stealth.js - Standalone stealth/screen-capture-protection module
 *
 * Completely isolated. Update without disturbing other code.
 *
 * Features:
 * - Stealth mode: hide window, show tray
 * - Screen capture protection: hide from Zoom/Teams/WebEx via SetWindowDisplayAffinity
 *
 * Usage:
 *   stealth.init(window)           - Initialize with Electron BrowserWindow
 *   stealth.enable()              - Hide window + show tray
 *   stealth.disable()             - Show window + hide tray
 *   stealth.toggle()              - Toggle stealth
 *   stealth.isEnabled()           - Check stealth state
 *   stealth.setUndetectable(bool) - Toggle screen capture protection
 *   stealth.isUndetectable()      - Check capture protection state
 *   stealth.toggleUndetectable()  - Toggle capture protection
 */

const { app, Tray, Menu, nativeImage, screen } = require("electron")
const log = require("electron-log/main")
const logger = log

let _window = null
let _tray = null
let _enabled = false
let _undetectable = false

// WDA_EXCLUDEFROMCAPTURE - excludes window from screen capture on Windows
const WDA_EXCLUDEFROMCAPTURE = 0x00000001

/**
 * Initialize with Electron BrowserWindow
 * @param {BrowserWindow} window
 */
function init(window) {
  if (!window || typeof window.hide !== "function") {
    throw new Error("[Stealth] Invalid BrowserWindow")
  }
  _window = window
  logger.info("[Stealth] Module initialized")
}

/**
 * Create a minimal transparent 16x16 tray icon from raw pixel data
 */
function createTrayIcon() {
  // 16x16 solid transparent pixel RGBA buffer
  const size = 16
  const stride = size * 4  // RGBA
  const buffer = Buffer.alloc(size * stride)

  // Make a subtle semi-transparent dot
  for (let y = 6; y <= 9; y++) {
    for (let x = 6; x <= 9; x++) {
      const idx = y * stride + x * 4
      buffer[idx] = 59       // B
      buffer[idx + 1] = 130  // G
      buffer[idx + 2] = 246  // R (#3b82f6 blue)
      buffer[idx + 3] = 180  // A
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
  _tray.setToolTip("AI Note Taker — Click to restore")

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Restore Window",
      click: () => disable()
    },
    { type: "separator" },
    {
      label: "Exit",
      click: () => app.quit()
    }
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
 * Enable stealth mode — apply screen capture protection, show tray.
 * Window stays visible (minimal UI controlled by CSS class).
 */
function enable() {
  if (!_window) {
    logger.warn("[Stealth] No window")
    return false
  }

  if (_enabled) return true

  logger.info("[Stealth] Enabling stealth...")

  try {
    createTray()
    // Also enable capture protection when stealth mode is activated
    _window.setContentProtection(true)
    _enabled = true
    _undetectable = true
    logger.info("[Stealth] Stealth enabled (tray active, capture protection ON)")
    return true
  } catch (e) {
    logger.error("[Stealth] Enable error:", e.message)
    return false
  }
}

/**
 * Disable stealth mode — remove screen capture protection, hide tray
 */
function disable() {
  if (!_window) {
    logger.warn("[Stealth] No window")
    return false
  }

  if (!_enabled) return true

  logger.info("[Stealth] Disabling stealth...")

  try {
    destroyTray()
    setUndetectable(false)
    _enabled = false
    logger.info("[Stealth] Stealth disabled (screen capture allowed)")
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
 * Enable/disable screen capture protection.
 *
 * On Windows: Uses SetWindowDisplayAffinity with WDA_EXCLUDEFROMCAPTURE.
 * This hides the window content from screen capture in:
 * - Zoom, Teams, WebEx, Discord, OBS, Snipping Tool, etc.
 *
 * Note: This does NOT use any game-specific anti-cheat APIs.
 * It's the standard Windows DPI API for content protection.
 */
function setUndetectable(enable) {
  if (!_window) {
    logger.warn("[Stealth] No window")
    return false
  }

  try {
    if (enable) {
      // Hide from screen capture
      _window.setContentProtection(true)
      _undetectable = true
      logger.info("[Stealth] Screen capture protection ENABLED")
    } else {
      _window.setContentProtection(false)
      _undetectable = false
      logger.info("[Stealth] Screen capture protection DISABLED")
    }
    return true
  } catch (e) {
    logger.error("[Stealth] Undetectable error:", e.message)
    return false
  }
}

/**
 * Check if screen capture protection is active
 */
function isUndetectable() {
  return _undetectable
}

/**
 * Toggle screen capture protection
 */
function toggleUndetectable() {
  return setUndetectable(!_undetectable)
}

module.exports = {
  init,
  enable,
  disable,
  toggle,
  isEnabled,
  setUndetectable,
  isUndetectable,
  toggleUndetectable
}
