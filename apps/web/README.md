# ANT Web App (`apps/web/`)

The web front-end for ANT (AI Note Taker), deployed to Vercel and embedded in the Electron desktop app.

## Quick start

```bash
# Install Vite (one-time, from the repo root)
npm install

# Local dev server with hot-reload (http://localhost:5173)
# The dev server proxies /api, /health, /docs, /openapi.json
# to the FastAPI backend on http://localhost:8000.
npm run dev

# Production build → apps/web/dist/
npm run build

# Preview the production build (http://localhost:4173)
npm run preview
```

> **Note:** The dev server assumes the FastAPI backend is running on port 8000.
> Start it from `backend/`: `python3 start_server.py` (or `make dev` from the root).

## Page → file map

The web app is a **static multi-page application** (not a true SPA) —
each page is a self-contained `.html` file at the root of this folder
with a sibling `.js` when the page needs JavaScript. The clean URLs
in column 1 are served via rewrites in the root `vercel.json`.

| URL (clean)             | File                              | Has JS?                          |
|-------------------------|-----------------------------------|----------------------------------|
| `/`                     | `index.html`                      | yes (`app.js`)                   |
| `/analytics-dashboard`  | `analytics-dashboard.html`        | yes (`analytics-dashboard.js`)   |
| `/caption-overlay`      | `caption-overlay.html`            | no (browser-rendered)            |
| `/cognitive-graph`      | `cognitive-graph.html`            | yes (`js/cognitive-graph.js`)    |
| `/interview-overlay`    | `interview-overlay.html`          | no                               |
| `/interview-simulator`  | `interview-simulator.html`        | yes (`interview-simulator.js`)   |
| `/job-tracker`          | `job-tracker.html`                | yes (`job-tracker.js`)           |
| `/overlay`              | `overlay.html`                    | no                               |
| `/pre-interview`        | `pre-interview.html`              | yes (`pre-interview.js`)         |
| `/resume-review`        | `resume-review.html`              | yes (`resume-review.js`)         |
| `/resume-review-v2`     | `resume-review-v2.html`           | yes (`resume-review-v2.js`)      |
| `/signin`               | `signin.html`                     | no (form posts to backend)       |
| `/splash`               | `splash.html`                     | no (static splash)               |
| `/study-plan`           | `study-plan.html`                 | yes (`study-plan.js`)            |

PWA icons (`icon-72x72.png` through `icon-512x512.png`) are
regenerated from `assets/design/source/Ant_App_icon.png` at the
repo root via `make pwa-icons`.

## Source layout

```
apps/web/
├── index.html                # Main entry (chat / overlay shell)
├── app.js                    # Monolithic dev source (9200+ lines)
├── style.css                 # Single stylesheet (8200+ lines)
├── manifest.json             # PWA manifest
├── sw.js                     # Service worker
├── caption-overlay.html      # Multi-page entry
├── cognitive-graph.html      # Multi-page entry
├── interview-overlay.html    # Multi-page entry
├── interview-simulator.html  # Multi-page entry
├── job-tracker.html          # Multi-page entry
├── overlay.html              # Multi-page entry
├── pre-interview.html        # Multi-page entry
├── resume-review.html        # Multi-page entry
├── resume-review-v2.html     # Multi-page entry
├── signin.html               # Multi-page entry
├── splash.html               # Multi-page entry
├── study-plan.html           # Multi-page entry
├── analytics-dashboard.html  # Multi-page entry
├── js/                       # Modular refactor (NOT YET WIRED UP — see below)
│   ├── main.js
│   ├── cognitive-graph.js
│   ├── core/                 # state, events, config, api, auth-helper, window-controls
│   └── components/           # Shell, SettingsPanel, CognitiveGraph, etc.
├── css/                      # Modular refactor (NOT YET WIRED UP)
│   ├── main.css
│   ├── base/
│   └── components/
├── assets/                   # Icons, splash, banner, etc.
│   └── icons/                # ant-icon-{32,192}.png, ant-icon.svg, ant-splash.png
├── dist/                     # Vite build output (gitignored)
├── node_modules/             # Vite install (gitignored)
├── package.json              # Vite config
├── package-lock.json         # npm lockfile
└── vite.config.js            # Vite config (multi-page entry, API proxy)
```

## Modular refactor (work in progress)

The `js/` and `css/` sub-folders hold a modular ES-module version of the front-end:

- `js/main.js` (entry) imports from `./core/state.js`, `./components/Shell.js`, etc.
- `css/main.css` is the corresponding single-file stylesheet
- `js/core/` holds the framework primitives (state, events, config, API client, auth helper, window controls)
- `js/components/` holds the UI components (Shell, SettingsPanel, CognitiveGraph, etc.)
- `css/base/` and `css/components/` hold the corresponding styles

This refactor is **not yet wired up to `index.html`** — that file still references the monolithic `app.js` and `style.css`. Migrating the live source to the modular tree is a separate refactor (estimated 1-2 days of work plus testing). The dist/ build output will look very different once that migration is done because Vite will be able to tree-shake the modular code.

## Build pipeline

1. `npm install` reads `package.json` and installs `vite ^6.0.0` (and its transitive deps) into `node_modules/`.
2. `npm run dev` starts the Vite dev server on port 5173 with API proxy to the backend.
3. `npm run build` runs `vite build`, which:
   - Reads `vite.config.js`'s `rollupOptions.input` for the list of HTML entries
   - Bundles each entry's referenced JS/CSS, hashes asset filenames for cache-busting
   - Emits hashed assets to `dist/assets/`
   - Copies each HTML entry to `dist/` with the hashed asset names inlined
4. `vercel.json` at the repo root sets `outputDirectory: "apps/web"`, so Vercel serves `apps/web/` (the dev source) as-is for preview deploys, and `apps/web/dist/` (the Vite build) for production.

## Deployment

- **Vercel:** `vercel.json` declares `outputDirectory: "apps/web"`. Vercel runs `npm run build` automatically (via the `buildCommand` in the Vercel project settings; this is not in `vercel.json` because Vercel detects Vite from `package.json`).
- **Electron desktop:** `electron/package.json`'s `build.extraResources` copies `apps/web/` into the packaged app, and `main.js` loads `apps/web/index.html` as the renderer.

## Service worker

`sw.js` is registered in the browser PWA flow (skipped in Electron where `file://` protocol is used). It caches the shell and core assets for offline use.
