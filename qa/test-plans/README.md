# Manual & Exploratory Test Plans

> **Role tag:** `qa`
> **Owner:** `role-qa`

---

## What goes here

A test plan is a step-by-step checklist that a human follows to verify
a feature works in the wild. It's *not* automated — it's the QA
substitute for the human's eyes on a real install.

Two flavors:

1. **Manual test plan** — for a specific feature. "Open a new Electron
   window, record 5s of audio, check the transcript appears within 2s."
   The plan is a markdown file with steps + expected behavior + how
   to mark pass/fail.
2. **Exploratory test plan** — for an area of the app. "Spend 30
   minutes clicking through the auth flow; document any surprise." The
   plan is a markdown file with the *scope* and the *charter*; the
   tester fills in what they find.

---

## Format

Every test plan has the same header (machine-readable for the
`qa/runner/` script if we ever build one):

```markdown
---
plan: <name>
feature: <short slug of the feature under test>
role: <which role owns the feature; see CODEOWNERS>
last_reviewed: YYYY-MM-DD
estimated_minutes: <integer>
---

# <Plan title>

## Setup
- …

## Steps
1. …
2. …

## Pass criteria
- …

## Fail criteria
- …

## Notes
- …
```

---

## Why separate from automated tests

Some things automated tests *can't* catch:

- Visual glitches (off-by-one pixel, wrong shade of grey, an icon
  that's been clipped)
- Audio quality (does the transcript appear at the right speed? does
  the recording sound clean?)
- Multi-device scenarios (does the app behave correctly when you have
  two windows open, or a desktop and a phone signed in to the same
  account?)
- Onboarding UX (does the first-run experience make sense to a new
  user?)
- Error messages (does the user understand what went wrong, or do
  they see a stack trace?)

The manual plans catch what the automated tests don't.

---

## Adding a new test plan

1. Create a file in this folder named after the feature slug:
   `qa/test-plans/<feature-slug>.md`.
2. Use the format above.
3. The first PR that adds a new feature should also add a test plan
   for it (file the QA role in the PR template).
4. Re-review the plan when the feature changes; bump `last_reviewed`.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
