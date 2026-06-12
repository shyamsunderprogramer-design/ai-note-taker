# UI/UX Dev Docs

> **Role tag:** `uiux`
> **Charter:** [`OWNERS.uiux.md`](../../OWNERS.uiux.md)
> **CODEOWNERS routing:** `.github/CODEOWNERS` lines starting with
> `/apps/`, `/mobile/`, `/electron/features/`, `/assets/design/` map
> to the `role-uiux` GitHub Team.

This is the docs home for everything `uiux` dev owns. The web SPA,
the mobile app, the Chrome extension, the Electron renderer-side
features, and the design source files.

---

## What's in this folder

| Subfolder | What's there |
|---|---|
| [design-system/](design-system/) | Design tokens, color palette, typography, spacing, components |
| [components/](components/) | Per-component docs (the 6 React-style class components) |
| [accessibility/](accessibility/) | A11y guidelines, ARIA patterns, screen-reader notes |

---

## Where the actual code lives

The code is in:

- `apps/web/` (Vite SPA)
- `apps/landing/` (landing page)
- `apps/ant-chrome-extension/` (MV3 Chrome extension)
- `electron/features/` (Electron renderer-side features)
- `electron/assets/` (Electron design assets)
- `assets/design/` (design source files — PNG, SVG)
- `mobile/src/` (React Native)
- `mobile/{App.js,index.js,app.json}` (RN entry points)

This folder is *only* the docs home. The code itself is not in `docs/`.

---

## When to add a doc here

Add a doc here when:

- You're adding a new web component → add to `components/`
- You're adding a new design token → update `design-system/`
- You're adding a new HTML page → update the web app README
  (the page itself is auto-routed by Vite, not this folder)
- You're adding a new mobile screen → update the mobile README
- You're changing the color palette / typography → update
  `design-system/`
- You're adding a new ARIA pattern → update `accessibility/`

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
