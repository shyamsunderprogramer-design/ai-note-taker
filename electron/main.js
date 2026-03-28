const { app, BrowserWindow, globalShortcut, ipcMain, session } = require("electron")
const path = require("path")
const { spawn } = require("child_process")
const stealth = require("./stealth")
const log = require("electron-log/main")
const Store = require("electron-store")
const fs = require("fs")
const crypto = require("crypto")

log.initialize()
log.transports.file.level = "info"
log.transports.console.level = "debug"
log.transports.file.maxSize = 5 * 1024 * 1024

const logger = log
const store = new Store()

const appDataDir = path.join(__dirname, "../electron-data")
app.setPath("userData", appDataDir)
app.setPath("sessionData", appDataDir)

const conversationsDir = path.join(appDataDir, "conversations")

// Ensure conversations directory exists
function ensureConversationsDir() {
  if (!fs.existsSync(conversationsDir)) {
    fs.mkdirSync(conversationsDir, { recursive: true })
  }
}

let win
let backendProcess = null

// Global exception handler
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
  // Ensure window has valid dimensions
  if (!bounds.width || bounds.width < 360) bounds.width = DEFAULT_BOUNDS.width
  if (!bounds.height || bounds.height < 280) bounds.height = DEFAULT_BOUNDS.height

  // Ensure window is on a visible screen
  const displays = require("electron").screen.getAllDisplays()
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

  // If no saved position or not on screen, center on primary display
  if (bounds.x === undefined || bounds.y === undefined || !onScreen) {
    const primary = require("electron").screen.getPrimaryDisplay()
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

  win = new BrowserWindow({
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
  })

  // Keep on top at appropriate level
  win.setAlwaysOnTop(true, "screen-saver", 1)
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  win.loadFile(path.join(__dirname, "../renderer/index.html"))
  win.webContents.openDevTools({ mode: "detach" })

  // Save window bounds on move/resize
  win.on("resize", saveBounds)
  win.on("move", saveBounds)

  // Initialize stealth after window loads
  stealth.init(win)
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

async function startBackend() {
  // Skip if backend already running
  if (await isBackendRunning()) {
    logger.info("[Backend] Already running on port 8000, skipping spawn")
    return
  }

  // Try common venv paths, then fall back to 'python' on PATH
  const venvPaths = [
    path.join(__dirname, "../AINT_Venv/Scripts/python.exe"),
    path.join(__dirname, "../../AINT_Venv/Scripts/python.exe"),
    "python",
    "python3"
  ]
  const pythonExe = venvPaths.find(p => {
    try { require("fs").accessSync(p, require("fs").constants.X_OK); return true } catch { return false }
  }) || "python"
  const backendDir = path.join(__dirname, "../backend")

  const env = {
    ...process.env,
    PYTHONPATH: backendDir
  }

  backendProcess = spawn(pythonExe, [
    "-m", "uvicorn", "main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--log-level", "info"
  ], {
    cwd: backendDir,
    env: env,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true
  })

  backendProcess.stdout.on("data", (data) => {
    logger.info("[Backend] %s", data.toString().trim())
  })

  backendProcess.stderr.on("data", (data) => {
    logger.error("[Backend] %s", data.toString().trim())
  })

  backendProcess.on("close", (code) => {
    logger.info("Backend process exited with code %s", code)
  })

  backendProcess.on("error", (err) => {
    logger.error("Backend spawn error: %s", err.message)
  })
}

// ==============================
// IPC HANDLERS
// ==============================
ipcMain.handle("store:get", (_event, key) => store.get(key))
ipcMain.handle("store:set", (_event, key, value) => { store.set(key, value) })

// Conversation history handlers
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
  const data = fs.readFileSync(filePath, "utf-8")
  return JSON.parse(data)
})

ipcMain.handle("conversation:list", () => {
  ensureConversationsDir()
  const files = fs.readdirSync(conversationsDir).filter(f => f.endsWith(".json"))
  return files.map(f => {
    const filePath = path.join(conversationsDir, f)
    const data = JSON.parse(fs.readFileSync(filePath, "utf-8"))
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
    w.hide()
  }
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
    const [currentWidth, currentHeight] = w.getSize()
    w.setSize(width || currentWidth, height || currentHeight)
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
})

ipcMain.handle("window:set-stealth-mode", (_event, enabled) => {
  if (enabled) {
    stealth.enable()
  } else {
    stealth.disable()
  }
  return { enabled: stealth.isEnabled(), undetectable: stealth.isUndetectable() }
})

ipcMain.handle("window:set-undetectable", (_event, enabled) => {
  stealth.setUndetectable(enabled)
  return { undetectable: stealth.isUndetectable() }
})

// Broadcast stealth state changes to renderer (for shortcut-triggered toggles)
function broadcastStealthState() {
  if (win && win.webContents) {
    win.webContents.send("stealth:state-changed", {
      enabled: stealth.isEnabled(),
      undetectable: stealth.isUndetectable()
    })
  }
}

// App-level handlers
ipcMain.handle("app:open-logs", () => {
  const { shell } = require("electron")
  shell.openPath(log.transports.file.getFile().path.replace(/[^\/\\]+$/, ""))
})

// File save dialog
ipcMain.handle("dialog:save-file", async (_event, { defaultPath, filters, content, encryptionKey }) => {
  const { dialog, BrowserWindow } = require("electron")
  const fs = require("fs")
  const crypto = require("crypto")

  let dataToSave = content
  let actualFilters = filters

  // If encryption requested
  if (encryptionKey) {
    const key = crypto.scryptSync(encryptionKey, "salt", 32)
    const iv = crypto.randomBytes(16)
    const cipher = crypto.createCipheriv("aes-256-cbc", key, iv)
    let encrypted = cipher.update(content, "utf8", "hex")
    encrypted += cipher.final("hex")
    dataToSave = JSON.stringify({ iv: iv.toString("hex"), data: encrypted })
    // Change extension hint
    actualFilters = filters.map(f => ({ ...f, name: f.name + " (Encrypted)" }))
  }

  const win = BrowserWindow.getFocusedWindow()
  const result = await dialog.showSaveDialog(win, {
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

// ==============================
// APP LIFECYCLE
// ==============================
app.whenReady().then(async () => {
  // Request microphone permission
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(permission === "media")
  })

  // Disable caching for renderer files to ensure latest version is always loaded
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

  // Restore stealth state from last session
  const savedStealthState = store.get("stealthState", false)
  if (savedStealthState) {
    stealth.enable()
  }

  // Global shortcuts (logged for debugging)
  function registerShortcut(accelerator, name, fn) {
    const success = globalShortcut.register(accelerator, fn)
    if (success) {
      logger.info(`[Shortcut] Registered: ${accelerator} -> ${name}`)
    } else {
      logger.warn(`[Shortcut] Failed to register: ${accelerator} (may conflict with another app)`)
    }
  }

  // Alt+D — toggle stealth mode (capture protection + tray)
  registerShortcut("Alt+D", "toggle stealth", () => {
    logger.info("[Shortcut] Alt+D fired")
    if (stealth.isEnabled()) {
      stealth.disable()
      store.set("stealthState", false)
      if (win) {
        if (win.isMinimized()) win.restore()
        win.setResizable(true)
        win.show()
        win.focus()
      }
    } else {
      stealth.enable()
      store.set("stealthState", true)
    }
    broadcastStealthState()
  })

  // Alt+Space — hide/show window (toggle visibility)
  registerShortcut("Alt+Space", "hide/show window", () => {
    logger.info("[Shortcut] Alt+Space fired")
    if (win) {
      if (win.isVisible()) {
        win.hide()
      } else {
        if (win.isMinimized()) win.restore()
        win.setResizable(true)
        win.show()
        win.focus()
      }
    }
  })

  // Ctrl+Left — move window left
  registerShortcut("CommandOrControl+Left", "move window left", () => {
    logger.info("[Shortcut] Ctrl+Left fired")
    if (win) {
      const [x, y] = win.getPosition()
      win.setPosition(x - 50, y)
    }
  })

  // Ctrl+Right — move window right
  registerShortcut("CommandOrControl+Right", "move window right", () => {
    logger.info("[Shortcut] Ctrl+Right fired")
    if (win) {
      const [x, y] = win.getPosition()
      win.setPosition(x + 50, y)
    }
  })

  // Ctrl+Up — move window up
  registerShortcut("CommandOrControl+Up", "move window up", () => {
    logger.info("[Shortcut] Ctrl+Up fired")
    if (win) {
      const [x, y] = win.getPosition()
      win.setPosition(x, y - 50)
    }
  })

  // Ctrl+Down — move window down
  registerShortcut("CommandOrControl+Down", "move window down", () => {
    logger.info("[Shortcut] Ctrl+Down fired")
    if (win) {
      const [x, y] = win.getPosition()
      win.setPosition(x, y + 50)
    }
  })

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else {
      const w = BrowserWindow.getFocusedWindow() || win
      if (w) {
        w.show()
        w.focus()
      }
    }
  })
})

app.on("will-quit", () => {
  globalShortcut.unregisterAll()
  if (backendProcess) {
    backendProcess.kill()
  }
})

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit()
  }
})
