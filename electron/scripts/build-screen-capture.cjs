// Build on the release runner; end users never need Xcode or a Swift compiler.
const path = require('node:path');
const fs = require('node:fs');
const { execFileSync } = require('node:child_process');

function buildScreenCapture(context, execute = execFileSync) {
  if (context.electronPlatformName !== 'darwin') return;
  const arch = typeof context.arch === 'number' ? ({ 1: 'x64', 3: 'arm64' })[context.arch] : context.arch;
  if (!['x64', 'arm64'].includes(arch)) throw Error(`Unsupported screen capture architecture: ${context.arch}`);
  const directory = path.join(context.packager.projectDir, 'native', arch);
  fs.mkdirSync(directory, { recursive: true });
  execute('/usr/bin/xcrun', ['swiftc', '-parse-as-library', path.join(context.packager.projectDir, 'lib/screen-capture.swift'),
    '-O', '-target', `${arch === 'x64' ? 'x86_64' : 'arm64'}-apple-macos14.0`,
    '-o', path.join(directory, 'ant-screen-capture')], { stdio: 'pipe', timeout: 120000 });
}
exports.default = buildScreenCapture;
