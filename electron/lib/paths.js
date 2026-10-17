/**
 * Paths module — centralizes the userData / conversations / store
 * locations and the portable-mode flag detection.
 *
 * Electron stores per-user data in a path like:
 *   - Windows: %APPDATA%\ai-note-taker-data\
 *   - macOS:   ~/Library/Application Support/ai-note-taker-data/
 *   - Linux:   ~/.config/ai-note-taker-data/
 *
 * We move everything under a `ai-note-taker-data/` subfolder so the
 * app's data is grouped cleanly.
 *
 * Portable mode (Windows only) keeps the data alongside the
 * executable — useful for running off a USB drive.
 */
const path = require("path")
const fs = require("fs")
const { app } = require("electron")

const PLATFORM = process.platform // 'win32' | 'darwin' | 'linux'

/** True if the app is running in portable mode (--portable flag
 *  or PORTABLE file next to the executable). */
function isPortableMode() {
  const portableFlagPath = path.join(process.resourcesPath || ".", "PORTABLE")
  return process.argv.includes("--portable") || fs.existsSync(portableFlagPath)
}

/** Migrate config from the old userData location to the new one. */
function migrateLegacyUserData(appDataDir) {
  const _origUserData = app.getPath("userData")
  const newConfigPath = path.join(appDataDir, "config.json")
  const oldConfigPath = path.join(_origUserData, "config.json")
  if (!fs.existsSync(newConfigPath) && fs.existsSync(oldConfigPath)) {
    try {
      fs.copyFileSync(oldConfigPath, newConfigPath)
      return { migrated: true, from: oldConfigPath, to: newConfigPath }
    } catch (e) {
      return { migrated: false, error: e.message }
    }
  }
  return { migrated: false, reason: "nothing to migrate" }
}

/** Initialize app.setPath() so the rest of the app reads from
 *  `ai-note-taker-data/`. Must be called BEFORE any electron-store
 *  instances are created. */
function initializeAppPaths() {
  const _origUserData = app.getPath("userData")
  const appDataDir = path.join(_origUserData, "ai-note-taker-data")
  app.setPath("userData", appDataDir)
  app.setPath("sessionData", appDataDir)
  return { appDataDir, migration: migrateLegacyUserData(appDataDir) }
}

/** Ensure `ai-note-taker-data/conversations/` exists. */
function ensureConversationsDir(appDataDir) {
  if (!appDataDir || typeof appDataDir !== "string") {
    throw new TypeError(
      `[paths] ensureConversationsDir requires a valid appDataDir string, got: ${JSON.stringify(appDataDir)}`
    )
  }
  const conversationsDir = path.join(appDataDir, "conversations")
  if (!fs.existsSync(conversationsDir)) {
    fs.mkdirSync(conversationsDir, { recursive: true })
  }
  return conversationsDir
}

module.exports = {
  PLATFORM,
  isPortableMode,
  initializeAppPaths,
  ensureConversationsDir,
}
