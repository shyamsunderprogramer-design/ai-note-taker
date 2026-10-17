const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const path = require('node:path')
const source = fs.readFileSync(path.join(__dirname, '../../apps/web/app.js'), 'utf8')
const scope = vm.createContext({ window: {}, console, URL })
for (const name of ['escapeHtml', 'sanitizeInput', 'sanitizeUrl', 'highlightCode', 'highlightYAML', 'detectCodeLanguage', 'formatMessage', 'parseLists', 'parseMarkdownTables', 'formatSuggestionContent']) {
  const start = source.indexOf(`function ${name}(`)
  assert.ok(start >= 0, name)
  const end = source.indexOf('\n}', start) + 2
  vm.runInContext(source.slice(start, end), scope)
}

test('Markdown treats HTML payloads as text while retaining formatting', () => {
  const html = scope.formatMessage('**<img src=x onerror=alert(1)>**\n\n<svg onload=alert(1)>')
  assert.doesNotMatch(html, /<(?:img|svg)\b/)
  assert.match(html, /<strong>&lt;img/)
})

test('inline code stays escaped and Markdown links retain query strings', () => {
  const html = scope.formatMessage('`<img src=x>` [safe](https://example.com/?a=1&b=2)')
  assert.match(html, /<code class="inline-code">&lt;img src=x&gt;<\/code>/)
  assert.match(html, /href="https:\/\/example.com\/\?a=1&amp;b=2"/)
  assert.doesNotMatch(scope.formatMessage('[bad](javascript:alert(1))'), /href=/)
})

test('suggestion formatting cannot introduce active HTML', () => {
  assert.doesNotMatch(scope.formatSuggestionContent('**<img src=x onerror=alert(1)>**'), /<img\b/)
})

test('fenced HTML code remains readable without creating active elements', () => {
  const html = scope.formatMessage('```html\n<img src=x onerror=alert(1)>\n```')
  assert.match(html, /<pre class="code-block">/)
  assert.match(html, /&lt;img/)
  assert.doesNotMatch(html, /<img\b/)
})
