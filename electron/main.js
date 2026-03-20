const { app, BrowserWindow, globalShortcut, ipcMain, session } = require("electron")
const path = require("path")
const { spawn } = require("child_process")
const stealth = require("./stealth")

const appDataDir = path.join(__dirname, "../electron-data")
app.setPath("userData", appDataDir)
app.setPath("sessionData", appDataDir)

let win
let backendProcess = null

function safeConsoleMethod(methodName) {
  const original = console[methodName]
  console[methodName] = (...args) => {
    try {
      original.apply(console, args)
    } catch (err) {
      if (!err || err.code !== "EPIPE") {
        throw err
      }
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
    if (err && err.code !== "EPIPE") {
      throw err
    }
  })
}

ignoreBrokenPipe(process.stdout)
ignoreBrokenPipe(process.stderr)

process.on("uncaughtException", (err) => {
  if (err && err.code === "EPIPE") {
    return
  }
  throw err
})

function createWindow() {
  win = new BrowserWindow({
    width: 760,
    height: 360,
    minWidth: 560,
    minHeight: 300,
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

  win.setAlwaysOnTop(true, "screen-saver", 1)
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  win.loadFile(path.join(__dirname, "../renderer/index.html"))
}

ipcMain.handle("window:minimize", () => {
  const focusedWindow = BrowserWindow.getFocusedWindow() || win
  if (focusedWindow) {
    focusedWindow.setSize(420, 84)
    focusedWindow.setResizable(false)
    focusedWindow.show()
    focusedWindow.focus()
  }
})

ipcMain.handle("window:toggle-maximize", () => {
  const focusedWindow = BrowserWindow.getFocusedWindow() || win
  if (!focusedWindow) {
    return { isMaximized: false }
  }
  focusedWindow.setResizable(true)
  if (focusedWindow.isMaximized()) {
    focusedWindow.unmaximize()
  } else {
    focusedWindow.maximize()
  }
  return { isMaximized: focusedWindow.isMaximized() }
})

ipcMain.handle("window:close", () => {
  const focusedWindow = BrowserWindow.getFocusedWindow() || win
  if (focusedWindow) {
    focusedWindow.close()
  }
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

ipcMain.handle("window:restore", () => {
  const focusedWindow = BrowserWindow.getFocusedWindow() || win
  if (!focusedWindow) return
  if (focusedWindow.isMinimized()) {
    focusedWindow.restore()
  }
  if (!focusedWindow.isMaximized()) {
    focusedWindow.setSize(760, 360)
  }
  focusedWindow.setResizable(true)
  focusedWindow.show()
  focusedWindow.focus()
})

function restoreWindow() {
  const focusedWindow = BrowserWindow.getFocusedWindow() || win
  if (!focusedWindow) return
  if (focusedWindow.isMinimized()) {
    focusedWindow.restore()
  }
  focusedWindow.setResizable(true)
  focusedWindow.show()
  focusedWindow.focus()
}

function startBackend() {
  const pythonPath = path.join(__dirname, "../AINT_Venv/Scripts/python.exe")
  const backendDir = path.join(__dirname, "../backend")

  backendProcess = spawn(pythonPath, [
    "-m", "uvicorn", "main:app",
    "--host", "127.0.0.1", "--port", "8000"
  ], {
    cwd: backendDir,
    stdio: "ignore",
    windowsHide: true
  })

  backendProcess.on("close", () => {})
}

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(permission === "media")
  })

  startBackend()
  createWindow()
  stealth.init(win)

  // Toggle stealth mode with Ctrl+Shift+H
  globalShortcut.register("CommandOrControl+Shift+H", () => {
    stealth.toggle()
  })

  // Toggle screen capture protection with Ctrl+Shift+U
  globalShortcut.register("CommandOrControl+Shift+U", () => {
    stealth.toggleUndetectable()
  })

  globalShortcut.register("CommandOrControl+Shift+A", () => {
    if (stealth.isEnabled()) {
      stealth.disable()
    }
    restoreWindow()
  })

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else {
      restoreWindow()
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
