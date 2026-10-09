'use strict';
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// Each run owns an unpredictable directory. A shared run can pass its directory
// explicitly; never adopt a symlink or another user's accessible directory.
function artifactDirectory(prefix, existing) {
  if (!existing) return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  const directory = path.resolve(existing);
  const stat = fs.lstatSync(directory);
  if (!stat.isDirectory() || stat.isSymbolicLink() ||
      (typeof process.getuid === 'function' &&
       (stat.uid !== process.getuid() || (stat.mode & 0o077) !== 0))) {
    throw new Error('Artifact directory must be a private directory owned by this user');
  }
  return directory;
}

function readPrivateJson(filename) {
  const fd = fs.openSync(filename, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > 65536 ||
        (typeof process.getuid === 'function' &&
         (stat.uid !== process.getuid() || (stat.mode & 0o077) !== 0))) {
      throw new Error('Credentials must be a small private file owned by this user');
    }
    return JSON.parse(fs.readFileSync(fd, 'utf8'));
  } finally {
    fs.closeSync(fd);
  }
}

module.exports = { artifactDirectory, readPrivateJson };
