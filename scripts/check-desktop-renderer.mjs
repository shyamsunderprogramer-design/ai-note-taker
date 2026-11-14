// Validate the exact local files copied into the desktop package.
import {spawnSync} from 'node:child_process';
import {existsSync, readFileSync, readdirSync, statSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const renderer = resolve(root, 'electron/renderer');
const missing = [], scripts = new Set();
let checked = 0;
for (const page of readdirSync(renderer).filter(name => name.endsWith('.html'))) {
  const html = readFileSync(resolve(renderer, page), 'utf8');
  for (const [tag] of html.matchAll(/<(?:script|link|img|source)\b[^>]*>/gi)) {
    const match = /\b(?:src|href)\s*=\s*["']([^"']+)["']/i.exec(tag);
    if (!match) continue;
    const url = new URL(match[1], `https://ant.invalid/${page}`);
    if (url.origin !== 'https://ant.invalid') continue;
    checked++;
    const path = resolve(renderer, `.${decodeURIComponent(url.pathname)}`);
    if (!path.startsWith(renderer + '/') || !existsSync(path) || !statSync(path).isFile()) missing.push(`${page}: ${match[1]}`);
    else if (path.endsWith('.js')) scripts.add(path);
  }
}
const syntaxErrors = [];
for (const script of scripts) {
  const result = spawnSync(process.execPath, ['--check', script], {encoding:'utf8'});
  if (result.status !== 0) syntaxErrors.push({script, error:result.stderr});
}
const desktop = JSON.parse(readFileSync(resolve(root, 'electron/package.json'), 'utf8'));
const resource = desktop.build.extraResources.find(item=>item.to==='renderer');
if (!resource || resolve(root, 'electron', resource.from) !== renderer) missing.push('desktop renderer packaging source');
console.log(JSON.stringify({checked, missing, scriptsChecked:scripts.size, syntaxErrors}, null, 2));
if (missing.length || syntaxErrors.length) process.exitCode = 1;
