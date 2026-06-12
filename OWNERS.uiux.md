# UI/UX Dev Role — Charter

> **Role tag:** `uiux`
> **GitHub team:** `role-uiux` (1 member today: `@shyamsunderprogramer-design`)
> **Charter owner:** This file is the canonical answer to "what does UI/UX dev own?"

---

## What this role owns

Everything the user sees and touches. File-level inventory, in priority order:

### Web SPA (the Vite app)
- `apps/web/` — all HTML, JS, CSS, assets, manifest, sw.js
  - `apps/web/index.html` (14 entries)
  - `apps/web/app.js` (co-owned with `backend` — UI/UX owns, backend approves API contract)
  - `apps/web/js/core/api.js` (co-owned with `backend` — same)
  - `apps/web/js/core/{auth-helper,config,state,events,window-controls}.js`
  - `apps/web/js/components/{CognitiveGraph,DocumentUpload,ExportImport,IntegrationPanel,SettingsPanel,Shell}.js`
  - `apps/web/css/` (modular refactor; live build target is `apps/web/style.css`)
  - `apps/web/assets/`

### Landing page
- `apps/landing/` — the marketing / hero / download page

### Chrome extension (MV3)
- `apps/ant-chrome-extension/` — all files; the extension is a UI surface
  - `manifest.json`, `background.js`, `popup.html`, `popup.js`, content scripts

### Electron UI side
- `electron/features/` — overlay-adapter.js, screen-recorder.js
- `electron/assets/` — design assets (icons, splash video) — *not* build config
  (the build config under `electron/build/` and `electron/scripts/` is devops)

### Design source files
- `assets/design/` — design source files (PNG, SVG, source assets)

### Mobile
- `mobile/src/screens/`
- `mobile/src/components/`
- `mobile/src/store/`
- `mobile/App.js`, `mobile/index.js`, `mobile/app.json`
- `mobile/package.json` (mobile-dep bumps; workspace plumbing is devops)

---

## What this role reads but doesn't own

| Area | Owner | Why UI/UX dev cares |
|---|---|---|
| `backend/routes/` | backend | UI/UX consumes these APIs; needs the contract |
| `docs/backend/api/API_REFERENCE.md` | backend | UI/UX reads the spec before writing the client |
| `e2e/tests/` | qa + uiux | e2e tests assert UI behavior; UI/UX approves visual assertions |
| `electron/main.js` / `preload.js` / `stealth.js` | devops + backend | UI/UX consumes the IPC bridge defined here |
| `.env.example` | devops | UI/UX doesn't read .env directly (uses `window.API_BASE`) |
| `mobile/__tests__/` | qa + uiux | mobile tests are qa-owned; UI/UX approves the screen behavior tests |

---

## What this role delivers

Typical PR outputs from a UI/UX dev:

- New HTML page in `apps/web/`
- New JS component in `apps/web/js/components/`
- New CSS module in `apps/web/css/components/`
- New mobile screen in `mobile/src/screens/`
- New mobile component in `mobile/src/components/`
- New Chrome extension content script or popup
- Electron renderer-side feature in `electron/features/`
- Vite config tweak in `apps/web/vite.config.js` (adding a new entry)
- New design asset in `assets/design/`
- Visual change: screenshot + recording attached to the PR
- For new HTML pages: a `vercel.json` rewrite entry (added in the same PR; devops reviews)

---

## What this role's AI agent has access to

> **Status:** the role-scoped AI agent is a planning stub, not yet wired up.
> See `agents/uiux/AGENTS.md` for the scoping plan.

When the agent is online, it will be able to:

- **Read:** every file in `apps/`, `electron/features/`, `electron/assets/`,
  `assets/design/`, `mobile/src/`
- **Write:** files in those same paths + `mobile/{App.js,index.js,app.json}`
- **Bash:** npm scripts scoped to the relevant workspace
  (`npm run web:dev`, `npm run mobile:start`, `npm run electron:dev`)
- **Memory:** `agents/uiux/MEMORY.md`

It will **not** have access to:
- The backend (`backend/`)
- The Electron runtime shell (`electron/main.js`, `preload.js`, `stealth.js`)
- Production secrets, real user data

---

## What this role reviews when it gets a PR

When CODEOWNERS routes a PR to `role-uiux`, this role checks:

1. **Vite build passes** — `cd apps/web && npx vite build` produces `apps/web/dist/`
2. **Visual change has a screenshot/recording** — attached in the PR body
3. **New HTML page got a `vercel.json` rewrite** — and the devops reviewer is tagged
4. **Mobile build passes** — `cd mobile && npm test` passes
5. **No `nodeIntegration` or `contextIsolation` disabled** in Electron renderer
6. **CSP unchanged** (or explicitly justified) — no new `unsafe-inline` or `unsafe-eval`
7. **API contract calls match the backend** — for any change to `app.js` or `js/core/api.js`,
   `role-backend` is also tagged

---

## How to contact this role

- **Today:** `@shyamsunderprogramer-design` (sole human member of `role-uiux`)
- **When collaborators join:** tag the `role-uiux` GitHub Team in the PR

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
