# Repository layout

ANT is an Electron desktop application backed by a local Python service.

| Path | Purpose |
| --- | --- |
| `electron/` | Desktop main process, preload, native helpers and packaging |
| `electron/renderer/` | Bundled interface, pages, overlays and renderer tests |
| `backend/` | FastAPI, transcription, AI providers and local data services |
| `e2e/` | Isolated renderer tests; the HTTP server is test tooling only |
| `qa/performance/renderer/` | Renderer behavior and performance probes |
| `mobile/` | Existing separate mobile project |
| `apps/ant-chrome-extension/` | Existing browser integration project |
| `scripts/` | Desktop asset checks, Python runtime and release verification |

The browser app build and PWA have been removed. The separate product website in
`apps/landing` provides desktop information and downloads, with its own Vercel build.
Desktop UI files remain HTML/CSS/JavaScript because Electron uses Chromium to render its windows.

Run `npm install`, then `npm run electron:start`. Use `npm test` for desktop and
renderer unit tests, `npm run renderer:check` for packaged assets, and
`npm run build` to check and package the desktop application.
