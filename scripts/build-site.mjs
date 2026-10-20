/** Compose the public website without changing the desktop renderer build. */
import { access, copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const source = resolve(root, "apps/landing");
const output = resolve(root, "apps/web/dist");
const entry = resolve(output, "index.html");
const appEntry = resolve(output, "browser-app.html");
const originalEntry = await readFile(entry, "utf8");
// Vercel serves existing files before applying rewrites. Make the marketing
// page the real index and preserve the built application under its own name.
// Re-running this composer must never replace the app with the marketing page.
if (originalEntry.includes("data-ant-product-site")) await access(appEntry);
else await writeFile(appEntry, originalEntry);
const { version } = JSON.parse(await readFile(resolve(root, "electron/package.json"), "utf8"));
if (!/^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/.test(version))
  throw new Error("Invalid desktop release version");
const releaseBase = `https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v${version}`;
const html = (await readFile(resolve(source, "index.html"), "utf8"))
  .replaceAll("{{VERSION}}", version)
  .replaceAll("{{RELEASE_BASE}}", releaseBase);
if (/\{\{[^}]+\}\}/.test(html)) throw new Error("Unresolved website template value");
await mkdir(resolve(output, "site/assets"), { recursive: true });
await writeFile(entry, html);
await writeFile(resolve(output, "product.html"), html);
for (const file of [
  "style.css",
  "tokens.css",
  "site.js",
  "assets/logo.svg",
  "assets/social-preview.png",
]) {
  await copyFile(resolve(source, file), resolve(output, "site", file));
}
await copyFile(
  resolve(root, "docs/architecture/overview.svg"),
  resolve(output, "site/assets/architecture.svg"),
);

// Newly installed browser PWAs should open the app, not the public homepage.
// Leave the source manifest and Electron/source development behavior untouched.
const manifest = JSON.parse(await readFile(resolve(output, "manifest.json"), "utf8"));
manifest.start_url = "/app";
await writeFile(resolve(output, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
await writeFile(
  resolve(output, "robots.txt"),
  "User-agent: *\nAllow: /\nDisallow: /app\nDisallow: /signin\nSitemap: https://ai-note-taker-five.vercel.app/sitemap.xml\n",
);
await writeFile(
  resolve(output, "sitemap.xml"),
  '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://ai-note-taker-five.vercel.app/</loc></url></urlset>\n',
);
console.log(`ANT website built with v${version} downloads; browser app preserved at /app.`);
