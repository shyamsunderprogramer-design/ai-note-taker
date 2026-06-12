#!/usr/bin/env node
/**
 * packages the chrome extension into a .zip suitable for the Chrome
 * Web Store upload. Excludes dev-only files (.md, scripts/, package.json,
 * node_modules, this packaging script).
 *
 * Usage: npm run package
 *        # or
 *        node scripts/package.js
 *
 * Output: ../ant-chrome-extension-v<version>.zip
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const PKG = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'package.json'), 'utf-8')
);

const EXCLUDE = [
  'scripts/',
  'package.json',
  'package-lock.json',
  'node_modules/',
  '.DS_Store',
  '*.md',
];

const OUT = path.resolve(
  ROOT,
  '..',
  '..',
  `ant-chrome-extension-v${PKG.version}.zip`
);

const cmd = [
  'zip',
  '-r',
  JSON.stringify(OUT),
  '.',
  ...EXCLUDE.flatMap((p) => ['-x', p]),
].join(' ');

console.log(`[ant-chrome-extension] packaging v${PKG.version}...`);
console.log(`[ant-chrome-extension] cmd: ${cmd}`);

try {
  execSync(cmd, { cwd: ROOT, stdio: 'inherit' });
  console.log(`[ant-chrome-extension] OK -> ${OUT}`);
} catch (e) {
  console.error(`[ant-chrome-extension] FAILED: ${e.message}`);
  process.exit(1);
}
