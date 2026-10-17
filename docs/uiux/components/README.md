# UI Components

> **Role tag:** `uiux`
> **Owner:** `role-uiux`

---

## The 6 React-style class components

The web SPA uses 6 large class components (per the existing pattern
established in `apps/web/js/components/`). Each one gets a deep-dive
here.

| Component | Path | Doc |
|---|---|---|
| `App` | `apps/web/js/app.js` | (TODO) |
| `ChatShell` | `apps/web/js/components/chat-shell.js` | (TODO) |
| `MessageList` | `apps/web/js/components/message-list.js` | (TODO) |
| `InputBar` | `apps/web/js/components/input-bar.js` | (TODO) |
| `Sidebar` | `apps/web/js/components/sidebar.js` | (TODO) |
| `Settings` | `apps/web/js/components/settings.js` | (TODO) |

---

## Per-component doc structure

Each component doc covers:

1. **Purpose** — what user problem it solves
2. **Props / state** — the public surface (state shape, lifecycle)
3. **Render tree** — which sub-components it composes
4. **Events** — what the user can do, what events fire
5. **ARIA** — accessibility contract (roles, labels, keyboard nav)
6. **Test coverage** — links to relevant tests
7. **Known gotchas** — historical bugs or workarounds

---

## When to add a component doc

- You're adding a new class component to `apps/web/js/components/`
- You're significantly reworking an existing component
- You're adding a new ARIA pattern to a component

A simple bugfix or a small change to an existing component does
**not** require a new doc — update the existing one if anything.

---

## Cross-platform components

The mobile app has its own component set in
`mobile/src/components/`. It's React Native, not React, so the
doc-per-component pattern still applies but lives next to the
mobile code, not in this folder.

The Chrome extension popup is small enough that a per-component doc
is overkill; it's documented inline in `apps/ant-chrome-extension/`.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
