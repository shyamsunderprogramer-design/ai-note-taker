/**
 * overlay-adapter.js - Overlay window and global hotkeys for ANT
 *
 * Features:
 * - Translucent overlay window with adjustable opacity
 * - Global hotkeys (Cmd/Ctrl+Shift+M/A/S/H/O/P/T)
 * - Click-through mode for stealth
 * - File drag & drop support
 * - Window state persistence
 *
 * @module OverlayAdapter
 */

const { BrowserWindow, globalShortcut, ipcMain, screen, dialog } = require("electron")
const path = require("path")
const log = require("electron-log/main")
const Store = require("electron-store")
const fs = require("fs")

const store = new Store({ name: "overlay-settings" })
const logger = log

const PLATFORM = process.platform

class OverlayAdapter {
  constructor(mainWindow) {
    this.mainWindow = mainWindow
    this.overlayWindow = null
    this.opacity = store.get("overlayOpacity", 0.9)
    this.isClickThrough = false
    this.overlayBounds = store.get("overlayBounds", {
      width: 400,
      height: 600,
      x: undefined,
      y: undefined
    })

    // Drag & drop state
    this.dragOverlay = null

    logger.info("[OverlayAdapter] Initialized")
  }

  /**
   * Create the translucent overlay window
   */
  createOverlay() {
    if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
      this.overlayWindow.focus()
      return this.overlayWindow
    }

    // Calculate position (default to right side of screen)
    const primaryDisplay = screen.getPrimaryDisplay()
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize

    const bounds = this.overlayBounds
    if (!bounds.x || !bounds.y) {
      bounds.x = screenWidth - bounds.width - 20
      bounds.y = Math.round((screenHeight - bounds.height) / 2)
    }

    this.overlayWindow = new BrowserWindow({
      width: bounds.width,
      height: bounds.height,
      x: bounds.x,
      y: bounds.y,
      minWidth: 300,
      minHeight: 400,
      transparent: true,
      frame: false,
      alwaysOnTop: true,
      skipTaskbar: true,
      opacity: this.opacity,
      backgroundColor: "#00000000",
      hasShadow: false,
      webPreferences: {
        preload: path.join(__dirname, "..", "preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
        webSecurity: true
      },
      // macOS specific
      titleBarStyle: PLATFORM === "darwin" ? "hidden" : undefined,
      trafficLightPosition: PLATFORM === "darwin" ? { x: -100, y: -100 } : undefined
    })

    // Set always on top level
    if (PLATFORM === "win32") {
      this.overlayWindow.setAlwaysOnTop(true, "monitor", 2147483647)
    } else if (PLATFORM === "darwin") {
      this.overlayWindow.setAlwaysOnTop(true, "floating", 999)
    }

    this.overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

    // Load the overlay HTML
    const isProd = require("electron").app.isPackaged
    const overlayPath = isProd
      ? path.join(process.resourcesPath, "renderer", "overlay.html")
      : path.join(__dirname, "..", "..", "apps", "web", "overlay.html")

    this.overlayWindow.loadFile(overlayPath).catch(() => {
      // Fallback to index with overlay mode
      const indexPath = isProd
        ? path.join(process.resourcesPath, "renderer", "index.html")
        : path.join(__dirname, "..", "..", "apps", "web", "index.html")
      this.overlayWindow.loadFile(indexPath, { hash: "overlay" })
    })

    // Save bounds on move/resize
    this.overlayWindow.on("moved", () => this.saveOverlayBounds())
    this.overlayWindow.on("resized", () => this.saveOverlayBounds())

    // Handle window close
    this.overlayWindow.on("closed", () => {
      this.overlayWindow = null
      this.isClickThrough = false
    })

    // Handle drag and drop
    this.setupDragAndDrop()

    logger.info("[OverlayAdapter] Overlay window created")
    return this.overlayWindow
  }

  /**
   * Save overlay window bounds
   */
  saveOverlayBounds() {
    if (!this.overlayWindow || this.overlayWindow.isDestroyed()) return
    const bounds = this.overlayWindow.getBounds()
    this.overlayBounds = bounds
    store.set("overlayBounds", bounds)
  }

  /**
   * Toggle overlay visibility
   */
  toggleOverlay() {
    if (!this.overlayWindow || this.overlayWindow.isDestroyed()) {
      this.createOverlay()
      return true
    }

    if (this.overlayWindow.isVisible()) {
      this.overlayWindow.hide()
      return false
    } else {
      this.overlayWindow.show()
      this.overlayWindow.focus()
      return true
    }
  }

  /**
   * Show overlay
   */
  showOverlay() {
    if (!this.overlayWindow || this.overlayWindow.isDestroyed()) {
      this.createOverlay()
    } else {
      this.overlayWindow.show()
      this.overlayWindow.focus()
    }
  }

  /**
   * Hide overlay
   */
  hideOverlay() {
    if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
      this.overlayWindow.hide()
    }
  }

  /**
   * Toggle click-through mode (mouse events pass through)
   */
  toggleClickThrough() {
    this.isClickThrough = !this.isClickThrough
    if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
      this.overlayWindow.setIgnoreMouseEvents(this.isClickThrough)
      // Visual feedback
      this.overlayWindow.webContents.send("click-through-changed", this.isClickThrough)
    }
    logger.info(`[OverlayAdapter] Click-through: ${this.isClickThrough}`)
    return this.isClickThrough
  }

  /**
   * Set overlay opacity (0.5 - 1.0)
   */
  setOpacity(value) {
    const clamped = Math.max(0.1, Math.min(1.0, value))
    const rounded = Math.round(clamped * 100) / 100
    if (rounded === this.opacity) return this.opacity
    this.opacity = rounded
    store.set("overlayOpacity", this.opacity)

    if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
      this.overlayWindow.setOpacity(this.opacity)
      this.overlayWindow.webContents.send("opacity-changed", this.opacity)
    }

    // Sync slider on main window (CSS only, not Electron window opacity)
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send("overlay-opacity-changed", this.opacity)
    }

    logger.info(`[OverlayAdapter] Opacity set to ${this.opacity}`)
    return this.opacity
  }

  /**
   * Get current opacity
   */
  getOpacity() {
    return this.opacity
  }

  /**
   * Increase opacity by step
   */
  increaseOpacity(step = 0.05) {
    return this.setOpacity(this.opacity + step)
  }

  /**
   * Decrease opacity by step
   */
  decreaseOpacity(step = 0.05) {
    return this.setOpacity(this.opacity - step)
  }

  /**
   * Set up drag and drop handling
   */
  setupDragAndDrop() {
    if (!this.overlayWindow) return

    // Prevent default drag behaviors
    this.overlayWindow.webContents.on("dom-ready", () => {
      this.overlayWindow.webContents.executeJavaScript(`
        document.addEventListener('dragover', (e) => {
          e.preventDefault()
          e.stopPropagation()
          if (window.setDragState) window.setDragState(true)
        })
        document.addEventListener('dragleave', (e) => {
          e.preventDefault()
          e.stopPropagation()
          if (window.setDragState) window.setDragState(false)
        })
        document.addEventListener('drop', (e) => {
          e.preventDefault()
          e.stopPropagation()
          if (window.setDragState) window.setDragState(false)
        })
      `).catch(() => {})
    })
  }

  /**
   * Process dropped file
   */
  async processDroppedFile(filePath) {
    if (!fs.existsSync(filePath)) {
      logger.warn(`[OverlayAdapter] File not found: ${filePath}`)
      return null
    }

    const ext = path.extname(filePath).toLowerCase()
    const stats = fs.statSync(filePath)

    const fileInfo = {
      path: filePath,
      name: path.basename(filePath),
      extension: ext,
      size: stats.size,
      type: this.getFileType(ext)
    }

    logger.info(`[OverlayAdapter] Processing dropped file: ${fileInfo.name} (${fileInfo.type})`)

    // Send to renderer for processing
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send("file-dropped", fileInfo)
    }

    if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
      this.overlayWindow.webContents.send("file-dropped", fileInfo)
    }

    return fileInfo
  }

  /**
   * Get file type category
   */
  getFileType(ext) {
    const imageExts = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"]
    const docExts = [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"]
    const codeExts = [".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml"]
    const audioExts = [".mp3", ".wav", ".ogg", ".m4a", ".flac"]
    const videoExts = [".mp4", ".avi", ".mkv", ".mov", ".webm"]

    if (imageExts.includes(ext)) return "image"
    if (docExts.includes(ext)) return "document"
    if (codeExts.includes(ext)) return "code"
    if (audioExts.includes(ext)) return "audio"
    if (videoExts.includes(ext)) return "video"
    return "unknown"
  }

  /**
   * Register global hotkeys for overlay control
   */
  registerHotkeys() {
    const shortcuts = []

    // Cmd/Ctrl+Shift+M - Toggle microphone/system audio
    const micShortcut = globalShortcut.register("CommandOrControl+Shift+M", () => {
      logger.info("[Hotkey] Toggle microphone/system audio")
      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send("hotkey-toggle-mic")
      }
    })
    if (micShortcut) shortcuts.push("Cmd/Ctrl+Shift+M (Toggle Mic)")

    // Cmd/Ctrl+Shift+A - Voice input (push-to-talk style)
    const voiceShortcut = globalShortcut.register("CommandOrControl+Shift+A", () => {
      logger.info("[Hotkey] Start voice input")
      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send("hotkey-start-voice")
      }
    })
    if (voiceShortcut) shortcuts.push("Cmd/Ctrl+Shift+A (Voice Input)")

    // Cmd/Ctrl+Shift+S - Screenshot + OCR
    const screenshotShortcut = globalShortcut.register("CommandOrControl+Shift+S", () => {
      logger.info("[Hotkey] Screenshot capture")
      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send("hotkey-screenshot")
      }
    })
    if (screenshotShortcut) shortcuts.push("Cmd/Ctrl+Shift+S (Screenshot)")

    // Cmd/Ctrl+Shift+H - Toggle overlay visibility
    const overlayShortcut = globalShortcut.register("CommandOrControl+Shift+H", () => {
      logger.info("[Hotkey] Toggle overlay")
      this.toggleOverlay()
    })
    if (overlayShortcut) shortcuts.push("Cmd/Ctrl+Shift+H (Toggle Overlay)")

    // Cmd/Ctrl+Shift+O - Set opacity to minimum (10%)
    const opacityDownShortcut = globalShortcut.register("CommandOrControl+Shift+O", () => {
      this.setOpacity(0.1)
      logger.info(`[Hotkey] Opacity set to minimum (${Math.round(this.opacity * 100)}%)`)
    })
    if (opacityDownShortcut) shortcuts.push("Cmd/Ctrl+Shift+O (Opacity min)")

    // Cmd/Ctrl+Shift+P - Set opacity to maximum (100%)
    const opacityUpShortcut = globalShortcut.register("CommandOrControl+Shift+P", () => {
      this.setOpacity(1.0)
      logger.info(`[Hotkey] Opacity set to maximum (${Math.round(this.opacity * 100)}%)`)
    })
    if (opacityUpShortcut) shortcuts.push("Cmd/Ctrl+Shift+P (Opacity max)")

    // Cmd/Ctrl+Shift+T - Toggle click-through
    const clickThroughShortcut = globalShortcut.register("CommandOrControl+Shift+T", () => {
      const state = this.toggleClickThrough()
      logger.info(`[Hotkey] Click-through: ${state}`)
    })
    if (clickThroughShortcut) shortcuts.push("Cmd/Ctrl+Shift+T (Click-Through)")

    logger.info(`[OverlayAdapter] Registered ${shortcuts.length} hotkeys`)
    if (shortcuts.length > 0) {
      logger.info(`[OverlayAdapter] Hotkeys: ${shortcuts.join(", ")}`)
    }

    return shortcuts
  }

  /**
   * Set up IPC handlers
   */
  setupIpcHandlers() {
    // Get overlay state
    ipcMain.handle("overlay:state", () => {
      const hasOverlay = this.overlayWindow && !this.overlayWindow.isDestroyed()
      return {
        visible: hasOverlay && this.overlayWindow.isVisible(),
        opacity: this.opacity,
        clickThrough: this.isClickThrough,
        bounds: this.overlayBounds
      }
    })

    // Create/show overlay
    ipcMain.handle("overlay:show", () => {
      this.showOverlay()
      return true
    })

    // Hide overlay
    ipcMain.handle("overlay:hide", () => {
      this.hideOverlay()
      return true
    })

    // Toggle overlay
    ipcMain.handle("overlay:toggle", () => {
      return this.toggleOverlay()
    })

    // Set opacity
    ipcMain.handle("overlay:set-opacity", (_event, value) => {
      return this.setOpacity(value)
    })

    // Get opacity
    ipcMain.handle("overlay:get-opacity", () => {
      return this.getOpacity()
    })

    // Toggle click-through
    ipcMain.handle("overlay:toggle-click-through", () => {
      return this.toggleClickThrough()
    })

    // Process file
    ipcMain.handle("overlay:process-file", async (_event, filePath) => {
      return await this.processDroppedFile(filePath)
    })

    // Open file dialog
    ipcMain.handle("overlay:open-file-dialog", async () => {
      const result = await dialog.showOpenDialog({
        properties: ["openFile"],
        filters: [
          { name: "All Files", extensions: ["*"] },
          { name: "Images", extensions: ["png", "jpg", "jpeg", "gif"] },
          { name: "Documents", extensions: ["pdf", "txt", "md", "doc", "docx"] },
          { name: "Code", extensions: ["py", "js", "ts", "html", "css", "json"] }
        ]
      })

      if (!result.canceled && result.filePaths.length > 0) {
        return await this.processDroppedFile(result.filePaths[0])
      }
      return null
    })

    logger.info("[OverlayAdapter] IPC handlers registered")
  }

  /**
   * Clean up resources
   */
  destroy() {
    // Unregister shortcuts
    // Note: Global shortcuts are managed by the caller

    // Destroy overlay window
    if (this.overlayWindow && !this.overlayWindow.isDestroyed()) {
      this.overlayWindow.destroy()
      this.overlayWindow = null
    }

    logger.info("[OverlayAdapter] Destroyed")
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// MODULE EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

module.exports = { OverlayAdapter }