const {test} = require('node:test')
const assert = require('node:assert/strict')
const fs = require('fs')
const path = require('path')
const os = require('os')
const {initializeConversationStorage, encode, decode} = require('../lib/conversation-storage')

test('both launch names share encrypted chats, retaining backups without resurrecting deleted chats', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ant-history-test-'))
  try {
    const sources = ['Electron', 'ai-note-taker'].map(name => path.join(root, name, 'ai-note-taker-data'))
    const ids = ['11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222']
    sources.forEach((source, i) => {
      fs.mkdirSync(path.join(source, 'conversations'), {recursive: true})
      fs.writeFileSync(path.join(source, 'conversations', ids[i] + '.json'), encode({
        id: ids[i], messages: Array.from({length: i ? 2 : 44}, () => ({role: 'user', text: 'test'})),
      }, source))
    })
    const result = initializeConversationStorage(root, sources[0])
    assert.equal(result.migrated, 2)
    assert.deepEqual(result.errors, [])
    const file = path.join(result.conversationsDir, ids[0] + '.json')
    assert.equal(decode(fs.readFileSync(file, 'utf8'), result.dataDir).messages.length, 44)
    assert.equal(initializeConversationStorage(root, sources[1]).conversationsDir, result.conversationsDir)
    const latest = {id: ids[0], updatedAt: Date.now(), messages: Array.from({length: 46}, () => ({role: 'user', text: 'new'}))}
    fs.writeFileSync(path.join(sources[0], 'conversations', ids[0] + '.json'), encode(latest, sources[0]))
    assert.equal(initializeConversationStorage(root, sources[0]).migrated, 1)
    assert.equal(decode(fs.readFileSync(file, 'utf8'), result.dataDir).messages.length, 46)
    fs.unlinkSync(file)
    assert.equal(initializeConversationStorage(root, sources[0]).migrated, 0)
    assert.equal(fs.existsSync(file), false)
    assert.ok(fs.existsSync(path.join(sources[0], 'conversations', ids[0] + '.json')))
  } finally {
    fs.rmSync(root, {recursive: true, force: true})
  }
})
