/* Loaded before content/popup scripts and imported by the service worker. */
globalThis.ANTPlatformUrls = Object.freeze({
  matches(raw, pattern) {
    try {
      const url = new URL(raw)
      if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return false
      const slash = pattern.indexOf('/')
      const domain = slash < 0 ? pattern : pattern.slice(0, slash)
      const prefix = slash < 0 ? '' : pattern.slice(slash)
      return (url.hostname === domain || url.hostname.endsWith('.' + domain)) &&
        (!prefix || url.pathname === prefix || url.pathname.startsWith(prefix.replace(/\/$/, '') + '/'))
    } catch {
      return false
    }
  }
})
