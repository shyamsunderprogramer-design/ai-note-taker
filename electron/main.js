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
function saveBounds() {
  if (win && !win.isMaximized() && !win.isMinimized()) {
    store.set("windowBounds", win.getBounds())
  }
}

// ==============================
// WINDOW CREATION
// ==============================
function createWindow() {
  const savedBounds = store.get("windowBounds", { width: 520, height: 440 })

  win = new BrowserWindow({
    width: savedBounds.width,
    height: savedBounds.height,
    x: savedBounds.x,
    y: savedBounds.y,
    minWidth: 420,
    minHeight: 360,
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

  // Save window bounds on move/resize
  win.on("resize", saveBounds)
  win.on("move", saveBounds)

  // Initialize stealth after window loads
  stealth.init(win)

  // Prevent background from going opaque on resize/maximize
  win.on("maximize", () => {
    win.setBackgroundColor("#00000000")
  })

  win.on("unmaximize", () => {
    win.setBackgroundColor("#00000000")
  })
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

  const pythonExe = path.join(__dirname, "../AINT_Venv/Scripts/python.exe")
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
  if (!w.isMaximized()) w.setSize(520, 440)
  w.setResizable(true)
  w.show()
  w.focus()
})

ipcMain.handle("window:set-stealth-mode", (_event, enabled) => {
  if (enabled) {
    stealth.enable()
  } else {
    stealth.disable()
  }
  return { enabled: stealth.isEnabled() }
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

// ==============================
// APP LIFECYCLE
// ==============================
app.whenReady().then(async () => {
  // Request microphone permission
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(permission === "media")
  })

  await startBackend()
  createWindow()

  // Enable stealth (capture protection) by default on startup
  stealth.enable()

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
      if (win) {
        if (win.isMinimized()) win.restore()
        win.setResizable(true)
        win.setSize(520, 440)
        win.show()
        win.focus()
      }
    } else {
      stealth.enable()
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
        win.setSize(520, 440)
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
