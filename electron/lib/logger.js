/**
 * Logger module — wraps electron-log with file rotation + production
 * mode suppression + scoped backend-crash log.
 *
 * Behavior:
 *   - Dev (non-packaged): full file log at info level (5MB rotation).
 *   - Prod (packaged): main file transport DISABLED for stealth mode
 *     (logs only go to console / memory).
 *   - Prod (packaged): a SEPARATE small error-only log is configured
 *     at userData/logs/backend-crash.log so backend spawn failures
 *     leave an on-disk artifact users/support can inspect. 100 KB cap,
 *     rotates to .old.log. Toggled via configureBackendCrashLog()
 *     once `app.whenReady()` fires (we need `app.getPath('userData')`).
 *
 * Usage:
 *   const { logger } = require('./lib/logger')
 *   logger.info('...')
 *   logger.warn('...')
 *   logger.error('[Backend] ...')   // ends up in backend-crash.log too
 */
const log = require("electron-log/main")

log.initialize()
log.transports.file.level = "info"
log.transports.console.level = "debug"
log.transports.file.maxSize = 5 * 1024 * 1024 // 5MB rotation

// Disable file logging in production for stealth mode
// Logs only go to console (memory), not to disk
try {
  const { app } = require("electron")
  if (app.isPackaged) {
    log.transports.file.level = false
  }
} catch (e) {
  // `app` is only available after the ready event. The caller can
  // also call configureForProduction() once `app` is ready.
}

// Scoped backend crash log: small, error-only, on-disk file in
// production ONLY. Lets us diagnose "backend failed to spawn" cases
// when the user reports problems, without violating stealth mode for
// the general log. Configured lazily because we need app.getPath.
let crashLogConfigured = false
function configureBackendCrashLog() {
  if (crashLogConfigured) return
  crashLogConfigured = true
  try {
    const { app } = require("electron")
    if (!app.isPackaged) return  // only in production
    const path = require("path")
    const fs = require("fs")
    const logDir = path.join(app.getPath("userData"), "logs")
    fs.mkdirSync(logDir, { recursive: true })
    const crashPath = path.join(logDir, "backend-crash.log")
    log.transports.file.resolvePathFn = () => crashPath
    log.transports.file.level = "error"
    log.transports.file.maxSize = 100 * 1024 // 100 KB; rotate to .old.log
  } catch (e) {
    // best-effort; if it fails we're back to console-only logging
  }
}

module.exports = {
  logger: log,
  /**
   * Call once `app.isPackaged` is reliable (after `app.whenReady()`).
   * Idempotent — safe to call multiple times.
   */
  configureForProduction() {
    log.transports.file.level = false
  },
  /**
   * Call once `app.whenReady()` has fired. Enables the scoped
   * 100 KB error-only backend-crash.log inside userData/logs/ so
   * backend spawn failures leave an on-disk trace. Idempotent.
   */
  configureBackendCrashLog,
}
