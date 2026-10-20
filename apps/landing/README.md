# ANT product website

The public product showcase shares the existing Vercel project with the browser app.

```sh
npm run site:build
npm run site:preview
```

Open `http://127.0.0.1:4178`. `/` is the product website; `/app` is the existing application. The preview serves Vercel's explicit routes and security headers, without starting a backend. Missing files return 404.

`site:build` runs the normal web build, then preserves the compiled app as `browser-app.html` and writes the marketing page to the deployed `index.html` (plus a `product.html` alias). The source renderer and standalone `web:build` output are unchanged. Vercel serves existing files before rewrites, so the public homepage must be the actual index file. Existing app routes, relative links, auth storage and service-worker scope remain valid. A newly installed browser PWA starts at `/app`.

Marketing sources live here. Shared fonts, brand primitives and the architecture SVG are reused from their source locations. Download links use the desktop version from `electron/package.json`; verify the six corresponding assets are published before deploying a new version. The release is currently a testing candidate, and the copy must change when that status changes.

The website has no tracking, backend calls, live recording or sign-in requirement. The examples contain explicitly labeled sample content. See [DESIGN.md](DESIGN.md) for design and QA decisions.

Vercel previews come from pull requests. Merging to `main` updates Production. The optional AWS `CD` workflow is unrelated to this website.

Browser regression check after building: `node qa/website/smoke.cjs` (uses the repository's Playwright Chromium and Firefox installs). CI runs this alongside the existing app tests. [QA notes and screenshots](../../docs/qa/product-website/README.md) record the initial review.
