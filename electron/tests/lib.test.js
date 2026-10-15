/**
 * Smoke tests for the lib/ helpers. Run with:
 *   node electron/tests/lib.test.js
 *
 * Uses node:test (built-in, no extra deps). We mock the
 * `electron` module so the lib files can be required outside
 * an Electron context.
 */
const { test } = require("node:test")
const assert = require("node:assert/strict")
const path = require("node:path")
const fs = require("node:fs")
const os = require("node:os")

// --- Mock electron BEFORE requiring lib/ ---
const tmpUserData = fs.mkdtempSync(path.join(os.tmpdir(), "ant-lib-test-"))
require.cache[require.resolve("electron")] = {
  exports: {
    app: {
      getPath: (k) => {
        if (k === "userData") return tmpUserData
        if (k === "home") return os.homedir()
        return tmpUserData
      },
      setPath: () => {},
      isPackaged: false,
    },
  },
}

// Now require the lib modules
const cryptoLib = require("../lib/crypto")
const pathsLib = require("../lib/paths")

// ───────────────────────────────────────────────────────────────
test("crypto.encryptConversation + decryptConversation roundtrip", () => {
  const key = cryptoLib.deriveConversationKey()
  const plain = "Hello, this is a test conversation transcript.\nWith multiple lines."
  const cipher = cryptoLib.encryptConversation(plain, key)
  assert.notEqual(cipher, plain, "cipher must differ from plaintext")
  const recovered = cryptoLib.decryptConversation(cipher, key)
  assert.equal(recovered, plain, "roundtrip must recover plaintext")
})

test("crypto.decryptConversation handles plaintext fallback", () => {
  const key = cryptoLib.deriveConversationKey()
  const plain = "legacy unencrypted text"
  const recovered = cryptoLib.decryptConversation(plain, key)
  assert.equal(recovered, plain, "non-JSON input should pass through unchanged")
})

test("crypto.deriveApiKeySalt returns 32-byte Buffer", () => {
  const salt = cryptoLib.deriveApiKeySalt()
  assert.ok(Buffer.isBuffer(salt), "must be a Buffer")
  assert.equal(salt.length, 32, "must be 32 bytes")
})

test("crypto.deriveConversationKey returns 32-byte Buffer", () => {
  const key = cryptoLib.deriveConversationKey()
  assert.ok(Buffer.isBuffer(key), "must be a Buffer")
  assert.equal(key.length, 32, "must be 32 bytes")
})

test("crypto.encryptConversation produces different ciphertexts for same input (random IV)", () => {
  const key = cryptoLib.deriveConversationKey()
  const plain = "same input twice"
  const c1 = cryptoLib.encryptConversation(plain, key)
  const c2 = cryptoLib.encryptConversation(plain, key)
  assert.notEqual(c1, c2, "random IV must produce different ciphertexts")
})

test("paths.PLATFORM is a known string", () => {
  assert.ok(["win32", "darwin", "linux"].includes(pathsLib.PLATFORM))
})

test("paths.isPortableMode returns false in default test env", () => {
  assert.equal(pathsLib.isPortableMode(), false)
})

test("paths.ensureConversationsDir creates the dir if missing", () => {
  const appDataDir = path.join(tmpUserData, "test-app-data")
  fs.mkdirSync(appDataDir, { recursive: true })
  const result = pathsLib.ensureConversationsDir(appDataDir)
  assert.ok(fs.existsSync(result), "conversations dir should now exist")
})

test("paths.ensureConversationsDir is idempotent", () => {
  const appDataDir = path.join(tmpUserData, "test-app-data-2")
  fs.mkdirSync(appDataDir, { recursive: true })
  const r1 = pathsLib.ensureConversationsDir(appDataDir)
  const r2 = pathsLib.ensureConversationsDir(appDataDir)
  assert.equal(r1, r2, "should return the same path")
  assert.ok(fs.existsSync(r1))
})

// Cleanup
test("cleanup tmp dir", () => {
  fs.rmSync(tmpUserData, { recursive: true, force: true })
})
