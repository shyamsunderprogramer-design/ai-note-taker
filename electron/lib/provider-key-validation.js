const { validateGoogleKey } = require('./google-key-validation')
const providers = {
  openai: ['OpenAI', 'https://api.openai.com/v1/chat/completions', 'gpt-4o-mini'],
  anthropic: ['Anthropic', 'https://api.anthropic.com/v1/messages', 'claude-haiku-4-5'],
  xai: ['xAI', 'https://api.x.ai/v1/chat/completions', 'grok-4.3'],
  deepseek: ['DeepSeek', 'https://api.deepseek.com/chat/completions', 'deepseek-chat'],
  groq: ['Groq', 'https://api.groq.com/openai/v1/chat/completions', 'openai/gpt-oss-20b'],
  'ollama-cloud': ['Ollama Cloud', 'https://ollama.com/api/chat', 'gemma4:31b'],
  perplexity: ['Perplexity', 'https://api.perplexity.ai/chat/completions', 'sonar'],
}
async function validateProviderKey(provider, key, fetchImpl = globalThis.fetch) {
  if (provider === 'google') return validateGoogleKey(key, fetchImpl)
  if (!Object.hasOwn(providers, provider)) return { success: false, error: 'Unsupported API key provider.' }
  if (typeof key !== 'string' || /\s/.test(key) || !/^[\x21-\x7e]{10,4096}$/.test(key)) return { success: false, error: 'Paste the complete API key without spaces.' }
  const [name, url, model] = providers[provider]
  const headers = { 'Content-Type': 'application/json' }
  if (provider === 'anthropic') Object.assign(headers, { 'x-api-key': key, 'anthropic-version': '2023-06-01' })
  else headers.Authorization = `Bearer ${key}`
  const payload = { model, messages: [{ role: 'user', content: 'Reply OK.' }], stream: false }
  if (provider === 'ollama-cloud') payload.options = { num_predict: 16 }
  else payload.max_tokens = 16
  if (provider === 'groq') { payload.max_tokens = 256; payload.reasoning_effort = 'low' }
  if (provider === 'xai') payload.reasoning_effort = 'none'
  try {
    const response = await fetchImpl(url, { method: 'POST', headers, body: JSON.stringify(payload), redirect: 'error', signal: AbortSignal.timeout(20000) })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = String(body.error?.message || body.error || response.statusText || 'Request failed').split(key).join('[redacted]').slice(0, 500)
      const hint = response.status === 401 ? ' Check or replace your API key.' : response.status === 429 ? ' Check quota/billing or retry later; a new key may not help.' : response.status === 403 ? ' Check account access and key restrictions.' : ' Resolve this provider error and retry.'
      return { success: false, error: `${name} (${response.status}): ${detail}${hint}` }
    }
    const answer = provider === 'anthropic' ? body.content?.find(p => p.type === 'text' && p.text?.trim())?.text : provider === 'ollama-cloud' ? body.message?.content : body.choices?.[0]?.message?.content
    if (typeof answer !== 'string' || !answer.trim()) return { success: false, error: `${name} returned no answer. Verification was inconclusive; retry.` }
    return { success: true, validated: true }
  } catch (error) {
    return { success: false, error: error.name === 'TimeoutError' || error.name === 'AbortError' ? `${name} verification timed out. Retry.` : `Could not connect to ${name}. Check your connection and retry.` }
  }
}
module.exports = { validateProviderKey, providers }
