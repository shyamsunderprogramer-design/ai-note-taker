/** Build the public desktop product site without packaging or exposing the app. */
import { copyFile, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const source = resolve(root, 'apps/landing');
const output = resolve(source, 'dist');
const { version, updated } = JSON.parse(await readFile(resolve(source, 'release.json'), 'utf8'));
if (!/^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/.test(version)) throw new Error('Invalid published release version');
if (!/^\d{4}-\d{2}-\d{2}$/.test(updated)) throw new Error('Invalid review date');
let commit = process.env.VERCEL_GIT_COMMIT_SHA;
if (!commit) {
  try { commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(); }
  catch { commit = 'local'; }
}
if (!/^(?:[a-f0-9]{40}|local)$/.test(commit)) throw new Error('Invalid source commit');
const releaseBase = `https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v${version}`;
const html = (await readFile(resolve(source, 'index.html'), 'utf8'))
  .replaceAll('{{VERSION}}', version).replaceAll('{{RELEASE_BASE}}', releaseBase)
  .replaceAll('{{UPDATED}}', updated).replaceAll('{{SOURCE_COMMIT}}', commit);
if (/\{\{[^}]+\}\}/.test(html)) throw new Error('Unresolved website template');
// Only this generated output is replaced. Use an explicit allowlist of public assets.
await rm(output, { recursive: true, force: true });
for (const directory of ['site/assets', 'assets/fonts', 'css/base']) {
  await mkdir(resolve(output, directory), { recursive: true });
}
await writeFile(resolve(output, 'index.html'), html);
for (const file of ['style.css', 'tokens.css', 'site.js', 'assets/ant-mark.png',
  'assets/ant-mark-light.png', 'assets/ant-queen-640.webp', 'assets/ant-queen-1280.webp',
  'assets/ant-knowledge-640.webp', 'assets/ant-knowledge-1280.webp', 'assets/social-preview.png']) {
  await copyFile(resolve(source, file), resolve(output, 'site', file));
}
for (const file of ['assets/fonts/Inter-Latin.woff2', 'assets/fonts/JetBrainsMono-Latin.woff2', 'css/base/variables.css']) {
  await copyFile(resolve(root, 'electron/renderer', file), resolve(output, file));
}
await copyFile(resolve(source, 'retire-sw.js'), resolve(output, 'sw.js'));
await writeFile(resolve(output, 'robots.txt'), 'User-agent: *\nAllow: /\nSitemap: https://ai-note-taker-five.vercel.app/sitemap.xml\n');
await writeFile(resolve(output, 'sitemap.xml'), '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://ai-note-taker-five.vercel.app/</loc><lastmod>' + updated + '</lastmod></url></urlset>\n');
console.log(`ANT marketing site built: ${output}; published downloads v${version}; source ${commit}.`);
