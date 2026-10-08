function redact(value) {
  return visit(value, new WeakSet())
}
function visit(value, seen) {
  if (typeof value === 'string') return value
    .replace(/([?&](?:token|api_key|access_token|refresh_token|secret)=)[^\s&"']+/gi, '$1[redacted]')
    .replace(/(Bearer\s+)[\w.-]+/gi, '$1[redacted]')
    .replace(/\beyJ[\w-]+\.[\w-]+\.[\w-]+\b/g, '[redacted]')
    .replace(/("(?:password|api[_-]?key|access_token|refresh_token|secret)"\s*:\s*")[^"]*"/gi, '$1[redacted]"')
  if (value instanceof Error) return visit(value.stack || value.message, seen)
  if (value && typeof value === 'object') {
    if (seen.has(value)) return '[circular]'
    seen.add(value)
    if (Array.isArray(value)) return value.map(item => visit(item, seen))
    return Object.fromEntries(Object.entries(value).map(([key,item]) =>
      [key, /^(?:password|token|api_?key|authorization|access_token|refresh_token|secret)$/i.test(key) ? '[redacted]' : visit(item, seen)]))
  }
  return value
}
module.exports = {redact}
