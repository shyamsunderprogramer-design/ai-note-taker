const { test } = require('node:test')
const assert = require('node:assert/strict')
const { validateGoogleKey } = require('../lib/google-key-validation')
const key = 'AQ.' + 'x'.repeat(300)
test('long AQ key is sent unchanged and requires generated text', async () => {
  const result = await validateGoogleKey(key, async (url, request) => {
    assert.equal(request.headers['x-goog-api-key'], key)
    assert.equal(request.method, 'POST')
    assert.equal(JSON.parse(request.body).generationConfig.maxOutputTokens, 256)
    return { ok: true, json: async () => ({ candidates: [{ content: { parts: [{ text: 'OK' }] } }] }) }
  })
  assert.equal(result.validated, true)
})
test('invalid credential error is actionable and redacts credential', async () => {
  const r = await validateGoogleKey(key, async () => ({ ok: false, status: 400, json: async () => ({ error: { message: 'API key not valid: ' + key } }) }))
  assert.equal(r.success, false)
  assert.match(r.error, /Get a new key/)
  assert.ok(!r.error.includes(key))
})
test('quota is not reported as invalid key', async () => {
  const r = await validateGoogleKey(key, async () => ({ ok: false, status: 429, json: async () => ({ error: { message: 'Quota exceeded' } }) }))
  assert.match(r.error, /quota\/billing/)
  assert.doesNotMatch(r.error, /Get a new key/)
})
test('empty responses and timeouts never validate', async () => {
  assert.equal((await validateGoogleKey(key, async () => ({ ok: true, json: async () => ({}) }))).success, false)
  assert.match((await validateGoogleKey(key, async () => { throw Object.assign(new Error(), { name: 'TimeoutError' }) })).error, /timed out/)
})
test('whitespace is rejected without making a request', async () => {
  let called = false
  assert.equal((await validateGoogleKey(key + '\n', async () => { called = true })).success, false)
  assert.equal(called, false)
})
