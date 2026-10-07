const {test} = require('node:test')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const assert = require('node:assert/strict')
const source = fs.readFileSync(path.join(__dirname, '../../apps/web/app.js'), 'utf8').replace(/\r\n/g, '\n')
const scope = {
  sanitizeInput: text => text,
  escapeHtml: text => text.replace(/</g, '&lt;').replace(/>/g, '&gt;'),
  sanitizeUrl: text => text,
  detectCodeLanguage: () => 'code',
  highlightCode: text => text,
}
vm.createContext(scope)
vm.runInContext(source.slice(source.indexOf('function formatMessage('), source.indexOf('/**\n * Typing effect')), scope)

test('blank lines in code remain inside one preformatted block', () => {
  const html = scope.formatMessage('Before\n\n```python\ndef test():\n    x = 1\n\n    return x\n```\n\nAfter')
  assert.ok(html.includes('x = 1\n\n    return x'))
  assert.equal((html.match(/<pre /g) || []).length, 1)
  assert.ok(!html.includes('<p>    return'))
})

test('Markdown tables have aligned headers and cells', () => {
  const html = scope.formatMessage('| Step | Action |\n|---|---|\n| 1 | Rotate |\n| 2 | Handoff |')
  assert.ok(html.includes('<table'))
  assert.ok(html.includes('<th scope="col">Step</th>'))
  assert.ok(html.includes('<td>Handoff</td>'))
  assert.ok(!html.includes('|---|'))
})

test('natural answers retain short paragraphs', () => {
  const html = scope.formatMessage('A clear answer.\n\nA practical example.')
  assert.equal(html, '<p>A clear answer.</p>\n<p>A practical example.</p>')
})
