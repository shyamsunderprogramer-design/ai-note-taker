# vercel.json — Vercel deployment config

This file configures how Vercel builds, serves, and secures the static
web app at `apps/web/`. The FastAPI backend is **not** deployed by
Vercel — it runs on Render (see `render.yaml` at the repo root).

## Build pipeline (Vite, configured in `apps/web/vite.config.js`)
- Vite reads `apps/web/package.json` and runs `vite build`
- `vite.config.js`'s `rollupOptions.input` lists 14 HTML entries
- Vite outputs to `apps/web/dist/` with hashed asset filenames
- Vercel then serves `apps/web/` (Vite overwrites `index.html` in
  place during build, so the dev source IS the served output)

## File structure (this file is JSON, not JSONC)
**`vercel.json` is strict JSON** (no comments, no trailing commas).
Vercel's deployment parser does not officially support JSONC, but
previous versions of this file used `//` comments and worked
incidentally. Phase 6 cleanup (2026-06-08) converted it to strict
JSON and moved all comments to this sidecar file.

## Sections

### `outputDirectory`
- `apps/web` — Vercel serves the source tree directly. Vite's
  `dist/` output is ignored (Vite overwrites the dev source in
  place during build).

### `rewrites`
Vercel serves the 14 static HTML pages directly. The rewrites
route clean URLs (no `.html` suffix) to the corresponding page.
E.g. `/caption-overlay` → `/caption-overlay.html`.

### `headers`

**`X-Frame-Options: DENY`** — don't allow this site to be embedded
in an iframe (clickjacking).

**`X-Content-Type-Options: nosniff`** — don't allow content-type
sniffing.

**`Referrer-Policy: strict-origin-when-cross-origin`** — send only
the origin (not the path) on cross-origin navigations.

**`Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`**
— force HTTPS for one year, including subdomains. Vercel terminates
TLS so this is safe to enable.

**`Permissions-Policy`** — restrict powerful browser features the
app doesn't need. Microphone is allowed for self (the note-taker
records audio).

**`Content-Security-Policy`** — see the dedicated section below.

### `headers.source: /sw.js`
`Cache-Control: public, max-age=0, must-revalidate` and
`Service-Worker-Allowed: /` — the service worker must never be
cached aggressively, otherwise deploys won't pick up new versions
and users will get stuck on stale caches.

### `headers.source: /assets/(.*)`
`Cache-Control: public, max-age=31536000, immutable` — Vite's
hashed assets can be cached forever. **Dormant** until the deployment
switches to serving `dist/` instead of the dev source.

### `trailingSlash: false`
Vercel does not redirect `/foo/` to `/foo`. The static-pages setup
expects exact paths (e.g. `/signin`).

## Content-Security-Policy

The CSP allows:

- `default-src 'self'` — only same-origin by default
- `script-src 'self' 'unsafe-inline' https://api.github.com` — same-origin
  scripts, inline scripts (see migration note), GitHub API for the
  landing-page star count
- `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com` —
  same-origin styles, inline styles (some HTML elements have
  `style="..."` attributes), Google Fonts
- `font-src 'self' https://fonts.gstatic.com data:` — same-origin
  fonts, Google Fonts, embedded fonts
- `img-src 'self' data: blob: https:` — same-origin, data URIs, blob
  URLs, and any HTTPS image
- `media-src 'self' blob: data:` — same-origin, blob, and data URIs
  (for audio capture in the note-taker)
- `connect-src 'self' https://ai-note-taker-7xvn.onrender.com
  wss://ai-note-taker-7xvn.onrender.com https://api.github.com
  http://localhost:* http://127.0.0.1:* ws://localhost:*
  ws://127.0.0.1:*` — backend, WebSocket backend, GitHub API,
  local dev fallbacks
- `frame-ancestors 'none'` — equivalent to `X-Frame-Options: DENY`
- `base-uri 'self'` — don't allow `<base>` tags to point elsewhere
- `form-action 'self'` — forms can only POST to same-origin

### Migration status (Phase 6, 2026-06-08)

- ✅ `unsafe-eval` REMOVED from `script-src` (was a spec leftover for
  a `new Function()` study-plan generator that no longer exists in
  user code).
- ✅ `index.html` migrated — 2 inline scripts extracted to
  `js/inline/platform-class.js` and `js/inline/sw-register.js`.
- ⚠️ `unsafe-inline` still allowed in `script-src` — 5 other HTML
  pages (caption-overlay.html, overlay.html, signin.html,
  splash.html, interview-overlay.html) have large inline
  initialization scripts. Migration plan: extract each to
  `js/inline/<page-name>.js` and replace with `<script src=...>`.
  Tracked as follow-up work.

See `docs/devsecops/security/` for the full CSP hardening log.
