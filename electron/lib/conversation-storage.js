const fs = require('fs')
const path = require('path')
const crypto = require('crypto')

function readRecord(filename, dataDir) {
  const fd = fs.openSync(filename, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0))
  try {
    if (!fs.fstatSync(fd).isFile()) throw new Error('Invalid conversation file')
    return decode(fs.readFileSync(fd, 'utf8'), dataDir)
  } finally {
    fs.closeSync(fd)
  }
}

function migrationRecorded(filename) {
  try {
    const fd = fs.openSync(filename, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0))
    fs.closeSync(fd)
    return true
  } catch (error) {
    if (error.code === 'ENOENT') return false
    throw error
  }
}

function conversationKey(dataDir) {
  return crypto.scryptSync(dataDir + ':ant-conversations', 'ai-note-taker-convo-salt-v1', 32)
}

function decode(raw, dataDir) {
  let record = JSON.parse(raw)
  if (record.iv && record.data) {
    const cipher = crypto.createDecipheriv('aes-256-cbc', conversationKey(dataDir), Buffer.from(record.iv, 'hex'))
    record = JSON.parse(cipher.update(record.data, 'hex', 'utf8') + cipher.final('utf8'))
  }
  if (!record.id || !Array.isArray(record.messages)) throw new Error('Invalid conversation record')
  return record
}

function encode(record, dataDir) {
  const iv = crypto.randomBytes(16)
  const cipher = crypto.createCipheriv('aes-256-cbc', conversationKey(dataDir), iv)
  const data = cipher.update(JSON.stringify(record), 'utf8', 'hex') + cipher.final('hex')
  return JSON.stringify({ iv: iv.toString('hex'), data })
}

// Keep settings in their existing location; share only conversation history.
function initializeConversationStorage(appDataRoot, currentDataDir) {
  const dataDir = path.join(appDataRoot, 'ai-note-taker-data')
  const conversationsDir = path.join(dataDir, 'conversations')
  fs.mkdirSync(conversationsDir, { recursive: true, mode: 0o700 })
  const sources = new Set([
    currentDataDir,
    path.join(appDataRoot, 'Electron', 'ai-note-taker-data'),
    path.join(appDataRoot, 'ai-note-taker', 'ai-note-taker-data'),
    path.join(appDataRoot, 'Electron'),
    path.join(appDataRoot, 'ai-note-taker'),
  ])
  const errors = []
  let migrated = 0
  for (const source of sources) {
    if (source === dataDir) continue
    const dir = path.join(source, 'conversations')
    if (!fs.existsSync(dir)) continue
    for (const name of fs.readdirSync(dir)) {
      if (!name.endsWith('.json')) continue
      try {
        const record = readRecord(path.join(dir, name), source)
        if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(record.id)) throw new Error('Invalid conversation id')
        const target = path.join(conversationsDir, `${record.id}.json`)
        // Legacy launches may save one last update before restarting. Import
        // newer records while keeping intentional shared deletions deleted.
        const markerDir = path.join(dataDir, 'conversation-migrations')
        const marker = path.join(markerDir, crypto.createHash('sha256').update(path.join(dir, name)).digest('hex'))
        try {
          const existing = readRecord(target, dataDir)
          if ((record.updatedAt || 0) > (existing.updatedAt || 0)) {
            const temporary = target + '.' + crypto.randomUUID() + '.tmp'
            fs.writeFileSync(temporary, encode(record, dataDir), { flag: 'wx', mode: 0o600 })
            fs.renameSync(temporary, target)
            migrated++
          }
        } catch (error) {
          if (error.code !== 'ENOENT') throw error
          if (migrationRecorded(marker)) continue
          try {
            fs.writeFileSync(target, encode(record, dataDir), { flag: 'wx', mode: 0o600 })
            migrated++
          } catch (writeError) {
            if (writeError.code !== 'EEXIST') throw writeError
          }
        }
        fs.mkdirSync(markerDir, { recursive: true, mode: 0o700 })
        try {
          fs.writeFileSync(marker, '', { flag: 'wx', mode: 0o600 })
        } catch (error) {
          if (error.code !== 'EEXIST') throw error
        }
      } catch (error) {
        errors.push({ file: path.join(dir, name), message: error.message })
      }
    }
  }
  return { dataDir, conversationsDir, migrated, errors }
}

module.exports = { initializeConversationStorage, conversationKey, decode, encode }
