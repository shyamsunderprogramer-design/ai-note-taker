/**
 * Crypto helpers — AES-256-CBC encryption for conversation files
 * and the API key store salt derivation.
 *
 * Both helpers derive a per-machine 32-byte key from the userData
 * path. The salt is fixed and versioned (changes to the salt
 * invalidate all existing encrypted data — bump the version suffix
 * in the salt when making a breaking change and document the
 * migration path).
 */
const crypto = require("crypto")
const path = require("path")
const fs = require("fs")
const os = require("os")
const { app } = require("electron")

/** Derive the per-machine encryption key for the API key store. */
function deriveApiKeySalt() {
  return crypto.scryptSync(
    app.getPath("userData") + ":ant-key-store",
    "ai-note-taker-salt-v2",
    32
  )
}

/** Derive the per-machine encryption key for conversation files. */
function deriveConversationKey() {
  return crypto.scryptSync(
    app.getPath("userData") + ":ant-conversations",
    "ai-note-taker-convo-salt-v1",
    32
  )
}

/** Encrypt a plaintext string (UTF-8) into a JSON envelope. */
function encryptConversation(plainText, _convoKey) {
  const iv = crypto.randomBytes(16)
  const cipher = crypto.createCipheriv("aes-256-cbc", _convoKey, iv)
  let encrypted = cipher.update(plainText, "utf8", "hex")
  encrypted += cipher.final("hex")
  return JSON.stringify({ iv: iv.toString("hex"), data: encrypted })
}

/** Decrypt a JSON envelope back into plaintext. If the input is
 *  not a valid envelope (e.g., legacy plaintext), return as-is. */
function decryptConversation(cipherText, _convoKey) {
  try {
    const parsed = JSON.parse(cipherText)
    if (!parsed.iv || !parsed.data) return cipherText // plaintext fallback
    const decipher = crypto.createDecipheriv(
      "aes-256-cbc",
      _convoKey,
      Buffer.from(parsed.iv, "hex")
    )
    let decrypted = decipher.update(parsed.data, "hex", "utf8")
    decrypted += decipher.final("utf8")
    return decrypted
  } catch (e) {
    return cipherText
  }
}

/** Delete a corrupt API key store file. Used when the encryption
 *  key changes and the existing file can't be decrypted. */
function resetApiKeyStoreFile(logger) {
  const keyFilePath = path.join(app.getPath("userData"), "secure-api-keys.json")
  try {
    fs.unlinkSync(keyFilePath)
  } catch (e) {
    if (logger) logger.warn("[API Key Store] Could not delete key file: %s", e.message)
  }
  // Also clean up old key file from before the userData path change
  try {
    const _oldUserData = path.join(
      app.getPath("home") || os.homedir(),
      "AppData",
      "Roaming",
      "ai-note-taker"
    )
    const oldFile = path.join(_oldUserData, "secure-api-keys.json")
    if (fs.existsSync(oldFile)) fs.unlinkSync(oldFile)
  } catch (e) {
    if (logger) logger.warn("[API Key Store] Could not delete old key file: %s", e.message)
  }
}

module.exports = {
  deriveApiKeySalt,
  deriveConversationKey,
  encryptConversation,
  decryptConversation,
  resetApiKeyStoreFile,
}
