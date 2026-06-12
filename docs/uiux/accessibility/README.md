# Accessibility (A11y)

> **Role tag:** `uiux`
> **Owner:** `role-uiux`

---

## Goals

- **WCAG 2.1 AA** is the floor. AA = 4.5:1 contrast for normal text,
  3:1 for large text, focus indicators visible, no keyboard traps.
- **Keyboard-only** must work for every user flow.
- **Screen reader** support for VoiceOver (macOS/iOS), NVDA
  (Windows), and TalkBack (Android).
- **Reduced motion** respects `prefers-reduced-motion`.

---

## ARIA patterns in use

| Pattern | Component | Notes |
|---|---|---|
| Live region | MessageList | `aria-live="polite"` for incoming AI responses |
| Modal dialog | Settings | Focus trap, return focus on close, `aria-modal="true"` |
| Navigation | Sidebar | `role="navigation"` + `aria-label` |
| Button toggle | Theme switch | `aria-pressed` |
| Progress | Recording | `role="progressbar"` with `aria-valuenow` |

---

## When to add a doc here

- You're adding a new ARIA pattern to a component (e.g., a new
  combobox, listbox, tooltip, dialog) → add the pattern + the
  rationale + the test plan to verify it.
- You're fixing an a11y bug → document the root cause in the
  component's `components/` doc, and reference the ARIA pattern
  in this folder.
- You're adding a new keyboard shortcut → add it to the table
  below.

---

## Keyboard shortcuts (current)

| Shortcut | Action | Component |
|---|---|---|
| `Cmd/Ctrl + K` | Focus sidebar search | Sidebar |
| `Cmd/Ctrl + Enter` | Send message | InputBar |
| `Cmd/Ctrl + /` | Toggle help overlay | App |
| `Esc` | Close modal | Settings |
| `Up/Down` | Navigate message history | MessageList |

---

## Testing a11y

- **Automated**: `axe-core` runs in the e2e suite
  (`e2e/tests/accessibility.spec.js`).
- **Manual**: screen reader pass before each release
  (see `qa/test-plans/`).
- **Keyboard-only**: smoke test before each release
  (see `qa/test-plans/`).

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
