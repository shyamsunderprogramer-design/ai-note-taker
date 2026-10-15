// Sign actual Mach-O binaries before Electron seals the outer app bundle.
// Data, static archives and symlinks must not be passed to codesign.
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const MACH_O = new Set(['feedface', 'cefaedfe', 'feedfacf', 'cffaedfe', 'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca']);

exports.default = async function signRuntime(context) {
  if (context.electronPlatformName !== 'darwin') return;
  const resources = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.app`, 'Contents/Resources');
  function visit(filename) {
    const stat = fs.lstatSync(filename);
    if (stat.isSymbolicLink()) return;
    if (stat.isDirectory()) {
      for (const child of fs.readdirSync(filename)) visit(path.join(filename, child));
      return;
    }
    if (!stat.isFile() || stat.size < 4) return;
    const fd = fs.openSync(filename, 'r');
    const magic = Buffer.alloc(4);
    try { fs.readSync(fd, magic, 0, 4, 0); } finally { fs.closeSync(fd); }
    if (MACH_O.has(magic.toString('hex'))) {
      execFileSync('/usr/bin/codesign', ['--force', '--sign', '-', '--timestamp=none', filename], { stdio: 'pipe' });
    }
  }
  visit(path.join(resources, 'python'));
  visit(path.join(resources, 'audiotee'));
};
