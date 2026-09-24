// Build the deployable app, enforce its build budget, and check local HTML assets.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const dist = resolve(root, 'apps/web/dist');
const start = performance.now();
const build = spawnSync(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['run', 'web:build'], {
  cwd: root, encoding: 'utf8', shell: process.platform === 'win32',
});
if (build.error || build.status !== 0) {
  console.error(build.error || build.stderr || build.stdout);
  process.exit(1);
}
const seconds = (performance.now() - start) / 1000;
const missing = [];
const scripts = new Set();
let checked = 0;
function checkReference(reference, page) {
  const url = new URL(reference, `https://ant.invalid/${page}`);
  if (url.origin !== 'https://ant.invalid') return;
  checked++;
  const path = resolve(dist, `.${decodeURIComponent(url.pathname)}`);
  if (!existsSync(path) || !statSync(path).isFile()) missing.push(`${page}: ${reference}`);
  else if (url.pathname.endsWith('.js')) scripts.add(path);
}
for (const page of readdirSync(dist).filter(name => name.endsWith('.html'))) {
  const html = readFileSync(resolve(dist, page), 'utf8');
  for (const [tag] of html.matchAll(/<(?:script|link|img|source)\b[^>]*>/gi)) {
    const match = /\b(?:src|href)\s*=\s*["']([^"']+)["']/i.exec(tag);
    if (match) checkReference(match[1], page);
  }
}
for (const asset of ['sw.js', 'manifest.json', 'style.css', 'app.js']) {
  checkReference(`/${asset}`, 'index.html');
}
const manifest = JSON.parse(readFileSync(resolve(dist, 'manifest.json'), 'utf8'));
for (const icon of manifest.icons || []) checkReference(icon.src, 'manifest.json');
const syntaxErrors = [];
for (const script of scripts) {
  const result = spawnSync(process.execPath, ['--check', script], { encoding: 'utf8' });
  if (result.status !== 0) syntaxErrors.push({ script, error: result.stderr || String(result.error) });
}
console.log(JSON.stringify({ buildSeconds: +seconds.toFixed(3), budgetSeconds: 15, checked, missing, scriptsChecked: scripts.size, syntaxErrors }, null, 2));
if (missing.length || syntaxErrors.length || seconds > 15) process.exit(1);
