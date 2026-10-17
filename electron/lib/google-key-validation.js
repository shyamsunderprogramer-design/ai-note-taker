// Validate the exact proposed credential before replacing the saved key.
async function validateGoogleKey(apiKey, fetchImpl = globalThis.fetch) {
  if (typeof apiKey !== 'string' || /\s/.test(apiKey) || !/^[\x21-\x7e]{20,4096}$/.test(apiKey)) {
    return { success: false, error: 'Paste the complete Google API key without spaces.' }
  }
  try {
    const response = await fetchImpl('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent', {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(20000),
      headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
      body: JSON.stringify({ contents: [{ parts: [{ text: 'Reply OK.' }] }], generationConfig: { maxOutputTokens: 256 } }),
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = String(body.error?.message || response.statusText || 'Request failed').split(apiKey).join('[redacted]').slice(0, 500)
      const invalid = response.status === 401 || /API_KEY_INVALID|API key not valid|key.*(?:expired|invalid|revoked)/i.test(JSON.stringify(body.error || {}))
      const help = invalid ? ' Get a new key in Google AI Studio.' : response.status === 429 ? ' Check quota/billing or retry later; a new key may not help.' : response.status === 403 ? ' Check Gemini API access and key restrictions.' : ' Retry after resolving this error.'
      return { success: false, error: `Google (${response.status}): ${detail}${help}` }
    }
    const answer = body.candidates?.some(c => c.content?.parts?.some(p => !p.thought && typeof p.text === 'string' && p.text.trim()))
    if (!answer) return { success: false, error: 'Google returned no answer. Key verification was inconclusive; retry.' }
    return { success: true, validated: true }
  } catch (error) {
    return { success: false, error: error.name === 'TimeoutError' || error.name === 'AbortError' ? 'Google verification timed out. Retry.' : 'Could not connect to Google for verification. Check your connection and retry.' }
  }
}
module.exports = { validateGoogleKey }
