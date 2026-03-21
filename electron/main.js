const { app, BrowserWindow, globalShortcut, ipcMain, session } = require("electron")
const path = require("path")
const { spawn } = require("child_process")
const stealth = require("./stealth")

const appDataDir = path.join(__dirname, "../electron-data")
app.setPath("userData", appDataDir)
app.setPath("sessionData", appDataDir)

let win
let backendProcess = null

// ==============================
// CONSOLE FIX — ignore EPIPE
// ==============================
function safeConsoleMethod(methodName) {
  const original = console[methodName]
  console[methodName] = (...args) => {
    try {
      original.apply(console, args)
    } catch (err) {
      if (!err || err.code !== "EPIPE") throw err
    }
  }
}

safeConsoleMethod("log")
safeConsoleMethod("error")
safeConsoleMethod("warn")
safeConsoleMethod("info")

function ignoreBrokenPipe(stream) {
  if (!stream) return
  stream.on("error", (err) => {
    if (err && err.code !== "EPIPE") throw err
  })
}

ignoreBrokenPipe(process.stdout)
ignoreBrokenPipe(process.stderr)

process.on("uncaughtException", (err) => {
  if (err && err.code === "EPIPE") return
  throw err
})

// ==============================
// WINDOW CREATION
// ==============================
function createWindow() {
  win = new BrowserWindow({
    width: 520,
    height: 440,
    minWidth: 420,
    minHeight: 360,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    alwaysOnTop: true,
    skipTaskbar: false,
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

  backendProcess = spawn(pythonExe, [
    "-m", "uvicorn", "main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--log-level", "warning"
  ], {
    cwd: backendDir,
    stdio: "ignore",
    windowsHide: true
  })

  backendProcess.on("close", () => {
    console.log("[Main] Backend process exited")
  })

  backendProcess.on("error", (err) => {
    console.error("[Main] Backend spawn error:", err.message)
  })
}

// ==============================
// IPC HANDLERS
// ==============================
ipcMain.handle("window:minimize", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (w) {
    w.minimize()
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

  // Ctrl+Shift+A — restore window
  globalShortcut.register("CommandOrControl+Shift+A", () => {
    if (stealth.isEnabled()) {
      stealth.disable()
    }
    const w = BrowserWindow.getFocusedWindow() || win
    if (w) {
      if (w.isMinimized()) w.restore()
      w.setResizable(true)
      w.setSize(520, 440)
      w.show()
      w.focus()
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
