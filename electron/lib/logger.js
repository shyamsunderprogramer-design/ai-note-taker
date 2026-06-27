/**
 * Logger module — wraps electron-log with file rotation + production
 * mode suppression.
 *
 * Exposed as a single shared `logger` instance. The file transport
 * is disabled in packaged builds to keep the app on disk
 * footprint minimal (also reduces risk of leaking sensitive
 * operation data via the log file).
 *
 * Usage:
 *   const { logger } = require('./lib/logger')
 *   logger.info('...')
 *   logger.warn('...')
 *   logger.error('...')
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

module.exports = {
  logger: log,
  /**
   * Call once `app.isPackaged` is reliable (after `app.whenReady()`).
   * Idempotent — safe to call multiple times.
   */
  configureForProduction() {
    log.transports.file.level = false
  },
}
