/** Local static preview of the Vercel website routes; no backend or credentials. */
import { createServer } from "node:http";
import { readFile, open } from "node:fs/promises";
import { constants } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, extname, sep } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const output = resolve(root, "apps/web/dist");
const config = JSON.parse(await readFile(resolve(root, "vercel.json"), "utf8"));
const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".woff2": "font/woff2",
  ".txt": "text/plain",
  ".xml": "application/xml",
};
const port = Number(process.env.PORT || 4178);
const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url, "http://127.0.0.1");
    let pathname = decodeURIComponent(url.pathname);
    if (!["GET", "HEAD"].includes(request.method)) {
      response.writeHead(405).end();
      return;
    }
    const redirect = config.redirects?.find((rule) => rule.source === pathname);
    if (redirect) {
      response.writeHead(redirect.permanent ? 308 : 307, { Location: redirect.destination + url.search }).end();
      return;
    }
    if (pathname !== "/" && pathname.endsWith("/")) {
      response.writeHead(308, { Location: pathname.replace(/\/+$/, "") + url.search }).end();
      return;
    }
    pathname = config.rewrites.find((rule) => rule.source === pathname)?.destination || pathname;
    const path = resolve(output, "." + pathname);
    if (!path.startsWith(output + sep)) {
      response.writeHead(404).end("Not found");
      return;
    }
    // Inspect and read the same open file so a concurrent rebuild cannot
    // substitute a different file between a path-based stat and read.
    const file = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
    let body;
    try {
      if (!(await file.stat()).isFile()) {
        response.writeHead(404).end("Not found");
        return;
      }
      if (request.method !== "HEAD") body = await file.readFile();
    } finally {
      await file.close();
    }
    const headers = Object.fromEntries(
      config.headers
        .find((rule) => rule.source === "/(.*)")
        .headers.map((header) => [header.key, header.value]),
    );
    response.writeHead(200, {
      ...headers,
      "Content-Type": mime[extname(path)] || "application/octet-stream",
      "Cache-Control": "no-cache",
    });
    response.end(body);
  } catch (error) {
    response.writeHead(error instanceof URIError ? 400 : 404).end("Not found");
  }
});
server.listen(port, "127.0.0.1", () =>
  console.log(`ANT product website: http://127.0.0.1:${port}`),
);
