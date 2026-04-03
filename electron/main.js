const { app, BrowserWindow, globalShortcut, ipcMain, session, desktopCapturer } = require("electron")
const path = require("path")
const { spawn } = require("child_process")
const os = require("os")
const stealth = require("./stealth")
const log = require("electron-log/main")
const Store = require("electron-store")
const { autoUpdater } = require("electron-updater")
const fs = require("fs")
const crypto = require("crypto")

log.initialize()
log.transports.file.level = "info"
log.transports.console.level = "debug"
log.transports.file.maxSize = 5 * 1024 * 1024

const PLATFORM = process.platform  // 'win32' | 'darwin' | 'linux'
const logger = log
const store = new Store()

// appData path is cross-platform via Electron API
const appDataDir = path.join(app.getPath("userData"), "ai-note-taker-data")
app.setPath("userData", appDataDir)
app.setPath("sessionData", appDataDir)

const conversationsDir = path.join(appDataDir, "conversations")

function ensureConversationsDir() {
  if (!fs.existsSync(conversationsDir)) {
    fs.mkdirSync(conversationsDir, { recursive: true })
  }
}

let win
let backendProcess = null

// Keep window above all others by re-applying monitor level after any show operation
function ensureTopmost(w) {
  if (!w || PLATFORM !== "win32") return
  w.setAlwaysOnTop(true, "monitor", 2147483647)
}

// ======================================
// AUTO SCREENSHOT STATE
// ======================================
let screenshotBuffer = []        // ring buffer of base64 PNGs
const SCREENSHOT_BUFFER_MAX = 5
let autoScreenshotEnabled = false
let autoScreenshotInterval = null

process.on("uncaughtException", (err) => {
  logger.error("Uncaught exception: %s", err.stack || err.message)
})

process.on("unhandledRejection", (reason) => {
  logger.error("Unhandled rejection: %s", String(reason))
})

// ==============================
// WINDOW STATE
// ==============================
const DEFAULT_BOUNDS = { width: 420, height: 320, x: undefined, y: undefined }

function validateBounds(bounds) {
  if (!bounds.width || bounds.width < 360) bounds.width = DEFAULT_BOUNDS.width
  if (!bounds.height || bounds.height < 280) bounds.height = DEFAULT_BOUNDS.height

  const { screen } = require("electron")
  const displays = screen.getAllDisplays()
  const windowCenter = {
    x: bounds.x !== undefined ? bounds.x + bounds.width / 2 : bounds.x,
    y: bounds.y !== undefined ? bounds.y + bounds.height / 2 : bounds.y
  }

  let onScreen = false
  for (const display of displays) {
    const { x, y, width, height } = display.bounds
    if (windowCenter.x >= x && windowCenter.x <= x + width &&
        windowCenter.y >= y && windowCenter.y <= y + height) {
      onScreen = true
      break
    }
  }

  if (bounds.x === undefined || bounds.y === undefined || !onScreen) {
    const primary = screen.getPrimaryDisplay()
    const { width: screenWidth, height: screenHeight } = primary.workAreaSize
    bounds.x = Math.round((screenWidth - bounds.width) / 2)
    bounds.y = Math.round((screenHeight - bounds.height) / 2)
  }

  return bounds
}

function saveBounds() {
  if (win && !win.isMaximized() && !win.isMinimized()) {
    store.set("windowBounds", win.getBounds())
  }
}

// ==============================
// WINDOW CREATION
// ==============================
function createWindow() {
  const savedBounds = store.get("windowBounds", DEFAULT_BOUNDS)
  const bounds = validateBounds(savedBounds)

  // Platform-specific window options
  const windowOpts = {
    width: bounds.width,
    height: bounds.height,
    x: bounds.x,
    y: bounds.y,
    minWidth: 360,
    minHeight: 280,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  }

  // titleBarStyle only works on macOS
  if (PLATFORM === "darwin") {
    windowOpts.titleBarStyle = "hidden"
    windowOpts.trafficLightPosition = { x: 12, y: 12 }
  }

  // Windows: use "monitor" level — above all normal windows, PIP, fullscreen apps
  // This is the highest normal window level, only below system notifications
  win = new BrowserWindow(windowOpts)
  if (PLATFORM === "win32") {
    win.setAlwaysOnTop(true, "monitor", 2147483647)
  }

  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  // In production, renderer is in extraResources; in dev, it's alongside electron/
  const isProd = app.isPackaged
  const rendererPath = isProd
    ? path.join(process.resourcesPath, "renderer", "index.html")
    : path.join(__dirname, "..", "renderer", "index.html")
  win.loadFile(rendererPath)

  win.on("resize", saveBounds)
  win.on("move", saveBounds)
  stealth.init(win)
  ensureTopmost(win)
}

// ======================================
// AUTO SCREENSHOT
// ======================================
async function captureAutoScreenshot() {
  try {
    const sources = await desktopCapturer.getSources({
      types: ["screen"],
      thumbnailSize: { width: 1280, height: 720 }
    })
    if (sources && sources.length > 0) {
      const b64 = sources[0].thumbnail.toPNG().toString("base64")
      screenshotBuffer.push(b64)
      if (screenshotBuffer.length > SCREENSHOT_BUFFER_MAX) {
        screenshotBuffer.shift()
      }
      logger.info("[AutoScreenshot] Captured, buffer size: %d", screenshotBuffer.length)
    }
  } catch (e) {
    logger.warn("[AutoScreenshot] Capture failed:", e.message)
  }
}

function startAutoScreenshot(intervalMs) {
  intervalMs = intervalMs || 5000
  if (autoScreenshotInterval) clearInterval(autoScreenshotInterval)
  autoScreenshotInterval = setInterval(captureAutoScreenshot, intervalMs)
  captureAutoScreenshot()
  logger.info("[AutoScreenshot] Started with interval %dms", intervalMs)
}

function stopAutoScreenshot() {
  if (autoScreenshotInterval) {
    clearInterval(autoScreenshotInterval)
    autoScreenshotInterval = null
    logger.info("[AutoScreenshot] Stopped")
  }
}

// ==============================
// BACKEND PROCESS
// ==============================
async function isBackendRunning() {
  try {
    const http = require("http")
    return await new Promise((resolve) => {
      const req = http.get("http://127.0.0.1:8000/health", (res) => resolve(res.statusCode === 200))
      req.on("error", () => resolve(false))
      req.setTimeout(1000, () => { req.destroy(); resolve(false) })
    })
  } catch { return false }
}

function getPythonExecutable() {
  const isProd = app.isPackaged

  // In dev mode, try common venv paths for current platform
  if (!isProd) {
    const devPaths = [
      // Windows dev
      path.join(__dirname, "..", "AINT_Venv", "Scripts", "python.exe"),
      // macOS/Linux dev (relative)
      path.join(__dirname, "..", "AINT_Venv", "bin", "python"),
      // Parent-relative Windows
      path.join(__dirname, "..", "..", "AINT_Venv", "Scripts", "python.exe"),
      // Parent-relative macOS/Linux
      path.join(__dirname, "..", "..", "AINT_Venv", "bin", "python"),
    ]
    for (const p of devPaths) {
      try {
        fs.accessSync(p, fs.constants.X_OK)
        return p
      } catch { /* try next */ }
    }
  }

  // In production, look in extraResources (process.resourcesPath)
  if (isProd) {
    const venvBin = PLATFORM === "win32" ? "Scripts" : "bin"
    const candidates = [
      path.join(process.resourcesPath, "AINT_Venv", venvBin, PLATFORM === "win32" ? "python.exe" : "python"),
    ]
    for (const p of candidates) {
      try {
        fs.accessSync(p, fs.constants.X_OK)
        return p
      } catch { /* try next */ }
    }
  }

  // Fallback to system python
  return PLATFORM === "win32" ? "python" : "python3"
}

async function startBackend() {
  if (await isBackendRunning()) {
    logger.info("[Backend] Already running on port 8000, skipping spawn")
    return
  }

  const pythonExe = getPythonExecutable()
  const isProd = app.isPackaged
  const backendDir = isProd
    ? path.join(process.resourcesPath, "backend")
    : path.join(__dirname, "..", "backend")

  // Verify backend main.py exists
  const mainPy = path.join(backendDir, "main.py")
  if (!fs.existsSync(mainPy)) {
    logger.error("[Backend] main.py not found at:", mainPy)
    return
  }

  const env = {
    ...process.env,
    PYTHONPATH: backendDir
  }

  const spawnOpts = {
    cwd: backendDir,
    env: env,
    stdio: ["ignore", "pipe", "pipe"]
  }

  // windowsHide only works on Windows
  if (PLATFORM === "win32") {
    spawnOpts.windowsHide = true
  }

  logger.info(`[Backend] Starting: ${pythonExe} in ${backendDir}`)

  backendProcess = spawn(pythonExe, [
    "-m", "uvicorn", "main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--log-level", "info"
  ], spawnOpts)

  backendProcess.stdout.on("data", (data) => {
    logger.info("[Backend] %s", data.toString().trim())
  })

  backendProcess.stderr.on("data", (data) => {
    logger.error("[Backend] %s", data.toString().trim())
  })

  backendProcess.on("close", (code) => {
    logger.info("[Backend] Process exited with code %s", code)
  })

  backendProcess.on("error", (err) => {
    logger.error("[Backend] Spawn error: %s", err.message)
  })
}

// ==============================
// IPC HANDLERS
// ==============================
ipcMain.handle("store:get", (_event, key) => store.get(key))
ipcMain.handle("store:set", (_event, key, value) => { store.set(key, value) })

ipcMain.handle("conversation:save", (_event, conversation) => {
  ensureConversationsDir()
  const id = conversation.id || crypto.randomUUID()
  const now = Date.now()
  const record = {
    ...conversation,
    id,
    createdAt: conversation.createdAt || now,
    updatedAt: now
  }
  const filePath = path.join(conversationsDir, `${id}.json`)
  fs.writeFileSync(filePath, JSON.stringify(record, null, 2), "utf-8")
  return record
})

ipcMain.handle("conversation:load", (_event, id) => {
  const filePath = path.join(conversationsDir, `${id}.json`)
  if (!fs.existsSync(filePath)) return null
  return JSON.parse(fs.readFileSync(filePath, "utf-8"))
})

ipcMain.handle("conversation:list", () => {
  ensureConversationsDir()
  return fs.readdirSync(conversationsDir)
    .filter(f => f.endsWith(".json"))
    .map(f => {
      const data = JSON.parse(fs.readFileSync(path.join(conversationsDir, f), "utf-8"))
      return {
        id: data.id,
        title: data.title,
        pinned: data.pinned || false,
        createdAt: data.createdAt,
        updatedAt: data.updatedAt,
        messageCount: data.messages ? data.messages.length : 0
      }
    })
})

ipcMain.handle("conversation:delete", (_event, id) => {
  const filePath = path.join(conversationsDir, `${id}.json`)
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath)
    return true
  }
  return false
})

ipcMain.handle("window:minimize", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (w) w.hide()
})

ipcMain.handle("window:toggle-maximize", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (!w) return { isMaximized: false }
  w.setResizable(true)
  const maxed = w.isMaximized()
  if (maxed) w.unmaximize()
  else w.maximize()
  return { isMaximized: w.isMaximized() }
})

ipcMain.handle("window:close", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (w) w.close()
})

ipcMain.handle("window:resize", (_event, width, height) => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (w) {
    const [cw, ch] = w.getSize()
    w.setSize(width || cw, height || ch)
  }
})

ipcMain.handle("window:restore", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (!w) return
  if (w.isMinimized()) w.restore()
  const savedBounds = store.get("windowBounds")
  if (savedBounds) {
    w.setSize(savedBounds.width, savedBounds.height)
  } else {
    w.setSize(960, 720)
  }
  w.show()
  w.focus()
  ensureTopmost(w)
})

ipcMain.handle("window:set-stealth-mode", (_event, enabled) => {
  if (enabled) stealth.enable()
  else stealth.disable()
  return { enabled: stealth.isEnabled(), undetectable: stealth.isUndetectable() }
})

ipcMain.handle("window:set-undetectable", (_event, enabled) => {
  stealth.setUndetectable(enabled)
  return { undetectable: stealth.isUndetectable() }
})

ipcMain.handle("window:capture-screenshot", async () => {
  try {
    const sources = await desktopCapturer.getSources({
      types: ["screen"],
      thumbnailSize: { width: 1920, height: 1080 }
    })
    if (!sources || sources.length === 0) {
      logger.warn("[Screenshot] No screen sources found")
      return null
    }
    // Get the primary screen (first source)
    const primarySource = sources[0]
    if (!primarySource.thumbnail || primarySource.thumbnail.isEmpty()) {
      logger.warn("[Screenshot] Screen capture returned empty thumbnail")
      return null
    }
    const base64 = primarySource.thumbnail.toPNG().toString("base64")
    logger.info("[Screenshot] Captured screen, size: %d bytes", base64.length)
    return base64
  } catch (e) {
    logger.error("[Screenshot] error:", e)
    return null
  }
})

ipcMain.handle("app:open-logs", () => {
  const { shell } = require("electron")
  shell.openPath(path.dirname(log.transports.file.getFile().path))
})

ipcMain.handle("clipboard:write", async (_event, text) => {
  require("electron").clipboard.writeText(text)
  return true
})

// Auto-updater handlers
ipcMain.handle("updater:check", async () => {
  try {
    const result = await autoUpdater.checkForUpdates()
    return { available: !!result?.updateInfo, info: result?.updateInfo || null }
  } catch (e) {
    return { available: false, error: e.message }
  }
})

ipcMain.handle("updater:download", async () => {
  try {
    await autoUpdater.downloadUpdate()
    return { started: true }
  } catch (e) {
    return { started: false, error: e.message }
  }
})

ipcMain.handle("updater:install", () => {
  autoUpdater.quitAndInstall(false, true)
})

// File save dialog
ipcMain.handle("dialog:save-file", async (_event, { defaultPath, filters, content, encryptionKey }) => {
  const { dialog, BrowserWindow: BW } = require("electron")

  let dataToSave = content
  let actualFilters = filters

  if (encryptionKey) {
    const key = crypto.scryptSync(encryptionKey, "salt", 32)
    const iv = crypto.randomBytes(16)
    const cipher = crypto.createCipheriv("aes-256-cbc", key, iv)
    let encrypted = cipher.update(content, "utf8", "hex")
    encrypted += cipher.final("hex")
    dataToSave = JSON.stringify({ iv: iv.toString("hex"), data: encrypted })
    actualFilters = filters.map(f => ({ ...f, name: f.name + " (Encrypted)" }))
  }

  const winRef = BrowserWindow.getFocusedWindow()
  const result = await dialog.showSaveDialog(winRef, {
    defaultPath,
    filters: actualFilters,
    properties: ["createDirectory", "showOverwriteConfirmation"]
  })

  if (result.canceled || !result.filePath) return { success: false }

  try {
    fs.writeFileSync(result.filePath, dataToSave, "utf8")
    return { success: true, filePath: result.filePath }
  } catch (err) {
    logger.error("File save error:", err.message)
    return { success: false, error: err.message }
  }
})

// Platform info for renderer
ipcMain.handle("app:platform", () => PLATFORM)

// ======================================
// SCREENSHOT IPC HANDLERS
// ======================================
ipcMain.handle("overlay:get-latest-screenshot", () => {
  return screenshotBuffer.length > 0 ? screenshotBuffer[screenshotBuffer.length - 1] : null
})

ipcMain.handle("auto-screenshot:set-enabled", (_event, enabled, intervalMs) => {
  autoScreenshotEnabled = enabled
  if (enabled) {
    startAutoScreenshot(intervalMs || 5000)
  } else {
    stopAutoScreenshot()
  }
  store.set("autoScreenshotEnabled", enabled)
  store.set("autoScreenshotInterval", intervalMs || 5000)
  return { enabled, intervalMs: enabled ? (intervalMs || 5000) : 0 }
})

ipcMain.handle("auto-screenshot:get-status", () => {
  return {
    enabled: autoScreenshotEnabled,
    intervalMs: autoScreenshotInterval ? (store.get("autoScreenshotInterval") || 5000) : 0
  }
})

// ==============================
// APP LIFECYCLE
// ==============================
app.whenReady().then(async () => {
  // Auto-updater — only enable on win32/mac for now; Linux works too but is less tested
  autoUpdater.logger = logger
  autoUpdater.autoDownload = false
  autoUpdater.autoInstallOnAppQuit = true

  autoUpdater.on("update-available", (info) => {
    logger.info("[Updater] update available:", info.version)
    if (win?.webContents) win.webContents.send("updater:available", info)
  })
  autoUpdater.on("update-not-available", () => {
    logger.info("[Updater] no update available")
  })
  autoUpdater.on("download-progress", (progress) => {
    if (win?.webContents) win.webContents.send("updater:progress", progress)
  })
  autoUpdater.on("update-downloaded", (info) => {
    logger.info("[Updater] downloaded:", info.version)
    if (win?.webContents) win.webContents.send("updater:downloaded", info)
  })
  autoUpdater.on("error", (e) => {
    logger.error("[Updater] error:", e.message)
  })

  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(permission === "media")
  })

  session.defaultSession.webRequest.onBeforeSendHeaders((details, callback) => {
    if (details.url.includes("file://")) {
      details.requestHeaders["Cache-Control"] = "no-cache, no-store, must-revalidate"
      details.requestHeaders["Pragma"] = "no-cache"
      details.requestHeaders["Expires"] = "0"
    }
    callback({ requestHeaders: details.requestHeaders })
  })

  await startBackend()
  createWindow()

  const savedStealthState = store.get("stealthState", false)
  if (savedStealthState) stealth.enable()

  // Restore auto-screenshot setting
  const savedAutoSS = store.get("autoScreenshotEnabled", false)
  if (savedAutoSS) {
    const interval = store.get("autoScreenshotInterval", 5000)
    startAutoScreenshot(interval)
    autoScreenshotEnabled = true
  }

  // Global shortcuts — all use CommandOrControl (works on Mac=Cmd, Win/Linux=Ctrl)
  function registerShortcut(accelerator, name, fn) {
    const ok = globalShortcut.register(accelerator, fn)
    if (ok) logger.info(`[Shortcut] ${accelerator} -> ${name}`)
    else logger.warn(`[Shortcut] Failed: ${accelerator} (may conflict)`)
  }

  // Alt+D — toggle stealth
  registerShortcut("Alt+D", "toggle stealth", () => {
    if (stealth.isEnabled()) {
      stealth.disable()
      store.set("stealthState", false)
      if (win) { win.restore(); win.show(); win.focus(); ensureTopmost(win) }
    } else {
      stealth.enable()
      store.set("stealthState", true)
    }
    if (win?.webContents) win.webContents.send("stealth:state-changed", {
      enabled: stealth.isEnabled(),
      undetectable: stealth.isUndetectable()
    })
  })

  // Alt+Space — hide/show
  registerShortcut("Alt+Space", "hide/show", () => {
    if (!win) return
    if (win.isVisible()) win.hide()
    else { win.restore(); win.show(); win.focus(); ensureTopmost(win) }
  })

  // Ctrl+Arrow — move window
  const moveBy = (dx, dy) => {
    if (!win) return
    const [x, y] = win.getPosition()
    win.setPosition(x + dx, y + dy)
  }
  registerShortcut("CommandOrControl+Left",  "move left",  () => moveBy(-50, 0))
  registerShortcut("CommandOrControl+Right", "move right", () => moveBy(50, 0))
  registerShortcut("CommandOrControl+Up",    "move up",    () => moveBy(0, -50))
  registerShortcut("CommandOrControl+Down",   "move down",  () => moveBy(0, 50))

  // Ctrl+Enter — trigger AI (works from any app, not just focused window)
  registerShortcut("CommandOrControl+Enter", "trigger ai", () => {
    if (win?.webContents) {
      win.webContents.send("trigger-ai", {})
    }
  })

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
    else { win?.show(); win?.focus(); ensureTopmost(win) }
  })
})

app.on("will-quit", () => {
  globalShortcut.unregisterAll()
  if (backendProcess) backendProcess.kill()
})

app.on("window-all-closed", () => {
  // On macOS, apps typically stay open until explicitly quit (Cmd+Q)
  if (PLATFORM !== "darwin") app.quit()
})
