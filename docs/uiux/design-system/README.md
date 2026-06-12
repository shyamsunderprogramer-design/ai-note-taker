# Design System

> **Role tag:** `uiux`
> **Owner:** `role-uiux`

---

## What goes here

The design tokens, color palette, typography scale, spacing scale,
and component visual specs. Anything that defines the *look* of the
app, abstracted away from any specific component implementation.

---

## Token categories

| Category | Examples | Source of truth |
|---|---|---|
| Colors | primary, secondary, surface, on-surface, error | `apps/web/css/tokens.css` |
| Typography | font family, scale (display/headline/body/caption), weights | `apps/web/css/typography.css` |
| Spacing | 4/8/12/16/24/32/48 px scale | `apps/web/css/tokens.css` |
| Elevation | shadow levels 0–5 | `apps/web/css/elevation.css` |
| Motion | duration (fast/medium/slow), easing curves | `apps/web/css/motion.css` |
| Radii | sm (4px), md (8px), lg (12px), full (9999px) | `apps/web/css/tokens.css` |

> Web fonts (Inter + JetBrains Mono) are bundled locally under
> `apps/web/fonts/` and inlined via `@font-face` in
> `apps/web/index.html` as a bulletproof fallback. See
> `local-ai-wiring-2026-06-09` memory.

---

## When to add to this folder

- You're introducing a new color or semantic color role
  (e.g., "warning", "success", "info") — add a new token and
  document it here.
- You're adding a new typography size or weight — update the
  scale and document the use case.
- You're standardizing a new spacing or radius value — add it to
  the scale and reference the rationale here.

Do **not** add component-specific styles here. Those go in
[`components/`](components/).

---

## Cross-platform parity

- **Web** consumes tokens via CSS custom properties.
- **Electron** renders the web SPA, so the CSS tokens apply.
- **Mobile** (React Native) uses an analogous token object in
  `mobile/src/theme/tokens.ts` — keep both in sync.
- **Chrome extension** is a popup consuming the same web tokens.

When you change a token, audit the mobile `tokens.ts` for parity.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
