// Sign actual Mach-O binaries before Electron seals the outer app bundle.
// Data, static archives and symlinks must not be passed to codesign.
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const MACH_O = new Set(['feedface', 'cefaedfe', 'feedfacf', 'cffaedfe', 'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca']);

exports.default = async function signRuntime(context) {
  if (context.electronPlatformName !== 'darwin') return;
  const resources = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.app`, 'Contents/Resources');
  function signFile(filename) {
    const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    const magic = Buffer.alloc(4);
    try {
      const stat = fs.fstatSync(fd);
      if (!stat.isFile() || stat.size < 4) return;
      fs.readSync(fd, magic, 0, 4, 0);
    } finally { fs.closeSync(fd); }
    if (MACH_O.has(magic.toString('hex'))) {
      execFileSync('/usr/bin/codesign', ['--force', '--sign', '-', '--timestamp=none', filename], { stdio: 'pipe' });
    }
  }
  function visit(directory) {
    for (const child of fs.readdirSync(directory, { withFileTypes: true })) {
      const filename = path.join(directory, child.name);
      if (child.isDirectory()) visit(filename);
      else if (child.isFile()) signFile(filename);
    }
  }
  visit(path.join(resources, 'python'));
  signFile(path.join(resources, 'audiotee'));
  signFile(path.join(resources, 'ant-screen-capture'));
};
