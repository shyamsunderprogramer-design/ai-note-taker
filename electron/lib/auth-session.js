const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { fileURLToPath } = require('node:url');

function readPrivateFile(filename) {
  const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > 128 * 1024) throw Error('Invalid authentication storage');
    return fs.readFileSync(fd);
  } finally { fs.closeSync(fd); }
}

function writePrivateFile(filename, bytes, createOnly = false) {
  fs.mkdirSync(path.dirname(filename), { recursive: true, mode: 0o700 });
  const temporary = `${filename}.${crypto.randomBytes(12).toString('hex')}.tmp`;
  fs.writeFileSync(temporary, bytes, { flag: 'wx', mode: 0o600 });
  try {
    if (createOnly) fs.linkSync(temporary, filename);
    else fs.renameSync(temporary, filename);
  } finally {
    try { fs.unlinkSync(temporary); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
}

function backendSigningSecret(directory, configured = '') {
  if (configured) return configured;
  const filename = path.join(directory, 'jwt-secret');
  try { readPrivateFile(filename); }
  catch (error) {
    if (error.code !== 'ENOENT') throw error;
    try { writePrivateFile(filename, crypto.randomBytes(32).toString('hex'), true); }
    catch (creationError) { if (creationError.code !== 'EEXIST') throw creationError; }
  }
  const secret = readPrivateFile(filename).toString('utf8');
  if (!/^[a-f0-9]{64}$/.test(secret)) throw Error('Invalid saved authentication signing key');
  return secret;
}

function validateSession(value) {
  if (!value || typeof value.access_token !== 'string' || !value.access_token || value.access_token.length > 16384 ||
      (value.refresh_token != null && (typeof value.refresh_token !== 'string' || value.refresh_token.length > 16384))) {
    throw Error('Invalid login session');
  }
  return { access_token: value.access_token, refresh_token: value.refresh_token || null,
    remember: value.remember === true, expires_at: Number(value.expires_at) || 0 };
}

function createAuthSessionStore({ directory, safeStorage, platform = process.platform }) {
  const filename = path.join(directory, 'remembered-session.bin');
  let session = null;
  let loaded = false;
  const encryptionAvailable = () => safeStorage.isEncryptionAvailable() &&
    !(platform === 'linux' && safeStorage.getSelectedStorageBackend() === 'basic_text');
  function load() {
    if (loaded) return;
    // A temporarily locked keychain must not erase the saved session.
    if (!fs.existsSync(filename)) { loaded = true; return; }
    if (!encryptionAvailable()) throw Error('Unlock your system keychain to restore your ANT login.');
    session = validateSession(JSON.parse(safeStorage.decryptString(readPrivateFile(filename))));
    loaded = true;
  }
  function clear() {
    try { fs.unlinkSync(filename); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    session = null;
    loaded = true;
  }
  return {
    get() { load(); return session ? { ...session } : null; },
    set(value) {
      const next = validateSession(value);
      if (next.remember) {
        if (!encryptionAvailable()) throw Error('Secure storage is unavailable. Unlock your system keychain or turn off Remember me.');
        writePrivateFile(filename, safeStorage.encryptString(JSON.stringify(next)));
      } else {
        clear();
      }
      session = next;
      loaded = true;
    },
    clear,
  };
}

function isAppFrame(event, rendererDirectory) {
  try {
    if (!event.senderFrame || event.senderFrame !== event.sender.mainFrame) return false;
    const url = new URL(event.senderFrame.url);
    if (url.protocol !== 'file:' || url.host) return false;
    const relative = path.relative(rendererDirectory, fileURLToPath(url));
    return !!relative && !relative.startsWith('..') && !path.isAbsolute(relative) && relative.endsWith('.html');
  } catch { return false; }
}

function createSessionRefresher(sessionStore, fetch = globalThis.fetch) {
  let pending;
  return async function refresh() {
    if (pending) return pending;
    const previous = sessionStore.get();
    if (!previous?.refresh_token) return false;
    const stillCurrent = () => sessionStore.get()?.refresh_token === previous.refresh_token;
    pending = (async () => {
      let response;
      try {
        response = await fetch('http://127.0.0.1:8000/auth/refresh', {
          method: 'POST', body: new URLSearchParams({refresh_token: previous.refresh_token}),
          signal: AbortSignal.timeout(10000),
        });
      } catch {
        throw Error("Can't reach the ANT backend to renew your login. Try again shortly.");
      }
      if (!stillCurrent()) return false;
      if (response.status === 401 || response.status === 403) { sessionStore.clear(); return false; }
      if (!response.ok) throw Error('Could not renew your login. Try again shortly.');
      const data = await response.json();
      if (!stillCurrent()) return false;
      if (!data.access_token) throw Error('The login renewal response was incomplete.');
      sessionStore.set({...previous, access_token:data.access_token,
        expires_at:Date.now() + (Number(data.expires_in) || 86400) * 1000});
      return true;
    })();
    try { return await pending; }
    finally { pending = null; }
  };
}

function registerAuthSessionIPC({ ipcMain, sessionStore, rendererDirectory }) {
  for (const operation of ['get', 'set', 'clear']) {
    ipcMain.on(`auth:session:${operation}`, (event, value) => {
      if (!isAppFrame(event, rendererDirectory)) { event.returnValue = { error: 'Unauthorized authentication request' }; return; }
      try { event.returnValue = { value: sessionStore[operation](value) ?? null }; }
      catch (error) { event.returnValue = { error: error.message }; }
    });
  }
  const refresh = createSessionRefresher(sessionStore);
  ipcMain.handle('auth:session:refresh', async event => {
    if (!isAppFrame(event, rendererDirectory)) return {error:'Unauthorized authentication request'};
    try { return {value:await refresh()}; }
    catch (error) { return {error:error.message}; }
  });
}

module.exports = { backendSigningSecret, createAuthSessionStore, createSessionRefresher, registerAuthSessionIPC, isAppFrame };
