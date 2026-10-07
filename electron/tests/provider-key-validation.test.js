const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const { validateProviderKey, providers } = require('../lib/provider-key-validation')
const key = 'synthetic-key.for-testing-only'
for (const provider of [...Object.keys(providers), 'google']) {
  test(`${provider}: sends exact key; requires answer; reports failures`, async () => {
    const success = await validateProviderKey(provider, key, async (url, req) => {
      assert.ok(url.startsWith('https://'))
      assert.ok(Object.values(req.headers).some(value => value === key || value === `Bearer ${key}`))
      assert.equal(req.redirect, 'error')
      const body = provider === 'google' ? { candidates: [{ content: { parts: [{ text: 'OK' }] } }] } : provider === 'anthropic' ? { content: [{ type: 'text', text: 'OK' }] } : provider === 'ollama-cloud' ? { message: { content: 'OK' } } : { choices: [{ message: { content: 'OK' } }] }
      return { ok: true, json: async () => body }
    })
    assert.equal(success.validated, true)
    for (const status of [401, 403, 429, 500]) {
      const failed = await validateProviderKey(provider, key, async () => ({ ok: false, status, json: async () => ({ error: { message: 'Provider error ' + key } }) }))
      assert.equal(failed.success, false)
      assert.ok(!failed.error.includes(key))
      assert.ok(failed.error.includes(String(status)))
    }
    assert.equal((await validateProviderKey(provider, key, async () => ({ ok: true, json: async () => ({}) }))).success, false)
    assert.equal((await validateProviderKey(provider, key, async () => { throw new Error('network') })).success, false)
  })
}
test('unsupported providers fail without network', async () => {
  let called = false
  assert.equal((await validateProviderKey('unknown', key, async () => { called = true })).success, false)
  assert.equal(called, false)
})
test('production save handler validates before storage or env changes', async () => {
  const source = fs.readFileSync(require.resolve('../main.js'), 'utf8')
  const start = source.indexOf('ipcMain.handle("apiKey:save"')
  const end = source.indexOf('ipcMain.handle("apiKey:get"', start)
  for (const valid of [false, true]) {
    let handler
    const writes = []
    vm.runInNewContext(source.slice(start, end), {
      ipcMain: { handle: (_, fn) => { handler = fn } },
      require: () => ({ validateProviderKey: async () => ({ success: valid, error: 'rejected' }) }),
      apiKeyStore: { set: () => writes.push('store') },
      logger: { info() {}, error() {} },
      _PROVIDER_ENV_MAP: { groq: 'GROQ_API_KEY' },
      _updateBackendEnv: () => writes.push('env'),
    })
    const result = await handler({}, { provider: 'groq', apiKey: key, syncToEnv: true })
    assert.equal(result.success, valid)
    assert.deepEqual(writes, valid ? ['store', 'env'] : [])
  }
})
