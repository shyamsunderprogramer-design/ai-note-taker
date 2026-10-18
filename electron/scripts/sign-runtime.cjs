// Sign actual Mach-O binaries before Electron seals the outer app bundle.
// Data, static archives and symlinks must not be passed to codesign.
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const MACH_O = new Set(['feedface', 'cefaedfe', 'feedfacf', 'cffaedfe', 'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca']);

exports.default = async function signRuntime(context, run = execFileSync) {
  if (context.electronPlatformName !== 'darwin') return;
  const config = context.packager.platformSpecificBuildOptions;
  let signArgs = ['--force', '--sign', '-', '--timestamp=none'];
  if (config.notarize === true) {
    if (!context.packager.forceCodeSigning || config.hardenedRuntime !== true || config.type !== 'distribution' || config.identity === '-') {
      throw new Error('Notarized runtimes require forced Developer ID distribution signing and Hardened Runtime');
    }
    // Import CSC_LINK first, then select the same identity/keychain as the outer
    // app. These APIs match the pinned electron-builder version in package.json.
    const { keychainFile } = await context.packager.codeSigningInfo.value;
    const identity = await context.packager.helper.findSigningIdentity(false, false, config.identity, keychainFile, config);
    if (!identity?.name?.startsWith('Developer ID Application:') || !identity.hash) {
      throw new Error('A Developer ID Application signing identity is required for the bundled runtime');
    }
    if (!process.env.APPLE_TEAM_ID || !identity.name.endsWith(`(${process.env.APPLE_TEAM_ID})`)) {
      throw new Error('The Developer ID signing identity does not match APPLE_TEAM_ID');
    }
    signArgs = ['--force', '--sign', identity.hash, '--timestamp', '--options', 'runtime',
      '--entitlements', path.resolve(context.packager.projectDir, config.entitlements)];
    if (keychainFile) signArgs.push('--keychain', keychainFile);
  }
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
      run('/usr/bin/codesign', [...signArgs, filename], { stdio: 'pipe' });
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
};
