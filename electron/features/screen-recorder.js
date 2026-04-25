/**
 * screen-recorder.js - Electron screen recording module for ANT
 *
 * Provides screen/window recording and screenshot capture using
 * Electron's desktopCapturer API and the renderer-side MediaRecorder API.
 *
 * Recording flow:
 *   1. Main process calls desktopCapturer.getSources() to enumerate screens/windows
 *   2. Selected source ID is sent to the renderer via IPC
 *   3. Renderer uses navigator.mediaDevices.getUserMedia with the source ID
 *      to obtain a MediaStream, then records it with MediaRecorder
 *   4. Recorded chunks are sent back to main process and written to disk as .webm
 *
 * @module ScreenRecorder
 */

const { desktopCapturer, ipcMain, app } = require("electron")
const path = require("path")
const fs = require("fs")
const log = require("electron-log/main")

const logger = log

// ═══════════════════════════════════════════════════════════════════════════════
// RECORDINGS DIRECTORY
// ═══════════════════════════════════════════════════════════════════════════════

function getRecordingsDir() {
  const dir = path.join(app.getPath("userData"), "recordings")
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true })
  }
  return dir
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIMESTAMP FILENAME HELPER
// ═══════════════════════════════════════════════════════════════════════════════

function timestampFilename() {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, "0")
  const yyyy = now.getFullYear()
  const mm = pad(now.getMonth() + 1)
  const dd = pad(now.getDate())
  const HH = pad(now.getHours())
  const MM = pad(now.getMinutes())
  const SS = pad(now.getSeconds())
  return `recording_${yyyy}${mm}${dd}_${HH}${MM}${SS}.webm`
}

// ═══════════════════════════════════════════════════════════════════════════════
// SCREEN RECORDER CLASS
// ═══════════════════════════════════════════════════════════════════════════════

class ScreenRecorder {
  constructor(mainWindow) {
    this.mainWindow = mainWindow
    this.isRecording = false
    this.currentRecordingPath = null
    this.currentSourceId = null
    this.recordingOptions = {}

    logger.info("[ScreenRecorder] Initialized")
  }

  // ───────────────────────────────────────────────────────────────────────────
  // GET AVAILABLE SOURCES
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * List available screen and window sources via desktopCapturer.
   * Returns an array of source descriptors with id, name, and thumbnail (base64 PNG).
   */
  async getRecordingSources() {
    try {
      const sources = await desktopCapturer.getSources({
        types: ["screen", "window"],
        thumbnailSize: { width: 320, height: 180 },
        fetchWindowIcons: true
      })

      if (!sources || sources.length === 0) {
        logger.warn("[ScreenRecorder] No desktop sources found")
        return []
      }

      const result = sources.map((source) => ({
        id: source.id,
        name: source.name,
        thumbnail: source.thumbnail && !source.thumbnail.isEmpty()
          ? source.thumbnail.toPNG().toString("base64")
          : null,
        appIcon: source.appIcon && !source.appIcon.isEmpty()
          ? source.appIcon.toPNG().toString("base64")
          : null
      }))

      logger.info("[ScreenRecorder] Found %d sources", result.length)
      return result
    } catch (err) {
      logger.error("[ScreenRecorder] getRecordingSources failed: %s", err.message)
      return []
    }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // START RECORDING
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Start recording a specific source.
   * Sends the source ID to the renderer so it can set up MediaRecorder.
   *
   * @param {Electron.BrowserWindow} window - The renderer window
   * @param {object} options - Recording options
   * @param {string} options.sourceId - The desktopCapturer source ID to record
   * @param {string} [options.audio] - Whether to include audio ("system"|"mic"|false)
   * @param {number} [options.videoBitsPerSecond] - Video bitrate (default 2500000)
   */
  async startRecording(window, options = {}) {
    if (this.isRecording) {
      logger.warn("[ScreenRecorder] Already recording")
      return { success: false, error: "already_recording" }
    }

    const targetWindow = window || this.mainWindow
    if (!targetWindow || targetWindow.isDestroyed()) {
      logger.error("[ScreenRecorder] No valid window for recording")
      return { success: false, error: "no_window" }
    }

    // If no sourceId provided, default to the first screen source
    let sourceId = options.sourceId
    if (!sourceId) {
      try {
        const sources = await desktopCapturer.getSources({
          types: ["screen"],
          thumbnailSize: { width: 1, height: 1 }
        })
        if (sources.length === 0) {
          logger.error("[ScreenRecorder] No screen sources available")
          return { success: false, error: "no_sources" }
        }
        sourceId = sources[0].id
      } catch (err) {
        logger.error("[ScreenRecorder] desktopCapturer unavailable: %s", err.message)
        return { success: false, error: "desktopCapturer_unavailable", message: err.message }
      }
    }

    this.currentSourceId = sourceId
    this.recordingOptions = {
      audio: options.audio || false,
      videoBitsPerSecond: options.videoBitsPerSecond || 2500000
    }

    // Generate output file path
    const recordingsDir = getRecordingsDir()
    const filename = timestampFilename()
    this.currentRecordingPath = path.join(recordingsDir, filename)

    // Tell the renderer to start recording with the given source
    this.isRecording = true

    targetWindow.webContents.send("recorder:start-capture", {
      sourceId: sourceId,
      filePath: this.currentRecordingPath,
      options: this.recordingOptions
    })

    logger.info("[ScreenRecorder] Recording started: source=%s, file=%s", sourceId, filename)
    return { success: true, sourceId, filePath: this.currentRecordingPath }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // STOP RECORDING
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Stop the current recording.
   * Sends a stop signal to the renderer and waits for the final file path.
   */
  async stopRecording() {
    if (!this.isRecording) {
      logger.warn("[ScreenRecorder] Not currently recording")
      return { success: false, error: "not_recording" }
    }

    const targetWindow = this.mainWindow
    if (!targetWindow || targetWindow.isDestroyed()) {
      logger.error("[ScreenRecorder] No valid window to stop recording")
      this.isRecording = false
      return { success: false, error: "no_window" }
    }

    // Tell the renderer to stop recording
    targetWindow.webContents.send("recorder:stop-capture")

    // The renderer will send back "recorder:save-recording" with the blob data.
    // We resolve this promise in the IPC handler for recorder:save-recording.
    const filePath = this.currentRecordingPath
    this.isRecording = false
    this.currentSourceId = null

    logger.info("[ScreenRecorder] Recording stopped, file: %s", filePath)
    return { success: true, filePath }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // TAKE SCREENSHOT
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Capture a single frame from the primary screen.
   *
   * @param {Electron.BrowserWindow} window - Optional window reference
   * @returns {object} - { success, data (base64 PNG), filePath }
   */
  async takeScreenshot(window) {
    try {
      const sources = await desktopCapturer.getSources({
        types: ["screen"],
        thumbnailSize: { width: 1920, height: 1080 }
      })

      if (!sources || sources.length === 0) {
        logger.warn("[ScreenRecorder] No screen sources for screenshot")
        return { success: false, error: "no_sources" }
      }

      const primarySource = sources[0]
      if (!primarySource.thumbnail || primarySource.thumbnail.isEmpty()) {
        logger.warn("[ScreenRecorder] Screenshot returned empty thumbnail")
        return { success: false, error: "empty_thumbnail" }
      }

      const base64 = primarySource.thumbnail.toPNG().toString("base64")

      // Also save to recordings directory for persistence
      const recordingsDir = getRecordingsDir()
      const now = new Date()
      const pad = (n) => String(n).padStart(2, "0")
      const filename = `screenshot_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}.png`
      const filePath = path.join(recordingsDir, filename)
      fs.writeFileSync(filePath, primarySource.thumbnail.toPNG())

      logger.info("[ScreenRecorder] Screenshot saved: %s (%d bytes)", filename, base64.length)
      return { success: true, data: base64, filePath }
    } catch (err) {
      logger.error("[ScreenRecorder] Screenshot failed: %s", err.message)
      return { success: false, error: err.message }
    }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // SAVE RECORDING DATA (called when renderer sends back recorded chunks)
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Save recording data (Blob/ArrayBuffer from renderer) to disk.
   *
   * @param {Buffer} data - The recorded video data as a Buffer
   * @param {string} [filePath] - Override file path; defaults to currentRecordingPath
   */
  saveRecordingData(data, filePath) {
    const targetPath = filePath || this.currentRecordingPath
    if (!targetPath) {
      logger.error("[ScreenRecorder] No file path for saving recording")
      return { success: false, error: "no_file_path" }
    }

    try {
      const recordingsDir = getRecordingsDir()
      if (!fs.existsSync(recordingsDir)) {
        fs.mkdirSync(recordingsDir, { recursive: true })
      }

      fs.writeFileSync(targetPath, data)
      logger.info("[ScreenRecorder] Recording saved: %s (%d bytes)", targetPath, data.length)
      return { success: true, filePath: targetPath }
    } catch (err) {
      logger.error("[ScreenRecorder] Failed to save recording: %s", err.message)
      return { success: false, error: err.message }
    }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // IPC HANDLER REGISTRATION
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Register all IPC handlers for screen recording.
   * Call this once after the app is ready and the main window exists.
   */
  registerIpcHandlers() {
    // Get available recording sources
    ipcMain.handle("recorder:get-sources", async () => {
      return await this.getRecordingSources()
    })

    // Start recording with a specific source
    ipcMain.handle("recorder:start", async (_event, sourceId) => {
      const options = {
        sourceId: sourceId,
        audio: false,
        videoBitsPerSecond: 2500000
      }
      return await this.startRecording(this.mainWindow, options)
    })

    // Stop recording and return the file path
    ipcMain.handle("recorder:stop", async () => {
      return await this.stopRecording()
    })

    // Take a screenshot
    ipcMain.handle("recorder:screenshot", async () => {
      return await this.takeScreenshot(this.mainWindow)
    })

    // Receive recorded data from the renderer and save to disk
    ipcMain.handle("recorder:save-recording", async (_event, data, filePath) => {
      // data arrives as an ArrayBuffer from the renderer
      const buffer = Buffer.from(data)
      return this.saveRecordingData(buffer, filePath)
    })

    // Update main window reference (useful if window is recreated)
    ipcMain.handle("recorder:set-window", (_event) => {
      // The main window is tracked externally; this is a no-op placeholder
      // for future extensibility if multiple windows are supported
      return { success: true }
    })

    // Get current recording state
    ipcMain.handle("recorder:status", () => {
      return {
        isRecording: this.isRecording,
        currentSourceId: this.currentSourceId,
        currentRecordingPath: this.currentRecordingPath
      }
    })

    logger.info("[ScreenRecorder] IPC handlers registered")
  }

  // ───────────────────────────────────────────────────────────────────────────
  // CLEANUP
  // ───────────────────────────────────────────────────────────────────────────

  /**
   * Clean up resources. Call on app quit.
   */
  destroy() {
    if (this.isRecording) {
      // Attempt to stop recording gracefully
      try {
        this.stopRecording()
      } catch {
        // Best effort
      }
    }
    logger.info("[ScreenRecorder] Destroyed")
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// MODULE EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════

module.exports = { ScreenRecorder }