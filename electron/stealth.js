/**
 * stealth.js - Screen capture hiding module
 *
 * Completely separate from UI and other features.
 * Handles hiding/showing the app window and screen capture protection.
 *
 * Usage:
 *   const stealth = require('./stealth')
 *   stealth.init(window)             - Initialize with Electron BrowserWindow
 *   stealth.enable()                 - Hide window, show tray icon
 *   stealth.disable()                - Show window, hide tray icon
 *   stealth.toggle()                 - Toggle between enable/disable
 *   stealth.isEnabled()              - Check if stealth is active
 *   stealth.setUndetectable(true)   - Hide from screen capture (Zoom/Teams/WebEx)
 *   stealth.isUndetectable()         - Check if screen capture protection is active
 */

const { app, Tray, Menu, nativeImage } = require('electron')

let _window = null
let _tray = null
let _enabled = false
let _undetectable = false

/**
 * Initialize with Electron BrowserWindow
 * @param {BrowserWindow} window - The window to hide/show
 */
function init(window) {
  if (!window || typeof window.hide !== 'function') {
    throw new Error('[Stealth] Invalid BrowserWindow')
  }
  _window = window
  console.log('[Stealth] Module initialized')
}

/**
 * Create system tray icon
 */
function createTray() {
  if (_tray) return

  // 16x16 transparent PNG icon
  const icon = nativeImage.createFromBuffer(
    Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAABYSURBVDiNY2AYBaNg2AAGA0NDBkZGxn/4DIyMDEi0MzKi7wuMjGh1MjIy/qdgFCwHou0LDIj0MjKi1cnIyPifwlEwCobfAwCR9R0LqF1eHwAAAABJRU5ErkJggg==',
      'base64'
    )
  )

  _tray = new Tray(icon)
  _tray.setToolTip('AI Note Taker - Click to restore')

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Restore Window',
      click: () => {
        disable()
      }
    },
    { type: 'separator' },
    {
      label: 'Exit',
      click: () => {
        app.quit()
      }
    }
  ])

  _tray.setContextMenu(contextMenu)

  // Single click restores
  _tray.on('click', () => {
    disable()
  })

  console.log('[Stealth] Tray created')
}

/**
 * Destroy tray icon
 */
function destroyTray() {
  if (_tray) {
    _tray.destroy()
    _tray = null
    console.log('[Stealth] Tray destroyed')
  }
}

/**
 * Enable stealth mode - hide window, show tray
 */
function enable() {
  if (!_window) {
    console.warn('[Stealth] No window to hide')
    return false
  }

  if (_enabled) {
    console.log('[Stealth] Already enabled')
    return true
  }

  console.log('[Stealth] Enabling...')

  try {
    // Hide from taskbar and screen
    _window.hide()
    _window.setSkipTaskbar(true)

    createTray()

    _enabled = true
    console.log('[Stealth] Enabled')
    return true
  } catch (e) {
    console.error('[Stealth] Enable error:', e.message)
    return false
  }
}

/**
 * Disable stealth mode - show window, hide tray
 */
function disable() {
  if (!_window) {
    console.warn('[Stealth] No window')
    return false
  }

  if (!_enabled) {
    console.log('[Stealth] Already disabled')
    return true
  }

  console.log('[Stealth] Disabling...')

  try {
    destroyTray()

    // Restore taskbar visibility
    _window.setSkipTaskbar(false)
    _window.show()
    _window.focus()

    _enabled = false
    console.log('[Stealth] Disabled')
    return true
  } catch (e) {
    console.error('[Stealth] Disable error:', e.message)
    return false
  }
}

/**
 * Toggle stealth mode
 */
function toggle() {
  if (_enabled) {
    disable()
  } else {
    enable()
  }
  return _enabled
}

/**
 * Check if stealth is currently enabled
 */
function isEnabled() {
  return _enabled
}

/**
 * Enable screen capture protection (hide from Zoom/Teams/WebEx)
 * Uses Electron's setContentProtection which maps to Windows SetWindowDisplayAffinity
 */
function setUndetectable(enable) {
  if (!_window) {
    console.warn('[Stealth] No window')
    return false
  }

  try {
    if (enable) {
      // WDA_EXCLUDEFROMCAPTURE = 0x00000001 - excludes window from screen capture
      _window.setContentProtection(true)
      _undetectable = true
      console.log('[Stealth] Undetectable mode enabled (screen capture blocked)')
    } else {
      _window.setContentProtection(false)
      _undetectable = false
      console.log('[Stealth] Undetectable mode disabled (screen capture allowed)')
    }
    return true
  } catch (e) {
    console.error('[Stealth] Undetectable error:', e.message)
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
