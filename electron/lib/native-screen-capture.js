const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const execute = promisify(execFile);
let binaryPromise;
async function getBinary() {
  if (!binaryPromise) {
    binaryPromise = (async () => {
      const source = path.join(__dirname, 'screen-capture.swift');
      const digest = crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex').slice(0,16);
      const directory = path.join(os.tmpdir(), `ant-screen-capture-${process.getuid()}`);
      await fs.mkdir(directory, { recursive: true, mode: 0o700 });
      const stat = await fs.lstat(directory);
      if (stat.isSymbolicLink() || stat.uid !== process.getuid()) throw new Error('Unsafe screen capture cache directory');
      await fs.chmod(directory, 0o700);
      const binary = path.join(directory, `capture-${digest}`);
      try { await fs.access(binary, fs.constants.X_OK); }
      catch {
        const temporary = `${binary}-${process.pid}`;
        await execute('/usr/bin/xcrun', ['swiftc', '-parse-as-library', source, '-O', '-module-cache-path', path.join(directory,'modules'), '-o', temporary], { timeout: 120000 });
        await fs.rename(temporary, binary);
      }
      return binary;
    })().catch(error => { binaryPromise = null; throw error; });
  }
  return binaryPromise;
}
async function captureNativeScreen(displayId, excludedPid = process.pid) {
  const binary = await getBinary();
  const { stdout } = await execute(binary, [String(excludedPid), String(displayId)], { encoding: 'buffer', maxBuffer: 16 * 1024 * 1024, timeout: 15000 });
  if (!stdout.length) throw new Error('Screen capture returned an empty image');
  return stdout.toString('base64');
}
module.exports = { captureNativeScreen, getBinary };
