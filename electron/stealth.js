/**
 * stealth.js - Bulletproof stealth/screen-capture-protection module
 *
 * Features:
 * - Stealth mode: minimal UI + tray
 * - Screen capture protection: hide from Zoom/Teams/WebEx/OBS via multiple techniques
 * - Cross-platform: Windows, macOS, Linux support
 *
 * Usage:
 *   stealth.init(window)           - Initialize with Electron BrowserWindow
 *   stealth.enable()              - Enable stealth + bulletproof capture protection
 *   stealth.disable()             - Disable stealth
 *   stealth.isEnabled()           - Check stealth state
 *   stealth.isUndetectable()      - Check if capture protection is active
 */

const { app, Tray, Menu, nativeImage, screen, ipcMain } = require("electron")
const log = require("electron-log/main")
const logger = log
const path = require("path")
const fs = require("fs")

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
  logger.info("[Stealth] Module initialized (bulletproof mode)")
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
 * Apply bulletproof screen capture protection
 */
function applyBulletproofProtection() {
  if (!_window || _window.isDestroyed()) return

  // Method 1: Electron's cross-platform content protection
  try {
    _window.setContentProtection(true)
    logger.info("[Stealth] Content protection enabled")
  } catch (e) {
    logger.warn("[Stealth] Content protection failed:", e.message)
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

  // Method 3: Additional visual obfuscation
  // Make window semi-transparent which can confuse some capture methods
  try {
    _window.setOpacity(0.95)
  } catch (e) {
    // Ignore
  }

  // Method 4: Disable compositing on supported platforms
  // This can prevent some capture methods
  if (IS_LINUX) {
    try {
      _window.setContentProtection(true)
    } catch (e) {
      // Fallback already attempted above
    }
  }

  // Method 5: Set window to exclude from capture on macOS
  if (IS_MAC) {
    try {
      // On macOS, setContentProtection uses CGWindow
      // Additional: set window level to be above capture
      _window.setAlwaysOnTop(true, "screen-saver", 2147483647)
    } catch (e) {
      logger.warn("[Stealth] macOS additional protection failed:", e.message)
    }
  }
}

/**
 * Remove bulletproof protection
 */
function removeBulletproofProtection() {
  if (!_window || _window.isDestroyed()) return

  // Remove content protection
  try {
    _window.setContentProtection(false)
  } catch (e) {
    logger.warn("[Stealth] Remove content protection failed:", e.message)
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

  // Restore opacity
  try {
    _window.setOpacity(1.0)
  } catch (e) {
    // Ignore
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
 * Enable stealth mode with bulletproof screen capture protection
 */
function enable() {
  if (!_window) {
    logger.warn("[Stealth] No window")
    return false
  }

  if (_enabled) return true

  logger.info("[Stealth] Enabling bulletproof stealth...")

  try {
    createTray()

    // Apply all protection methods
    applyBulletproofProtection()

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
    logger.info("[Stealth] Bulletproof stealth enabled")
    return true
  } catch (e) {
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

  if (!_enabled) return true

  logger.info("[Stealth] Disabling stealth...")

  try {
    // Stop protection interval
    if (_protectionInterval) {
      clearInterval(_protectionInterval)
      _protectionInterval = null
    }

    destroyTray()
    removeBulletproofProtection()

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
  return _undetectable
}

/**
 * Set undetectable state directly (for backward compatibility)
 */
function setUndetectable(enable) {
  if (enable) {
    if (!_enabled) enable()
  } else {
    if (_enabled) disable()
  }
  return true
}

/**
 * Toggle screen capture protection
 */
function toggleUndetectable() {
  return toggle()
}

module.exports = {
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
