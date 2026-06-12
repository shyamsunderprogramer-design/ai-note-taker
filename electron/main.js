const { app, BrowserWindow, globalShortcut, ipcMain, session, desktopCapturer, shell } = require("electron")
const path = require("path")
const { spawn } = require("child_process")
const os = require("os")
const stealth = require("./stealth")
const { OverlayAdapter } = require("./features/overlay-adapter")
const { ScreenRecorder } = require("./features/screen-recorder")
const { logger, configureForProduction: configureLoggerForProduction } = require("./lib/logger")
const { PLATFORM, isPortableMode, initializeAppPaths, ensureConversationsDir } = require("./lib/paths")
const cryptoLib = require("./lib/crypto")
const Store = require("electron-store")
const { autoUpdater } = require("electron-updater")
const fs = require("fs")
const crypto = require("crypto")

// Speed optimizations below (must run before app.whenReady())
app.commandLine.appendSwitch("disable-features",
  "HttpsUpgrades,HttpsFirstModeV2,HttpsFirstBalancedMode," +
  "MediaRouter,TabHoverCardImages,ReadAnything," +
  "AccessibilityPerformanceMonitoring,PaymentMethodQuery,WebPayments"
)

// Disable background networking
app.commandLine.appendSwitch("disable-background-networking")

// Disable component extensions (PDF viewer, etc)
app.commandLine.appendSwitch("disable-component-extensions-with-background-pages")

// Disable renderer backgrounding (keep UI responsive)
app.commandLine.appendSwitch("disable-renderer-backgrounding")

// Disable background timer throttling
app.commandLine.appendSwitch("disable-background-timer-throttling")

// Limit in-memory cache
app.commandLine.appendSwitch("disk-cache-size", "104857600") // 100MB

// Limit media cache
app.commandLine.appendSwitch("media-cache-size", "52428800") // 50MB

// Reduce memory usage
app.commandLine.appendSwitch("js-flags", "--max-old-space-size=4096")

// Prevent Chromium from upgrading HTTP→HTTPS on localhost (which causes
// ERR_SSL_PROTOCOL_ERROR since our dev backend only serves plain HTTP).
// Must be set BEFORE app.whenReady().
// NOTE: Do NOT use "ignore-certificate-errors" globally — it disables TLS
// verification for ALL requests, not just localhost.
app.commandLine.appendSwitch("allow-insecure-localhost")
// Treat http://127.0.0.1:8000 as a secure origin so Chromium won't
// auto-upgrade it to HTTPS (Chromium's built-in HSTS preload forces HTTPS
// for localhost/127.0.0.1 since Chrome 89)
app.commandLine.appendSwitch("unsafely-treat-insecure-origin-as-secure", "http://127.0.0.1:8000")

// Disable file logging in production for stealth mode
// Logs only go to console (memory), not to disk
if (app.isPackaged) {
  configureLoggerForProduction()
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUTOSTART CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════
const AUTO_START_SETTINGS_KEY = "autoStartEnabled"
const AUTO_START_HIDDEN_KEY = "autoStartHidden"

function configureAutoStart(enabled, openAsHidden = true) {
  if (!app.isPackaged) {
    logger.info("[Autostart] Skipping in development mode")
    return { success: false, reason: "development_mode" }
  }

  try {
    app.setLoginItemSettings({
      openAtLogin: enabled,
      openAsHidden: openAsHidden,
      path: app.getPath("exe"),
      args: enabled ? ["--hidden"] : []
    })

    logger.info(`[Autostart] ${enabled ? "Enabled" : "Disabled"} (hidden: ${openAsHidden})`)
    return { success: true, enabled }
  } catch (err) {
    logger.error("[Autostart] Failed:", err.message)
    return { success: false, error: err.message }
  }
}

function getAutoStartStatus() {
  return app.getLoginItemSettings()
}

function getAppDataPath() {
  if (isPortableMode()) {
    // In portable mode, store data next to executable
    const portableDataDir = path.join(path.dirname(app.getPath("exe")), "ANT-Data")
    if (!fs.existsSync(portableDataDir)) {
      fs.mkdirSync(portableDataDir, { recursive: true })
    }
    return portableDataDir
  }
  return appDataDir
}

// appData path is cross-platform via Electron API
// IMPORTANT: Set userData BEFORE creating Store instances so they read/write
// from the correct location.
const { appDataDir } = initializeAppPaths()
const conversationsDir = ensureConversationsDir(appDataDir)

const store = new Store()

// Secure API key storage - encrypted using machine-specific key derived with
// full 32-byte key (not sliced down). Uses unique salt per app instance.
const _keyDeriveSalt = cryptoLib.deriveApiKeySalt()
let apiKeyStore
try {
  apiKeyStore = new Store({
    name: "secure-api-keys",
    encryptionKey: _keyDeriveSalt.toString("hex")
  })
} catch (e) {
  // If the store can't be loaded (e.g., old encryption key no longer matches),
  // delete the corrupted file and recreate with the new key.
  logger.warn("[API Key Store] Failed to load encrypted store, resetting: %s", e.message)
  cryptoLib.resetApiKeyStoreFile(logger)
  apiKeyStore = new Store({
    name: "secure-api-keys",
    encryptionKey: _keyDeriveSalt.toString("hex")
  })
}

// T4: AES-256 encryption for conversation files at rest
const _convoKey = cryptoLib.deriveConversationKey()

function _encryptConversation(plainText) {
  return cryptoLib.encryptConversation(plainText, _convoKey)
}

function _decryptConversation(cipherText) {
  return cryptoLib.decryptConversation(cipherText, _convoKey)
}

let win
let splashScreen = null
let overlayAdapter = null
let screenRecorder = null
let backendProcess = null
let backendStopped = false  // true if user/App Quit initiated the stop — don't restart
let backendRestartAttempts = 0
let backendHealthCheckInterval = null
let backendStatus = "unknown" // "unknown" | "starting" | "ready" | "error" | "dead"
const MAX_BACKEND_RESTART_ATTEMPTS = 5
const BACKEND_RESTART_BASE_DELAY_MS = 1000

// Track if app is quitting to prevent close event interference
app.isQuitting = false

// Splash visibility timing — ensures splash is visible for at least 2 seconds
let _mainWindowReady = false
let _splashMinTimeDone = false
function _tryShowMain() {
  if (_mainWindowReady && _splashMinTimeDone && win && !win.isDestroyed()) {
    win.show()
    win.focus()
    closeSplashScreen()
  }
}

// T3: CSP nonce store — maps webContentsId → nonce for nonce-based CSP headers
const _cspNonceMap = new Map()
const BACKEND_HEALTH_CHECK_INTERVAL_MS = 5000

// Exponential backoff delay calculation
function getRestartDelayMs(attempt) {
  // 1s, 2s, 4s, 8s, 16s
  return BACKEND_RESTART_BASE_DELAY_MS * Math.pow(2, attempt - 1)
}

// Keep window above all others - uses platform-appropriate level
function ensureTopmost(w) {
  if (!w || w.isDestroyed()) return

  if (PLATFORM === "win32") {
    // Windows: use "monitor" level — above all normal windows, PIP, fullscreen apps
    w.setAlwaysOnTop(true, "monitor", 2147483647)
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
let autoScreenshotEnabled = true
let autoScreenshotInterval = null

process.on("uncaughtException", (err) => {
  logger.error("Uncaught exception: %s", err.stack || err.message)
  // Only crash on truly fatal errors; log and continue for others
  if (err.code === "ERR_UNHANDLED_ERROR" || err.message?.includes("EPERM")) {
    process.exit(1)
  }
})

process.on("unhandledRejection", (reason) => {
  logger.error("Unhandled rejection: %s", String(reason))
})

// ==============================
// WINDOW STATE
// ==============================
// Minimum dimensions chosen so the rich UI (hero banner 180px + header 50px +
// controls strip ~80px + input row ~60px + response area header 30px + chat
// area ≥ 200px) fits comfortably without the shell itself scrolling.
const MIN_WIDTH = 560
const MIN_HEIGHT = 600
// Reasonable default for first-run / when saved bounds are off-screen.
// 960x720 gives the welcome state + suggestion cards full breathing room and
// also fits 1366x768 minimum laptops without feeling cramped.
const DEFAULT_BOUNDS = { width: 960, height: 720, x: undefined, y: undefined }

function validateBounds(bounds) {
  if (!bounds.width || bounds.width < MIN_WIDTH) bounds.width = DEFAULT_BOUNDS.width
  if (!bounds.height || bounds.height < MIN_HEIGHT) bounds.height = DEFAULT_BOUNDS.height

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
    // Clamp to primary work area so very large saved bounds (e.g. from a
    // 4K display) don't push the window off a smaller secondary monitor.
    const targetW = Math.min(bounds.width, Math.round(screenWidth * 0.85))
    const targetH = Math.min(bounds.height, Math.round(screenHeight * 0.85))
    bounds.width = Math.max(MIN_WIDTH, targetW)
    bounds.height = Math.max(MIN_HEIGHT, targetH)
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

// ═══════════════════════════════════════════════════════════════════════════════
// SPLASH SCREEN - For perceived fast startup
// ═══════════════════════════════════════════════════════════════════════════════
function createSplashScreen() {
  logger.info("[Splash] Creating splash window...")
  // Show splash immediately for perceived speed
  splashScreen = new BrowserWindow({
    width: 420,
    height: 320,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    skipTaskbar: true,
    resizable: false,
    center: true,
    show: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js")
    }
  })

  // T3: Register CSP nonce for splash screen
  const splashNonce = crypto.randomBytes(16).toString("base64")
  splashScreen.cspNonce = splashNonce
  const splashWcId = splashScreen.webContents.id
  _cspNonceMap.set(splashWcId, splashNonce)
  splashScreen.webContents.on("destroyed", () => { _cspNonceMap.delete(splashWcId) })

  // Load splash HTML
  const isProd = app.isPackaged
  const splashPath = isProd
    ? path.join(process.resourcesPath, "renderer", "splash.html")
    : path.join(__dirname, "..", "apps", "web", "splash.html")

  splashScreen.loadFile(splashPath).catch(() => {
    // If splash.html doesn't exist, show basic splash
    splashScreen.loadURL(`data:text/html,
      <html><body style="margin:0;background:transparent;display:flex;align-items:center;justify-content:center;height:100vh;">
        <div style="text-align:center;color:white;font-family:sans-serif;">
          <img src="assets/desktop-icon.png" style="width:60px;height:60px;margin-bottom:20px;filter:drop-shadow(0 0 12px rgba(56,189,248,0.5));" alt="ANT">
          <div style="font-size:24px;font-weight:bold;">ANT</div>
          <div style="font-size:14px;opacity:0.7;margin-top:10px;">Loading...</div>
        </div>
      </body></html>
    `)
  })

  // Close splash after main window loads
  splashScreen.on("ready-to-show", () => {
    splashScreen.show()
  })

  return splashScreen
}

function closeSplashScreen() {
  if (splashScreen && !splashScreen.isDestroyed() && splashScreen.webContents) {
    splashScreen.close()
    splashScreen = null
  } else {
    splashScreen = null
  }
}

// ==============================
// WINDOW CREATION
// ==============================
async function createWindow() {
  const savedBounds = store.get("windowBounds", DEFAULT_BOUNDS)
  const bounds = validateBounds(savedBounds)

  // Platform-specific window options
  const windowOpts = {
    width: bounds.width,
    height: bounds.height,
    x: bounds.x,
    y: bounds.y,
    minWidth: MIN_WIDTH,
    minHeight: MIN_HEIGHT,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
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

  // titleBarStyle only works on macOS.
  // Native macOS traffic lights are pushed off-screen so the custom HTML
  // traffic lights in apps/web/index.html are the only ones the user sees.
  // We use a generous negative offset so they stay hidden regardless of
  // DPI / multi-monitor scaling.
  if (PLATFORM === "darwin") {
    windowOpts.titleBarStyle = "hidden"
    windowOpts.trafficLightPosition = { x: -100, y: -100 }
  }

  // Generate a new CSP nonce for this window
  const cspNonce = crypto.randomBytes(16).toString("base64")

  // Windows: use "monitor" level — above all normal windows, PIP, fullscreen apps
  // This is the highest normal window level, only below system notifications
  win = new BrowserWindow(windowOpts)

  // Show window only when content is ready AND minimum splash time elapsed
  win.once("ready-to-show", () => {
    logger.info(`[Window] ready-to-show: title="${win?.getTitle()}"`)
    _mainWindowReady = true
    _tryShowMain()
  })

  // Also fire on real first paint (did-finish-load) so the splash can be
  // dismissed as soon as signin.html or index.html is fully loaded, without
  // waiting the full 2s splash minimum. The ready-to-show event sometimes
  // fires before the renderer has actually painted the first frame.
  win.webContents.once("did-finish-load", () => {
    logger.info(`[Window] did-finish-load: title="${win?.getTitle()}"`)
    _mainWindowReady = true
    _tryShowMain()
  })

  // Store nonce on the window webContents for access in CSP headers
  win.cspNonce = cspNonce
  _cspNonceMap.set(win.webContents.id, cspNonce)
  win.webContents.on("destroyed", () => { _cspNonceMap.delete(win.webContents.id) })

  // Set always on top - "normal" level is most reliable on Windows
  // even though it sounds counter-intuitive
  if (PLATFORM === "win32") {
    win.setAlwaysOnTop(true, "monitor", 2147483647)
  } else if (PLATFORM === "darwin") {
    win.setAlwaysOnTop(true, "floating", 999)
  }

  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true })

  // In production, renderer is in extraResources; in dev, it's alongside electron/
  const isProd = app.isPackaged
  const webDir = isProd
    ? path.join(process.resourcesPath, "renderer")
    : path.join(__dirname, "..", "apps", "web")

  // Set window icon after webDir is known
  win.setIcon(path.join(webDir, "assets", "desktop-icon.png"))

  // Center the login window over the splash backdrop
  win.center()

  // Always load signin.html first — it will auto-redirect to index.html if already authenticated
  const loadAppropriatePage = () => {
    return win.loadFile(path.join(webDir, "signin.html"))
  }
  await loadAppropriatePage()

  // Open external links in system browser, not in Electron window
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http://") || url.startsWith("https://")) {
      shell.openExternal(url)
    }
    return { action: "deny" }
  })

  // Toggle DevTools with Ctrl+Shift+I when window is focused
  // (Global shortcut conflicts on Windows, so we use in-app listener)
  win.webContents.on("before-input-event", (event, input) => {
    const isCtrl = input.control || input.meta
    if (isCtrl && input.shift && input.key.toLowerCase() === "i") {
      event.preventDefault()
      if (win.webContents.isDevToolsOpened()) {
        win.webContents.closeDevTools()
      } else {
        win.webContents.openDevTools({ mode: "detach" })
      }
    }
  })
  win.webContents.on("will-navigate", (event, url) => {
    // Allow navigation to our own pages, block external navigation inside the window
    if (url.startsWith("http://") || url.startsWith("https://")) {
      if (!url.includes("127.0.0.1:") && !url.includes("localhost:")) {
        event.preventDefault()
        shell.openExternal(url)
      }
    }
  })

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

  // On macOS the native traffic lights are pushed off-screen (see
  // trafficLightPosition above) — close is triggered by the custom
  // HTML close button (via window.api.closeWindow) or by Cmd+Q / dock
  // Quit. In all cases we want to fully quit the app, not just close
  // the window, since Electron on darwin otherwise keeps the process
  // alive with no visible UI.
  let closeHandlerFired = false
  win.on("close", (event) => {
    if (PLATFORM === "darwin" && !app.isQuitting && !closeHandlerFired) {
      closeHandlerFired = true
      event.preventDefault()
      logger.info("[Main] Close requested on macOS, quitting app")
      app.quit()
    }
  })

  // Set up window state tracking
  // Note: Window is already set to always-on-top, no need for aggressive re-assertion
  stealth.init(win)
  ensureTopmost(win)

  // Initialize overlay adapter
  overlayAdapter = new OverlayAdapter(win)
  overlayAdapter.setupIpcHandlers()
}

// ======================================
// AUTO SCREENSHOT
// ======================================
async function captureAutoScreenshot() {
  try {
    const sources = await desktopCapturer.getSources({
      types: ["screen"],
      thumbnailSize: { width: 1280, height: 720 }  // Phase A: clamped to 720p
    })
    if (sources && sources.length > 0) {
      // Phase A: JPEG at 80% quality — 60-80% smaller than PNG
      const b64 = sources[0].thumbnail.toJPEG(80).toString("base64")
      screenshotBuffer.push(b64)
      if (screenshotBuffer.length > SCREENSHOT_BUFFER_MAX) {
        screenshotBuffer.shift()
      }
      logger.info("[AutoScreenshot] Captured (JPEG), buffer size: %d", screenshotBuffer.length)
    }
  } catch (e) {
    logger.warn("[AutoScreenshot] Capture failed:", e.message)
  }
}

function startAutoScreenshot(intervalMs) {
  intervalMs = intervalMs || 3000
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

  // Verify backend main.py exists (check both root and core/ locations)
  let mainPy = path.join(backendDir, "main.py")
  if (!fs.existsSync(mainPy)) {
    mainPy = path.join(backendDir, "core", "main.py")
  }
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

  // Determine uvicorn module path based on where main.py was found
  const isCoreMainPy = mainPy.includes(path.join("core", "main.py"))
  const uvicornModule = isCoreMainPy ? "core.main:app" : "main:app"

  backendProcess = spawn(pythonExe, [
    "-m", "uvicorn", uvicornModule,
    "--host", "127.0.0.1",
    "--port", "8000",
    "--log-level", "info"
  ], {
    ...spawnOpts,
    env: {
      ...process.env,
      ...spawnOpts.env,
      KEY_SERVER_SECRET: API_KEY_SERVER_SECRET,
      AUTH_REQUIRED: "true"
    }
  })

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

  // Wait for backend health check to pass (max 15s), then window opens
  const maxWait = 15000
  const startWait = Date.now()
  logger.info("[Backend] Waiting for backend to be ready...")
  while (Date.now() - startWait < maxWait) {
    if (await isBackendRunning()) {
      notifyRendererBackendStatus("ready")
      backendRestartAttempts = 0
      logger.info("[Backend] Ready! (%dms)", Date.now() - startWait)
      return
    }
    await new Promise(r => setTimeout(r, 200))
  }
  logger.warn("[Backend] Not ready after %dms, opening window anyway", maxWait)
}

// ==============================
// IPC HANDLERS
// ==============================
ipcMain.handle("store:get", (_event, key) => store.get(key))
ipcMain.handle("store:set", (_event, key, value) => { store.set(key, value) })

ipcMain.handle("conversation:save", (_event, conversation) => {
  ensureConversationsDir(appDataDir)
  const id = conversation.id || crypto.randomUUID()
  const now = Date.now()
  const record = {
    ...conversation,
    id,
    createdAt: conversation.createdAt || now,
    updatedAt: now
  }
  const filePath = path.join(conversationsDir, `${id}.json`)
  const encrypted = _encryptConversation(JSON.stringify(record))
  fs.writeFileSync(filePath, encrypted, "utf-8")
  return record
})

ipcMain.handle("conversation:load", (_event, id) => {
  // Validate id is a safe filename (UUID format) to prevent path traversal
  if (!id || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    logger.warn(`[conversation:load] Rejected invalid id: ${id}`)
    return null
  }
  const filePath = path.join(conversationsDir, `${id}.json`)
  if (!fs.existsSync(filePath)) return null
  const decrypted = _decryptConversation(fs.readFileSync(filePath, "utf-8"))
  try {
    return JSON.parse(decrypted)
  } catch (e) {
    logger.warn("[conversation:load] Failed to parse conversation %s: %s", id, e.message)
    return null
  }
})

ipcMain.handle("conversation:list", () => {
  ensureConversationsDir(appDataDir)
  return fs.readdirSync(conversationsDir)
    .filter(f => f.endsWith(".json"))
    .map(f => {
      const raw = fs.readFileSync(path.join(conversationsDir, f), "utf-8")
      const decrypted = _decryptConversation(raw)
      try {
        const data = JSON.parse(decrypted)
        return {
          id: data.id,
          title: data.title,
          pinned: data.pinned || false,
          createdAt: data.createdAt,
          updatedAt: data.updatedAt,
          messageCount: data.messages ? data.messages.length : 0
        }
      } catch (e) {
        logger.warn("[conversation:list] Failed to parse %s: %s", f, e.message)
        return null
      }
    })
    .filter(Boolean)
})

ipcMain.handle("conversation:delete", (_event, id) => {
  // Validate id is a safe filename (UUID format) to prevent path traversal
  if (!id || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    logger.warn(`[conversation:delete] Rejected invalid id: ${id}`)
    return false
  }
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
    // Use native minimize (yellow traffic light behavior on macOS)
    w.minimize()
    // Note: We don't hide from taskbar or destroy tray on normal minimize
    // That behavior is only for stealth mode (Alt+D)
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
  // Quit the app entirely (triggers will-quit which kills backend, etc.)
  logger.info("[Main] window:close called, quitting app")
  app.quit()
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
  ensureTopmost(w)
  // Restart auto-screenshot if it was enabled
  const savedAutoSS = store.get("autoScreenshotEnabled", true)
  if (savedAutoSS && !autoScreenshotInterval) {
    const interval = store.get("autoScreenshotInterval", 3000)
    startAutoScreenshot(interval)
    autoScreenshotEnabled = true
  }
})

ipcMain.handle("window:force-top", () => {
  const w = BrowserWindow.getFocusedWindow() || win
  if (!w) return
  ensureTopmost(w)
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
      thumbnailSize: { width: 1280, height: 720 }  // Phase A: clamped to 720p
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
    // Phase A: JPEG at 80% quality — 60-80% smaller than PNG
    const base64 = primarySource.thumbnail.toJPEG(80).toString("base64")
    logger.info("[Screenshot] Captured screen (JPEG), size: %d bytes", base64.length)
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

// ═══════════════════════════════════════════════════════════════════════════════
// AUTOSTART IPC HANDLERS
// ═══════════════════════════════════════════════════════════════════════════════
ipcMain.handle("autostart:set", (_event, { enabled, hidden }) => {
  const result = configureAutoStart(enabled, hidden !== false)
  if (result.success) {
    store.set(AUTO_START_SETTINGS_KEY, enabled)
    store.set(AUTO_START_HIDDEN_KEY, hidden !== false)
  }
  return result
})

ipcMain.handle("autostart:get", () => {
  const settings = getAutoStartStatus()
  const enabled = store.get(AUTO_START_SETTINGS_KEY, false)
  return {
    enabled: enabled && settings.executableWillLaunchAtLogin,
    openAsHidden: store.get(AUTO_START_HIDDEN_KEY, true),
    systemSettings: settings
  }
})

// ═══════════════════════════════════════════════════════════════════════════════
// PORTABLE MODE IPC HANDLERS
// ═══════════════════════════════════════════════════════════════════════════════
ipcMain.handle("app:portable-mode", () => {
  return {
    isPortable: isPortableMode(),
    dataPath: getAppDataPath()
  }
})

// Platform info for renderer
ipcMain.handle("app:platform", () => PLATFORM)

// ═══════════════════════════════════════════════════════════════════════════════
// FILE DRAG & DROP HANDLERS
// ═══════════════════════════════════════════════════════════════════════════════

// Handle file drop from renderer (when HTML5 drag-drop is used)
ipcMain.handle("file:drop", async (_event, filePath) => {
  if (overlayAdapter) {
    return await overlayAdapter.processDroppedFile(filePath)
  }
  return null
})

// Read file contents for the renderer
ipcMain.handle("file:read", async (_event, filePath) => {
  try {
    const fs = require("fs")
    if (!fs.existsSync(filePath)) {
      return { error: "File not found" }
    }

    const stats = fs.statSync(filePath)
    const ext = path.extname(filePath).toLowerCase()

    // For text/code files, read contents
    const textExts = [".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yaml", ".yml"]
    if (textExts.includes(ext) && stats.size < 1024 * 1024) { // Max 1MB
      const content = fs.readFileSync(filePath, "utf-8")
      return {
        name: path.basename(filePath),
        content,
        size: stats.size,
        type: "text"
      }
    }

    // For images, return base64
    const imageExts = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
    if (imageExts.includes(ext)) {
      const buffer = fs.readFileSync(filePath)
      const base64 = buffer.toString("base64")
      const mimeType = ext === ".png" ? "image/png" :
                       ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" :
                       ext === ".gif" ? "image/gif" :
                       ext === ".webp" ? "image/webp" : "image/png"
      return {
        name: path.basename(filePath),
        content: `data:${mimeType};base64,${base64}`,
        size: stats.size,
        type: "image"
      }
    }

    // For PDFs and other files, just return metadata
    return {
      name: path.basename(filePath),
      path: filePath,
      size: stats.size,
      type: overlayAdapter?.getFileType(ext) || "unknown"
    }
  } catch (err) {
    logger.error("[File] Read error:", err.message)
    return { error: err.message }
  }
})

// ======================================
// Provider name to .env variable mapping
const _PROVIDER_ENV_MAP = {
  openai: "OPENAI_API_KEY",
  anthropic: "ANTHROPIC_API_KEY",
  google: "GOOGLE_API_KEY",
  xai: "XAI_API_KEY",
  deepseek: "DEEPSEEK_API_KEY",
  groq: "GROQ_API_KEY",
  "ollama-cloud": "OLLAMA_CLOUD_API_KEY",
  perplexity: "PERPLEXITY_API_KEY",
}

function _updateBackendEnv(key, value) {
  const backendDir = app.isPackaged
    ? path.join(process.resourcesPath, "backend")
    : path.join(__dirname, "..", "backend")
  const envPath = path.join(backendDir, ".env")
  let content = ""
  try { content = fs.readFileSync(envPath, "utf8") } catch {}
  const lines = content.split(/\r?\n/)
  let found = false
  const pattern = new RegExp(`^(${key}=)(.*)$`)
  const newLines = lines.map((line) => {
    const match = line.match(pattern)
    if (match) {
      found = true
      return `${key}=${value}`
    }
    return line
  })
  if (!found) {
    newLines.push(`${key}=${value}`)
  }
  fs.writeFileSync(envPath, newLines.join("\n"), "utf8")
}

// SECURE API KEY STORAGE (P1 Privacy)
// ======================================
// Store API keys encrypted. Optionally sync to backend/.env for standalone usage.
ipcMain.handle("apiKey:save", (_event, { provider, apiKey, syncToEnv }) => {
  try {
    apiKeyStore.set(`apiKey.${provider}`, apiKey)
    logger.info(`[API Key] Saved encrypted key for provider: ${provider}`)
    if (syncToEnv) {
      const envKey = _PROVIDER_ENV_MAP[provider]
      if (envKey) {
        try {
          _updateBackendEnv(envKey, apiKey)
          logger.info(`[API Key] Synced ${provider} to backend/.env`)
        } catch (envErr) {
          logger.error(`[API Key] Failed to sync ${provider} to .env:`, envErr.message)
          return { success: true, warning: "Saved to encrypted store, but failed to write to backend/.env" }
        }
      }
    }
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

ipcMain.handle("apiKey:has", (_event, provider) => {
  try {
    const key = apiKeyStore.get(`apiKey.${provider}`, null)
    return { hasKey: !!key }
  } catch (err) {
    logger.error("[API Key] Has error:", err.message)
    return { hasKey: false }
  }
})

// HTTP endpoint for backend to request API keys
const http = require("http")
const API_KEY_SERVER_PORT = 18000 // Separate port for secure key exchange

// Throttle key server logging — only log once per provider per minute
const _keyLogTimestamps = {}
function _shouldLogKeyRequest(provider) {
  const now = Date.now()
  const lastLog = _keyLogTimestamps[provider] || 0
  if (now - lastLog > 60000) { // 1 minute throttle
    _keyLogTimestamps[provider] = now
    return true
  }
  return false
}

// Generate a shared secret for API key server authentication.
// The backend must include this secret in the X-Key-Server-Secret header.
const API_KEY_SERVER_SECRET = crypto.randomBytes(32).toString("hex")

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
      // Verify shared secret header to prevent unauthorized key access
      const clientSecret = req.headers["x-key-server-secret"]
      if (!clientSecret || !crypto.timingSafeEqual(
        Buffer.from(clientSecret, "utf8"),
        Buffer.from(API_KEY_SERVER_SECRET, "utf8")
      )) {
        res.writeHead(403, { "Content-Type": "application/json" })
        res.end(JSON.stringify({ error: "Unauthorized" }))
        // Rate-limit rejection logs to avoid spam
        const now = Date.now()
        if (!global._lastKeyRejectLog || (now - global._lastKeyRejectLog) > 10000) {
          logger.warn("[API Key Server] Rejected unauthorized key request (throttled)")
          global._lastKeyRejectLog = now
        }
        return
      }

      let body = ""
      req.on("data", chunk => body += chunk)
      req.on("end", () => {
        try {
          const { provider } = JSON.parse(body)
          const apiKey = apiKeyStore.get(`apiKey.${provider}`, null)
          res.writeHead(200, { "Content-Type": "application/json" })
          res.end(JSON.stringify({ apiKey }))
          // Only log when key is found, or throttle missing-key logs to once per minute per provider
          if (apiKey || _shouldLogKeyRequest(provider)) {
            logger.info(`[API Key Server] Key requested for ${provider}, found: ${!!apiKey}`)
          }
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

  let retries = 0
  const maxRetries = 3

  server.listen(API_KEY_SERVER_PORT, "127.0.0.1", () => {
    logger.info(`[API Key Server] Running on port ${API_KEY_SERVER_PORT}`)
  })

  // Handle EADDRINUSE — kill old process on port, retry up to 3 times
  server.on("error", (err) => {
    if (err.code === "EADDRINUSE" && retries < maxRetries) {
      retries++
      logger.warn(`[API Key Server] Port ${API_KEY_SERVER_PORT} in use (retry ${retries}/${maxRetries}), killing old process...`)
      // Kill whatever is using the port on Windows
      const { execSync } = require("child_process")
      try {
        execSync(`netstat -ano | findstr :${API_KEY_SERVER_PORT} | findstr LISTENING`, { encoding: "utf8" })
          .split("\n").filter(Boolean).forEach(line => {
            const pid = line.trim().split(/\s+/).pop()
            if (pid && pid !== process.pid.toString()) {
              try { execSync(`taskkill /PID ${pid} /F`, { stdio: "ignore" }) } catch {}
            }
          })
      } catch {}
      setTimeout(() => {
        server.close()
        server.listen(API_KEY_SERVER_PORT, "127.0.0.1", () => {
          logger.info(`[API Key Server] Retry succeeded on port ${API_KEY_SERVER_PORT}`)
        })
      }, 1500)
    } else if (err.code === "EADDRINUSE") {
      logger.error(`[API Key Server] Port ${API_KEY_SERVER_PORT} still in use after ${maxRetries} retries. Key server NOT started. Kill the old process manually: netstat -ano | findstr :${API_KEY_SERVER_PORT}`)
    } else {
      logger.error(`[API Key Server] Error: ${err.message}`)
    }
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
    startAutoScreenshot(intervalMs || 3000)
  } else {
    stopAutoScreenshot()
  }
  store.set("autoScreenshotEnabled", enabled)
  store.set("autoScreenshotInterval", intervalMs || 3000)
  return { enabled, intervalMs: enabled ? (intervalMs || 3000) : 0 }
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
  // Open-source project: no paid code signing cert.
  // Security relies on GitHub Releases channel integrity (git commit + release hash).
  // Users verify via the public repo: github.com/shyamsunderprogramer-design/ai-note-taker

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
    // Only apply CSP to our own app pages (file:// and localhost)
    // External websites (LeetCode, etc.) must NOT get our restrictive CSP
    const isOwnPage = details.url.startsWith("file://") ||
      details.url.includes("127.0.0.1:8000") ||
      details.url.includes("localhost:8000") ||
      details.url.includes("127.0.0.1:18000") ||
      details.url.includes("localhost:18000")

    const headers = { ...details.responseHeaders }

    // Strip HSTS header from localhost responses to prevent Chromium from
    // upgrading HTTP connections to HTTPS (which causes ERR_SSL_PROTOCOL_ERROR
    // since our dev backend only serves HTTP)
    if (details.url.includes("127.0.0.1") || details.url.includes("localhost")) {
      delete headers["Strict-Transport-Security"]
    }

    if (isOwnPage) {
      // T3: Nonce-based CSP — removes 'unsafe-inline' in favor of per-window nonce
      // For file:// URLs (local HTML), allow unsafe-inline since inline styles/scripts
      // in static files can't be dynamically nonced before parse.
      const isFile = details.url.startsWith("file://")
      const nonce = details.webContentsId ? _cspNonceMap.get(details.webContentsId) : null
      const scriptNonce = isFile ? "'self' 'unsafe-inline'" : (nonce ? `'nonce-${nonce}'` : "'self'")
      const styleNonce  = isFile ? "'self' 'unsafe-inline' https:" : (nonce ? `'nonce-${nonce}' https:` : "'self' https:")
      const csp = `default-src 'self'; script-src ${scriptNonce}; style-src ${styleNonce}; img-src 'self' data: blob: https:; font-src 'self' data: https:; connect-src 'self' ws://localhost:* ws://127.0.0.1:* http://localhost:* https://localhost:* http://127.0.0.1:* https://127.0.0.1:* wss://localhost:* wss://127.0.0.1:* wss: https:; media-src 'self' mediastream: blob: https:`
      headers["Content-Security-Policy"] = [csp]
    }

    // T26: Removed Access-Control-Allow-Origin: ["*"] — backend handles CORS
    callback({ responseHeaders: headers })
  })

  // Clear HSTS cache for localhost to prevent ERR_SSL_PROTOCOL_ERROR
  // Chromium caches HSTS directives and will upgrade HTTP→HTTPS even after
  // the server stops sending the header. This clears that cached state.
  session.defaultSession.clearStorageData({
    origins: ["http://127.0.0.1:8000", "https://127.0.0.1:8000",
              "http://localhost:8000", "https://localhost:8000"],
    storages: ["hsts"]
  }).catch(() => {})

  // Intercept HTTPS requests to localhost and redirect them to HTTP.
  // Chromium's built-in HSTS preload forces HTTPS for 127.0.0.1 and localhost,
  // causing ERR_SSL_PROTOCOL_ERROR since our backend only serves plain HTTP.
  // This onBeforeRequest handler catches those upgrades and redirects back to HTTP.
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    const url = details.url
    if (url.startsWith("https://127.0.0.1:") || url.startsWith("https://localhost:")) {
      const httpUrl = url.replace(/^https:/, "http:")
      callback({ redirectURL: httpUrl })
      return
    }
    callback({})
  })

  session.defaultSession.webRequest.onBeforeSendHeaders((details, callback) => {
    if (details.url.includes("file://")) {
      details.requestHeaders["Cache-Control"] = "no-cache, no-store, must-revalidate"
      details.requestHeaders["Pragma"] = "no-cache"
      details.requestHeaders["Expires"] = "0"
    }
    callback({ requestHeaders: details.requestHeaders })
  })

  // ═══════════════════════════════════════════════════════════════════════════════
  // FAST STARTUP SEQUENCE
  // ═══════════════════════════════════════════════════════════════════════════════

  // Check for hidden startup (skip splash)
  const startHidden = process.argv.includes("--hidden") || process.argv.includes("--autostart")
  const autoStartEnabled = store.get(AUTO_START_SETTINGS_KEY, false)

  // Start backend and create window in parallel
  const backendPromise = startBackend()
  const windowPromise = new Promise((resolve) => {
    if (startHidden && autoStartEnabled) {
      // Start hidden — no splash, no visible window
      createWindow()
      if (win) {
        win.hide()
        win.setSkipTaskbar(true)
        stealth.enable()
      }
      resolve(null)
    } else {
      // Show splash first, then create main window
      createSplashScreen()
      createWindow()
      // Brief splash minimum (800ms) so the user perceives the splash —
      // but never wait longer than that. The window shows as soon as
      // ready-to-show + did-finish-load both fire.
      setTimeout(() => {
        _splashMinTimeDone = true
        _tryShowMain()
      }, 800)
      resolve(null)
    }
  })

  // Wait for both to complete
  await Promise.all([backendPromise, windowPromise])

  // Fallback: force splash close and show main window after 15s
  setTimeout(() => {
    if (splashScreen && !splashScreen.isDestroyed()) {
      logger.info("[Splash] Fallback close after 15s timeout")
      closeSplashScreen()
    }
    _splashMinTimeDone = true
    _tryShowMain()
  }, 15000)

  // ═══════════════════════════════════════════════════════════════════════════════
  // POST-STARTUP INITIALIZATION (Lazy loading)
  // ═══════════════════════════════════════════════════════════════════════════════

  // Lazy initialize non-critical features after splash fades
  if (win) {
    setTimeout(() => {
      // Initialize overlay adapter
      if (!overlayAdapter) {
        overlayAdapter = new OverlayAdapter(win)
        overlayAdapter.setupIpcHandlers()
      }

      // Initialize screen recorder
      if (!screenRecorder) {
        screenRecorder = new ScreenRecorder(win)
        screenRecorder.registerIpcHandlers()
      }
    }, 6000) // Delay 6s (after splash fades)
  }

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
  const savedAutoSS = store.get("autoScreenshotEnabled", true)
  if (savedAutoSS) {
    const interval = store.get("autoScreenshotInterval", 3000)
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
        ensureTopmost(win)
      }
    } else {
      stealth.enable()
      store.set("stealthState", true)
      // Re-assert always on top after stealth enable
      if (win) {
        ensureTopmost(win)
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
      ensureTopmost(win)
      // Restart auto-screenshot if enabled
      const savedAutoSS = store.get("autoScreenshotEnabled", true)
      if (savedAutoSS && !autoScreenshotInterval) {
        const interval = store.get("autoScreenshotInterval", 3000)
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

  // Ctrl+Shift+Enter — screen-only AI answer (Cluely stealth answer, no voice input)
  registerShortcut("CommandOrControl+Shift+Enter", "trigger ai screen", () => {
    if (win?.webContents) {
      win.webContents.send("trigger-ai-screen", {})
    }
  })

  // F12 — toggle Developer Tools (Ctrl+Shift+I conflicts on some platforms)
  registerShortcut("F12", "toggle devtools", () => {
    if (win?.webContents) {
      if (win.webContents.isDevToolsOpened()) {
        win.webContents.closeDevTools()
      } else {
        win.webContents.openDevTools({ mode: "detach" })
      }
    }
  })

  // ═══════════════════════════════════════════════════════════════════════════════
  // CAPTION OVERLAY WINDOW
  // ═══════════════════════════════════════════════════════════════════════════════
  let captionWindow = null

  function createCaptionWindow() {
    if (captionWindow && !captionWindow.isDestroyed()) {
      captionWindow.show()
      captionWindow.focus()
      return captionWindow
    }

    captionWindow = new BrowserWindow({
      width: 500,
      height: 300,
      x: 50,
      y: 50,
      frame: false,
      transparent: true,
      alwaysOnTop: true,
      skipTaskbar: true,
      resizable: true,
      hasShadow: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, "preload.js"),
      },
    })

    // T3: Register CSP nonce for caption window
    const captionNonce = crypto.randomBytes(16).toString("base64")
    captionWindow.cspNonce = captionNonce
    _cspNonceMap.set(captionWindow.webContents.id, captionNonce)
    captionWindow.webContents.on("destroyed", () => { _cspNonceMap.delete(captionWindow.webContents.id) })

    if (PLATFORM === "win32") {
      captionWindow.setAlwaysOnTop(true, "monitor", 2147483647)
    }

    const captionPath = isProd
      ? path.join(process.resourcesPath, "renderer", "caption-overlay.html")
      : path.join(__dirname, "..", "apps", "web", "caption-overlay.html")

    captionWindow.loadFile(captionPath).catch(() => {
      // Fallback: load from backend URL
      captionWindow.loadURL(`http://127.0.0.1:8000/apps/web/caption-overlay.html`).catch(() => {})
    })

    captionWindow.on("closed", () => {
      captionWindow = null
    })

    return captionWindow
  }

  ipcMain.handle("caption:show", () => {
    createCaptionWindow()
    return true
  })

  ipcMain.handle("caption:hide", () => {
    if (captionWindow && !captionWindow.isDestroyed()) {
      captionWindow.hide()
    }
    return true
  })

  ipcMain.handle("caption:toggle", () => {
    if (captionWindow && !captionWindow.isDestroyed() && captionWindow.isVisible()) {
      captionWindow.hide()
      return false
    } else {
      createCaptionWindow()
      return true
    }
  })

  // Hotkey: Ctrl+Shift+C to toggle caption overlay
  globalShortcut.register("CommandOrControl+Shift+C", () => {
    if (captionWindow && !captionWindow.isDestroyed() && captionWindow.isVisible()) {
      captionWindow.hide()
    } else {
      createCaptionWindow()
    }
  })

  // ═══════════════════════════════════════════════════════════════════════════════
  // INTERVIEW OVERLAY WINDOW
  // ═══════════════════════════════════════════════════════════════════════════════
  let interviewOverlayWindow = null

  function createInterviewOverlayWindow() {
    if (interviewOverlayWindow && !interviewOverlayWindow.isDestroyed()) {
      interviewOverlayWindow.show()
      interviewOverlayWindow.focus()
      return interviewOverlayWindow
    }

    interviewOverlayWindow = new BrowserWindow({
      width: 380,
      height: 420,
      x: 60,
      y: 60,
      frame: false,
      transparent: true,
      alwaysOnTop: true,
      skipTaskbar: true,
      resizable: true,
      hasShadow: false,
      backgroundColor: "#00000000",
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, "preload.js"),
      },
    })

    // CSP nonce
    const ioNonce = crypto.randomBytes(16).toString("base64")
    interviewOverlayWindow.cspNonce = ioNonce
    _cspNonceMap.set(interviewOverlayWindow.webContents.id, ioNonce)
    interviewOverlayWindow.webContents.on("destroyed", () => { _cspNonceMap.delete(interviewOverlayWindow.webContents.id) })

    if (PLATFORM === "win32") {
      interviewOverlayWindow.setAlwaysOnTop(true, "monitor", 2147483647)
    }

    const ioPath = isProd
      ? path.join(process.resourcesPath, "renderer", "interview-overlay.html")
      : path.join(__dirname, "..", "apps", "web", "interview-overlay.html")

    interviewOverlayWindow.loadFile(ioPath).catch(() => {
      interviewOverlayWindow.loadURL(`http://127.0.0.1:8000/apps/web/interview-overlay.html`).catch(() => {})
    })

    interviewOverlayWindow.on("closed", () => {
      interviewOverlayWindow = null
    })

    return interviewOverlayWindow
  }

  ipcMain.handle("interview-overlay:show", () => {
    createInterviewOverlayWindow()
    return true
  })

  ipcMain.handle("interview-overlay:hide", () => {
    if (interviewOverlayWindow && !interviewOverlayWindow.isDestroyed()) {
      interviewOverlayWindow.hide()
    }
    return true
  })

  ipcMain.handle("interview-overlay:toggle", () => {
    if (interviewOverlayWindow && !interviewOverlayWindow.isDestroyed() && interviewOverlayWindow.isVisible()) {
      interviewOverlayWindow.hide()
      return false
    } else {
      createInterviewOverlayWindow()
      return true
    }
  })

  ipcMain.handle("interview-overlay:click-through", (event, enabled) => {
    if (interviewOverlayWindow && !interviewOverlayWindow.isDestroyed()) {
      interviewOverlayWindow.setIgnoreMouseEvents(enabled, { forward: true })
    }
  })

  ipcMain.handle("interview-overlay:opacity", (event, delta) => {
    if (interviewOverlayWindow && !interviewOverlayWindow.isDestroyed()) {
      const current = interviewOverlayWindow.getOpacity()
      const next = Math.max(0.3, Math.min(1.0, current + delta))
      interviewOverlayWindow.setOpacity(next)
      return next
    }
    return null
  })

  // Forward hotkey events from interview overlay to main window
  ipcMain.on("hotkey-toggle-mic", () => {
    if (win && !win.isDestroyed()) {
      win.webContents.send("hotkey-toggle-mic")
    }
  })

  ipcMain.on("hotkey-stealth-answer", () => {
    if (win && !win.isDestroyed()) {
      win.webContents.send("trigger-ai-screen")
    }
  })

  // Interview overlay context sync
  let _interviewOverlayContext = { company: "", role: "", skills: [], experience: "" }

  function sendInterviewContext(ctx) {
    _interviewOverlayContext = { ..._interviewOverlayContext, ...ctx }
    if (interviewOverlayWindow && !interviewOverlayWindow.isDestroyed()) {
      interviewOverlayWindow.webContents.send("interview:context", _interviewOverlayContext)
    }
  }

  ipcMain.on("interview-overlay:ready", () => {
    if (interviewOverlayWindow && !interviewOverlayWindow.isDestroyed()) {
      interviewOverlayWindow.webContents.send("interview:context", _interviewOverlayContext)
    }
  })

  ipcMain.handle("interview-overlay:set-context", (_event, ctx) => {
    sendInterviewContext(ctx)
    return true
  })

  // Hotkey: Ctrl+Shift+I to toggle interview overlay
  globalShortcut.register("CommandOrControl+Shift+I", () => {
    if (interviewOverlayWindow && !interviewOverlayWindow.isDestroyed() && interviewOverlayWindow.isVisible()) {
      interviewOverlayWindow.hide()
    } else {
      createInterviewOverlayWindow()
    }
  })

  // ═══════════════════════════════════════════════════════════════════════════════
  // OVERLAY HOTKEYS
  // ═══════════════════════════════════════════════════════════════════════════════
  if (overlayAdapter) {
    overlayAdapter.registerHotkeys()
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else if (win) {
      win.show()
      win.focus()
      ensureTopmost(win)
    }
  })
})

app.on("will-quit", () => {
  app.isQuitting = true
  logger.info("[Main] will-quit event triggered")
  globalShortcut.unregisterAll()
  backendStopped = true  // prevent crash-restart loop during shutdown
  stopHealthCheck()
  if (backendProcess) {
    logger.info("[Main] Killing backend process")
    backendProcess.kill()
  }
  if (overlayAdapter) overlayAdapter.destroy()
  if (screenRecorder) screenRecorder.destroy()
})

app.on("window-all-closed", () => {
  // On macOS, apps typically stay open until explicitly quit (Cmd+Q)
  if (PLATFORM !== "darwin") app.quit()
})
