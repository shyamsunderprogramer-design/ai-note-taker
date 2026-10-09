const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')
const scope = vm.createContext({ URL })
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../apps/ant-chrome-extension/url-safety.js'), 'utf8'), scope)
const matches = scope.ANTPlatformUrls.matches

test('platform matching validates hostname rather than URL substrings', () => {
  for (const url of ['https://evil.example/?next=https://meet.google.com',
    'https://meet.google.com.evil.example', 'https://meet.google.com@evil.example',
    'javascript:meet.google.com', 'not-a-url']) {
    assert.equal(matches(url, 'meet.google.com'), false, url)
  }
  assert.equal(matches('https://meet.google.com/abc-defg-hij', 'meet.google.com'), true)
  assert.equal(matches('https://company.zoom.us/j/123', 'zoom.us/j'), true)
  assert.equal(matches('https://company.zoom.us/profile', 'zoom.us/j'), false)
  assert.equal(matches('https://company.zoom.us/junk', 'zoom.us/j'), false)
})
