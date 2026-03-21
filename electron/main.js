const { app, BrowserWindow, globalShortcut, ipcMain, session } = require("electron")
const path = require("path")
const { spawn } = require("child_process")
const stealth = require("./stealth")
const log = require("electron-log/main")
const Store = require("electron-store")

log.initialize()
log.transports.file.level = "info"
log.transports.console.level = "debug"
log.transports.file.maxSize = 5 * 1024 * 1024

const logger = log
const store = new Store()

const appDataDir = path.join(__dirname, "../electron-data")
app.setPath("userData", appDataDir)
app.setPath("sessionData", appDataDir)

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
function startBackend() {
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

// ==============================
// APP LIFECYCLE
// ==============================
app.whenReady().then(() => {
  // Request microphone permission
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(permission === "media")
  })

  startBackend()
  createWindow()

  // Global shortcuts
  // Ctrl+Shift+H — toggle stealth (hide/show window)
  globalShortcut.register("CommandOrControl+Shift+H", () => {
    stealth.toggle()
  })

  // Ctrl+Shift+U — toggle screen capture protection
  globalShortcut.register("CommandOrControl+Shift+U", () => {
    stealth.toggleUndetectable()
  })

  // Ctrl+Shift+Enter — toggle hide/restore window
  globalShortcut.register("CommandOrControl+Shift+Return", () => {
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

  // Ctrl+Shift+Space — hide window (alternative)
  globalShortcut.register("CommandOrControl+Shift+Space", () => {
    if (win && win.isVisible()) {
      win.hide()
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
