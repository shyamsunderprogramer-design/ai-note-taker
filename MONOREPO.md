# ANT Monorepo

This document explains the npm workspaces setup created on 2026-06-05 (Fix #21 of [`docs/AUDIT_2026-06-05_Project_Audit.md`](docs/AUDIT_2026-06-05_Project_Audit.md)).

## Layout

```
/
├── package.json              ← root workspace manifest
├── apps/
│   ├── web/                  ← workspace: ant-web (Vite, deployed to Vercel)
│   ├── landing/              ← the landing page (served from apps/web/ on Vercel)
│   └── ant-chrome-extension/ ← workspace: ant-chrome-extension (MV3, no build)
├── electron/                 ← workspace: ai-note-taker (Electron desktop)
├── mobile/                   ← workspace: ant-mobile (React Native)
└── e2e/                      ← workspace: ant-e2e-tests (Playwright)
```

The Python backend (`backend/`) is **not** an npm workspace — Python uses `requirements.txt` and virtualenvs. Use `pip install -r backend/requirements.txt` to install backend deps.

The `apps/*` glob in the root `package.json` will pick up any future apps (e.g. `apps/cli`, `apps/admin`, `apps/ant-firefox-extension`) without needing to edit the workspaces array.

## Why workspaces

- **One `npm install`** at the repo root installs every JS dep across all four workspaces
- **Deduplication** of shared packages (e.g. `eslint` is used by both `mobile` and `e2e`, and is hoisted to the root)
- **Cross-workspace scripts** — `npm run web:build` runs `vite build` in `apps/web/` from anywhere
- **Symlinked workspace deps** — when one workspace needs to import another (currently none do, but it's now possible), npm workspaces handle the linking

## Quick start

```bash
# 1. Install all JS deps for every workspace
npm install

# 2. Pick a workspace to work on
npm run web:dev                  # Vite dev server for apps/web
npm run electron:dev             # Electron desktop app
npm run mobile:start             # React Native Metro bundler
npm run e2e:install:browsers     # One-time Playwright browser download
npm run e2e:test                 # Run Playwright e2e tests
```

## Cross-workspace commands

The root `package.json` exposes proxy scripts for each workspace. Each one runs `npm --workspace <name> <command>`, so you can stay at the repo root:

| Root command | What it does |
|---|---|
| `npm run web:dev` | Vite dev server on :5173 with API proxy to backend :8000 |
| `npm run web:build` | Build the web app to `apps/web/dist/` |
| `npm run web:preview` | Preview the production build on :4173 |
| `npm run electron:start` | Launch the Electron app |
| `npm run electron:dev` | Launch Electron in dev mode |
| `npm run electron:build` | Build the Electron app for the current platform |
| `npm run electron:build:win` | Build a Windows .exe |
| `npm run electron:build:mac` | Build a macOS .dmg |
| `npm run electron:build:linux` | Build a Linux AppImage |
| `npm run electron:icons` | Regenerate platform icons from the source PNG |
| `npm run mobile:start` | Start the React Native Metro bundler |
| `npm run mobile:android` | Build + run on Android emulator/device |
| `npm run mobile:ios` | Build + run on iOS simulator/device |
| `npm run mobile:test` | Run Jest tests for the mobile app |
| `npm run mobile:lint` | Lint the mobile app |
| `npm run e2e:test` | Run Playwright e2e tests headlessly |
| `npm run e2e:test:ui` | Run Playwright with the UI |
| `npm run e2e:install:browsers` | Download Chromium/Firefox/WebKit for Playwright |
| `npm run lint` | Lint the mobile app (web/e2e don't have a lint script) |
| `npm run test` | Run e2e tests (alias of `e2e:test`) |
| `npm run build` | Build web + Electron (mobile and e2e have no build) |

## Adding a new workspace

1. Create the folder and its `package.json` with a unique `name` and `"private": true`.
2. Add the folder path to the `workspaces` array in the root `package.json`. If the folder is under `apps/`, you can rely on the existing `apps/*` glob.
3. Add proxy scripts in the root `package.json`'s `scripts` block.
4. Run `npm install` at the root to link the new workspace.

## Workspace package names

| Folder | `name` field in `package.json` |
|---|---|
| `apps/web/` | `ant-web` |
| `apps/ant-chrome-extension/` | `ant-chrome-extension` |
| `electron/` | `ai-note-taker` |
| `mobile/` | `ant-mobile` |
| `e2e/` | `ant-e2e-tests` |

The `electron` workspace's name is `ai-note-taker` (not `ant-electron`) because that's the name that was already in `electron/package.json` from before the monorepo migration. Changing it would break the GitHub repo reference in `electron-builder` config (`build.publish.repo`) and the `homepage` URL. The mismatch is intentional.

The `ant-chrome-extension` workspace is a vanilla-JS MV3 Chrome extension (no build step, no bundler). It does not use `npm` for anything beyond `npm run package` (which produces a zip for the Chrome Web Store). The workspace is registered so it gets included in `npm install` cleanup and shows up in `ls apps/`.

## Private flag

All five workspace `package.json` files have `"private": true` set. npm workspaces require this — if any workspace is missing the flag, `npm install` will refuse to install until it's added.

## Migration from a non-monorepo setup

Before 2026-06-05, each workspace had its own `package.json` and was installed independently (or via the now-deleted, stale root `package-lock.json` which referenced a `packages/design-system` folder that never existed). The `npm install` at the repo root will now:

1. Read the root `package.json`
2. Walk the `workspaces` array
3. Install each workspace's deps, hoisting shared ones (like `eslint`) to the root `node_modules/`
4. Symlink each workspace into `node_modules/<name>` so cross-workspace imports work
5. Write a fresh `package-lock.json` at the root

The old `package-lock.json` was deleted as part of this migration because it was inconsistent with the new workspaces list.
