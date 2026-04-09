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

// Disable file logging in production for stealth mode
// Logs only go to console (memory), not to disk
if (app.isPackaged) {
  log.transports.file.level = false
}

const PLATFORM = process.platform  // 'win32' | 'darwin' | 'linux'
const logger = log
const store = new Store()

// Secure API key storage - encrypted using machine-specific key
const apiKeyStore = new Store({
  name: "secure-api-keys",
  encryptionKey: crypto.scryptSync(app.getPath("userData"), "ai-note-taker-salt-v1", 32).slice(0, 16).toString("hex").slice(0, 16)
})

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
let backendStopped = false  // true if user/App Quit initiated the stop — don't restart
let backendRestartAttempts = 0
let backendHealthCheckInterval = null
let backendStatus = "unknown" // "unknown" | "starting" | "ready" | "error" | "dead"
const MAX_BACKEND_RESTART_ATTEMPTS = 5
const BACKEND_RESTART_BASE_DELAY_MS = 1000
const BACKEND_HEALTH_CHECK_INTERVAL_MS = 5000

// Exponential backoff delay calculation
function getRestartDelayMs(attempt) {
  // 1s, 2s, 4s, 8s, 16s
  return BACKEND_RESTART_BASE_DELAY_MS * Math.pow(2, attempt - 1)
}

// Keep window above all others - Windows-specific aggressive approach
function ensureTopmost(w) {
  if (!w || w.isDestroyed()) return

  if (PLATFORM === "win32") {
    // Windows: use "normal" level which is actually the most reliable
    // "screen-saver" and other levels can behave unexpectedly
    // The key is to call it frequently and use moveTop()
    w.setAlwaysOnTop(true, "normal")
  } else if (PLATFORM === "darwin") {
    w.setAlwaysOnTop(true, "floating", 999)
  } else {
    w.setAlwaysOnTop(true)
  }

  w.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  // On Windows, also try to focus and raise
  if (PLATFORM === "win32" && !w.isFocused()) {
    w.focus()
  }
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
    // Note: alwaysOnTop is applied manually after window creation for more control
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
      allowRunningInsecureContent: false
    }
  }

  // titleBarStyle only works on macOS
  if (PLATFORM === "darwin") {
    windowOpts.titleBarStyle = "hidden"
    windowOpts.trafficLightPosition = { x: 12, y: 12 }
  }

  // Generate a new CSP nonce for this window
  const cspNonce = crypto.randomBytes(16).toString("base64")

  win = new BrowserWindow(windowOpts)

  // Store nonce on the window webContents for access in CSP headers
  win.cspNonce = cspNonce

  // Set always on top - "normal" level is most reliable on Windows
  // even though it sounds counter-intuitive
  if (PLATFORM === "win32") {
    win.setAlwaysOnTop(true, "normal")
  } else if (PLATFORM === "darwin") {
    win.setAlwaysOnTop(true, "floating", 999)
  }

  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  // In production, renderer is in extraResources; in dev, it's alongside electron/
  const isProd = app.isPackaged
  const rendererPath = isProd
    ? path.join(process.resourcesPath, "renderer", "index.html")
    : path.join(__dirname, "..", "renderer", "index.html")
  win.loadFile(rendererPath)

  // Inject nonce into all script and style tags after page loads
  win.webContents.on("did-finish-load", () => {
    if (!win || win.isDestroyed()) return
    const nonce = win.cspNonce
    if (!nonce) return
    win.webContents.executeJavaScript(`
      (function() {
        var nonce = ${JSON.stringify(nonce)};
        document.querySelectorAll('script').forEach(function(s) {
          if (!s.nonce) {
            s.nonce = nonce;
            if (s.src) s.setAttribute('nonce', nonce);
          }
        });
        document.querySelectorAll('style').forEach(function(s) {
          s.nonce = nonce;
          s.setAttribute('nonce', nonce);
        });
        var origCreateElement = document.createElement.bind(document);
        document.createElement = function(tagName) {
          var el = origCreateElement(tagName);
          if (tagName.toLowerCase() === 'script' || tagName.toLowerCase() === 'style') {
            Object.defineProperty(el, 'nonce', {
              get: function() { return nonce; },
              set: function() {},
              configurable: false
            });
          }
          return el;
        };
      })();
    `).catch(() => {})
  })

  win.on("resize", () => {
    // Only save bounds if not maximized
    if (!win.isMaximized()) saveBounds()
    // Notify renderer of maximize state change
    if (win?.webContents) {
      win.webContents.send("window:maximize-changed", { isMaximized: win.isMaximized() })
    }
  })
  win.on("move", () => {
    if (!win.isMaximized()) saveBounds()
  })
  win.on("maximize", () => {
    if (win?.webContents) {
      win.webContents.send("window:maximize-changed", { isMaximized: true })
    }
  })
  win.on("unmaximize", () => {
    if (win?.webContents) {
      win.webContents.send("window:maximize-changed", { isMaximized: false })
    }
  })

  // Set up window state tracking
  // Note: Window is already set to always-on-top, no need for aggressive re-assertion
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

// ==============================
// BACKEND HEALTH CHECK & SUPERVISION
// ==============================

function notifyRendererBackendStatus(status, data = {}) {
  backendStatus = status
  if (win?.webContents) {
    win.webContents.send("backend:status", { status, ...data })
  }
}

function startHealthCheck() {
  if (backendHealthCheckInterval) return
  backendHealthCheckInterval = setInterval(async () => {
    if (backendStopped) return
    const isHealthy = await isBackendRunning()
    if (!isHealthy && backendStatus === "ready") {
      logger.warn("[Backend] Health check failed - backend appears down")
      notifyRendererBackendStatus("error", { reason: "health_check_failed" })
      // Trigger restart
      if (!backendStopped && !backendProcess) {
        logger.info("[Backend] Triggering restart after health check failure")
        backendRestartAttempts++
        if (backendRestartAttempts <= MAX_BACKEND_RESTART_ATTEMPTS) {
          const delay = getRestartDelayMs(backendRestartAttempts)
          logger.info(`[Backend] Restarting in ${delay}ms (attempt ${backendRestartAttempts}/${MAX_BACKEND_RESTART_ATTEMPTS})`)
          setTimeout(() => startBackend(), delay)
        } else {
          logger.error("[Backend] Max restart attempts reached")
          notifyRendererBackendStatus("dead", { reason: "max_restarts" })
        }
      }
    } else if (isHealthy && backendStatus !== "ready") {
      notifyRendererBackendStatus("ready")
      backendRestartAttempts = 0 // Reset on successful health check
    }
  }, BACKEND_HEALTH_CHECK_INTERVAL_MS)
  logger.info("[Backend] Health check started (every %dms)", BACKEND_HEALTH_CHECK_INTERVAL_MS)
}

function stopHealthCheck() {
  if (backendHealthCheckInterval) {
    clearInterval(backendHealthCheckInterval)
    backendHealthCheckInterval = null
    logger.info("[Backend] Health check stopped")
  }
}

async function restartBackend() {
  logger.info("[Backend] Manual restart requested")
  backendRestartAttempts = 0 // Reset attempts for manual restart
  backendStopped = false
  if (backendProcess) {
    backendProcess.kill()
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  await startBackend()
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
  // If a user-initiated quit was requested, don't restart
  if (backendStopped) return

  // If a process exists but is actually dead, clear it so we can respawn
  if (backendProcess && backendProcess.exitCode !== null && backendProcess.exitCode !== undefined) {
    const pid = backendProcess.pid
    try { process.kill(pid, 0) } catch {
      // PID is dead or orphaned — clear the handle
      logger.info("[Backend] Previous process %d is gone, clearing handle", pid)
      backendProcess = null
    }
  }

  if (await isBackendRunning()) {
    logger.info("[Backend] Already running on port 8000, skipping spawn")
    backendRestartAttempts = 0
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

  notifyRendererBackendStatus("starting")
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
    backendProcess = null

    // Don't restart if app is quitting or was intentionally stopped
    if (backendStopped) return

    // Unexpected crash — attempt restart with exponential backoff
    backendRestartAttempts++
    if (backendRestartAttempts <= MAX_BACKEND_RESTART_ATTEMPTS) {
      const delay = getRestartDelayMs(backendRestartAttempts)
      notifyRendererBackendStatus("error", {
        reason: "crashed",
        exitCode: code,
        restartAttempt: backendRestartAttempts,
        maxAttempts: MAX_BACKEND_RESTART_ATTEMPTS,
        retryInMs: delay
      })
      logger.info(`[Backend] Restarting in ${delay}ms (attempt ${backendRestartAttempts}/${MAX_BACKEND_RESTART_ATTEMPTS})`)
      setTimeout(() => {
        startBackend()
      }, delay)
    } else {
      logger.error("[Backend] Max restart attempts reached — giving up. Restart the app to retry.")
      notifyRendererBackendStatus("dead", { reason: "max_restarts", exitCode: code })
    }
  })

  backendProcess.on("error", (err) => {
    logger.error("[Backend] Spawn error: %s", err.message)
    notifyRendererBackendStatus("error", { reason: "spawn_error", message: err.message })
  })

  // Start health check monitoring
  startHealthCheck()
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
  if (w) {
    // Complete stealth minimize - no tray, no traces
    w.setSkipTaskbar(true)
    w.hide()
    // Destroy tray if exists to remove from system tray
    stealth.destroyTray()
    // Clear screenshot buffer for privacy
    screenshotBuffer = []
    // Stop auto-screenshot while minimized
    if (autoScreenshotInterval) {
      clearInterval(autoScreenshotInterval)
      autoScreenshotInterval = null
    }
  }
})

ipcMain.handle("window:toggle-maximize", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (!w) return { isMaximized: false }
  w.setResizable(true)
  const maxed = w.isMaximized()
  if (maxed) {
    w.unmaximize()
    // Restore to previous size after unmaximize
    const savedBounds = store.get("windowBounds")
    if (savedBounds) {
      w.setSize(savedBounds.width, savedBounds.height)
    }
  } else {
    // Save current bounds before maximizing
    saveBounds()
    w.maximize()
  }
  return { isMaximized: w.isMaximized() }
})

ipcMain.handle("window:is-maximized", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  return { isMaximized: w ? w.isMaximized() : false }
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

// Backend supervision IPC handlers
ipcMain.handle("backend:restart", async () => {
  await restartBackend()
  return { success: true }
})

ipcMain.handle("backend:status", async () => {
  const isHealthy = await isBackendRunning()
  return {
    status: isHealthy ? "ready" : backendStatus,
    processRunning: !!backendProcess,
    restartAttempts: backendRestartAttempts,
    maxAttempts: MAX_BACKEND_RESTART_ATTEMPTS
  }
})

ipcMain.handle("window:restore", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (!w) return
  // Restore from stealth - show in taskbar again
  w.setSkipTaskbar(false)
  if (w.isMinimized()) w.restore()
  const savedBounds = store.get("windowBounds")
  if (savedBounds) {
    w.setSize(savedBounds.width, savedBounds.height)
  } else {
    w.setSize(960, 720)
  }
  w.show()
  w.focus()
  w.moveTop()
  w.setAlwaysOnTop(true, "normal")
  // Restart auto-screenshot if it was enabled
  const savedAutoSS = store.get("autoScreenshotEnabled", false)
  if (savedAutoSS && !autoScreenshotInterval) {
    const interval = store.get("autoScreenshotInterval", 5000)
    startAutoScreenshot(interval)
    autoScreenshotEnabled = true
  }
})

ipcMain.handle("window:force-top", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (!w) return
  w.moveTop()
  w.focus()
  w.setAlwaysOnTop(true, "normal")
  return true
})

ipcMain.handle("window:set-stealth-mode", (_event, enabled) => {
  if (enabled) stealth.enable()
  else stealth.disable()
  // Return both stealth mode AND capture protection state so renderer can sync accurately
  return { enabled: stealth.isEnabled(), undetectable: stealth.isUndetectable() }
})

ipcMain.handle("window:set-undetectable", (_event, enabled) => {
  stealth.setUndetectable(enabled)
  // Clear screenshot buffer when entering stealth mode (privacy)
  if (enabled) {
    screenshotBuffer = []
    logger.info("[Stealth] Screenshot buffer cleared for privacy")
  }
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
    // Generate random salt for each encryption (unique per file)
    const salt = crypto.randomBytes(16).toString("hex")
    const key = crypto.scryptSync(encryptionKey, salt, 32)
    const iv = crypto.randomBytes(16)
    const cipher = crypto.createCipheriv("aes-256-cbc", key, iv)
    let encrypted = cipher.update(content, "utf8", "hex")
    encrypted += cipher.final("hex")
    // Store salt, iv, and encrypted data - salt is needed for decryption
    dataToSave = JSON.stringify({ salt: salt, iv: iv.toString("hex"), data: encrypted })
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

// File import with optional decryption
ipcMain.handle("dialog:import-file", async (_event, { filePath, encryptionKey }) => {
  try {
    const content = fs.readFileSync(filePath, "utf8")
    const data = JSON.parse(content)

    // Check if file is encrypted
    if (data.salt && data.iv && data.data) {
      if (!encryptionKey) {
        return { error: "File is encrypted - password required" }
      }
      // Decrypt using stored salt and IV
      const salt = data.salt
      const iv = Buffer.from(data.iv, "hex")
      const key = crypto.scryptSync(encryptionKey, salt, 32)
      const decipher = crypto.createDecipheriv("aes-256-cbc", key, iv)
      let decrypted = decipher.update(data.data, "hex", "utf8")
      decrypted += decipher.final("utf8")
      return { content: decrypted }
    }

    // Not encrypted - return raw content
    return { content: content }
  } catch (err) {
    logger.error("File import error:", err.message)
    return { error: err.message }
  }
})

// Platform info for renderer
ipcMain.handle("app:platform", () => PLATFORM)

// ======================================
// SECURE API KEY STORAGE (P1 Privacy)
// ======================================
// Store API keys encrypted, never in .env
ipcMain.handle("apiKey:save", (_event, { provider, apiKey }) => {
  try {
    apiKeyStore.set(`apiKey.${provider}`, apiKey)
    logger.info(`[API Key] Saved encrypted key for provider: ${provider}`)
    return { success: true }
  } catch (err) {
    logger.error("[API Key] Save error:", err.message)
    return { success: false, error: err.message }
  }
})

ipcMain.handle("apiKey:get", (_event, provider) => {
  try {
    const key = apiKeyStore.get(`apiKey.${provider}`, null)
    return { apiKey: key }
  } catch (err) {
    logger.error("[API Key] Get error:", err.message)
    return { apiKey: null, error: err.message }
  }
})

// HTTP endpoint for backend to request API keys
const http = require("http")
const API_KEY_SERVER_PORT = 18000 // Separate port for secure key exchange

function startApiKeyServer() {
  const server = http.createServer(async (req, res) => {
    // Enable CORS for localhost only
    res.setHeader("Access-Control-Allow-Origin", "http://127.0.0.1:8000")
    res.setHeader("Access-Control-Allow-Methods", "POST")
    res.setHeader("Access-Control-Allow-Headers", "Content-Type")

    if (req.method === "OPTIONS") {
      res.writeHead(200)
      res.end()
      return
    }

    if (req.method === "POST" && req.url === "/get-key") {
      let body = ""
      req.on("data", chunk => body += chunk)
      req.on("end", () => {
        try {
          const { provider } = JSON.parse(body)
          const apiKey = apiKeyStore.get(`apiKey.${provider}`, null)
          res.writeHead(200, { "Content-Type": "application/json" })
          res.end(JSON.stringify({ apiKey }))
          logger.info(`[API Key Server] Key requested for ${provider}, found: ${!!apiKey}`)
        } catch (err) {
          res.writeHead(400, { "Content-Type": "application/json" })
          res.end(JSON.stringify({ error: err.message }))
        }
      })
    } else {
      res.writeHead(404)
      res.end()
    }
  })

  server.listen(API_KEY_SERVER_PORT, "127.0.0.1", () => {
    logger.info(`[API Key Server] Running on port ${API_KEY_SERVER_PORT}`)
  })
}

// Start the secure key server when app is ready
app.whenReady().then(() => {
  startApiKeyServer()
})

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

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    // Apply CSP to file:// protocol (renderer)
    const headers = { ...details.responseHeaders }
    // Use the window's CSP nonce for this request
    let nonce = ""
    if (details.url.includes("file://")) {
      // Match to the correct window's nonce
      const windows = BrowserWindow.getAllWindows()
      for (const w of windows) {
        if (!w.isDestroyed() && w.cspNonce) {
          // Use the first available nonce (for single-window app)
          nonce = w.cspNonce
          break
        }
      }
    }
    // T25: Tightened CSP — restrict connect-src to known origins, remove http: from img/media
    const csp = nonce
      ? `default-src 'self'; script-src 'self' 'nonce-${nonce}'; style-src 'self' 'nonce-${nonce}'; img-src 'self' data: blob: https:; font-src 'self' data:; connect-src 'self' ws://localhost:* http://localhost:* https://localhost:* http://127.0.0.1:* https://127.0.0.1:* wss: https:; media-src 'self' mediastream: blob: https:`
      : `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob: https:; font-src 'self' data:; connect-src 'self' ws://localhost:* http://localhost:* https://localhost:* http://127.0.0.1:* https://127.0.0.1:* wss: https:; media-src 'self' mediastream: blob: https:`
    headers["Content-Security-Policy"] = [csp]
    // T26: Removed Access-Control-Allow-Origin: ["*"] — backend handles CORS
    callback({ responseHeaders: headers })
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

  // Machine lock detection - clear sensitive data when screen locks
  const { systemPreferences } = require("electron")
  if (PLATFORM === "darwin") {
    systemPreferences.subscribeNotification("com.apple.screenIsLocked", () => {
      screenshotBuffer = []
      logger.info("[Privacy] Screen locked - screenshot buffer cleared")
    })
  }
  // Windows lock detection via power monitor
  const { powerMonitor } = require("electron")
  powerMonitor.on("lock-screen", () => {
    screenshotBuffer = []
    logger.info("[Privacy] Screen locked - screenshot buffer cleared")
  })
  powerMonitor.on("suspend", () => {
    screenshotBuffer = []
    logger.info("[Privacy] System suspended - screenshot buffer cleared")
  })

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
      if (win) {
        win.restore()
        win.show()
        win.focus()
        win.moveTop()
        win.setAlwaysOnTop(true, "normal")
      }
    } else {
      stealth.enable()
      store.set("stealthState", true)
      // Re-assert always on top after stealth enable
      if (win) {
        win.setAlwaysOnTop(true, "normal")
      }
    }
    if (win?.webContents) win.webContents.send("stealth:state-changed", {
      enabled: stealth.isEnabled(),
      undetectable: stealth.isUndetectable()
    })
  })

  // Alt+Space — hide/show (stealth toggle)
  registerShortcut("Alt+Space", "hide/show", () => {
    if (!win) return
    if (win.isVisible()) {
      // Hide completely - no taskbar, no tray, no traces
      win.setSkipTaskbar(true)
      win.hide()
      stealth.destroyTray()
      // Clear screenshot buffer for privacy
      screenshotBuffer = []
      // Stop auto-screenshot
      if (autoScreenshotInterval) {
        clearInterval(autoScreenshotInterval)
        autoScreenshotInterval = null
      }
    } else {
      // Restore - show in taskbar again
      win.setSkipTaskbar(false)
      win.restore()
      win.show()
      win.focus()
      win.moveTop()
      win.setAlwaysOnTop(true, "normal")
      // Restart auto-screenshot if enabled
      const savedAutoSS = store.get("autoScreenshotEnabled", false)
      if (savedAutoSS && !autoScreenshotInterval) {
        const interval = store.get("autoScreenshotInterval", 5000)
        startAutoScreenshot(interval)
        autoScreenshotEnabled = true
      }
    }
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
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else if (win) {
      win.show()
      win.focus()
      // Aggressively bring to absolute front
      win.moveTop()
      win.setAlwaysOnTop(true, "normal")
    }
  })
})

app.on("will-quit", () => {
  globalShortcut.unregisterAll()
  backendStopped = true  // prevent crash-restart loop during shutdown
  stopHealthCheck()
  if (backendProcess) backendProcess.kill()
})

app.on("window-all-closed", () => {
  // On macOS, apps typically stay open until explicitly quit (Cmd+Q)
  if (PLATFORM !== "darwin") app.quit()
})
