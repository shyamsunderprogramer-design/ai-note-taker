# QA / Testing Docs

> **Role tag:** `qa`
> **Charter:** [`OWNERS.qa.md`](../../OWNERS.qa.md)
> **CODEOWNERS routing:** `.github/CODEOWNERS` lines starting with
> `/e2e/`, `/qa/`, `/backend/tests/`, `/mobile/__tests__/`,
> `/electron/tests/` map to the `role-qa` GitHub Team.

This is the docs home for the QA role. Test strategy, test
environment manifest, troubleshooting test failures, and links
to the actual test code (which lives next to its code, not here).

---

## What's in this folder

| File | What's there |
|---|---|
| [test-strategy.md](test-strategy.md) | The QA strategy doc — what we test, how, and why |
| [test-environment.md](test-environment.md) | The QA test-environment manifest (Python, Node, Playwright, Ollama versions) |

---

## Where the actual test code lives

Test code stays next to its code (per the role-ownership refactor):

- `backend/tests/` — pytest, qa owns, backend approves test infra
- `e2e/` — Playwright, qa owns, uiux approves visual behavior
- `mobile/__tests__/` — Jest, qa owns, uiux approves screen tests
- `electron/tests/` — node:test, qa owns, devops approves build-time
  test infra

This folder (`docs/qa/`) is **not** for test code. It's for test
*strategy* and *environment* docs.

---

## Related folders

- [`qa/`](../../qa/) — test-environment artifacts (test plans,
  fixtures, performance scripts). Owned by `role-qa`.
- [`docs/TROUBLESHOOTING.md`](../devops/development/TROUBLESHOOTING.md) —
  co-owned with devops. QA owns the testing/CI-failure sections;
  devops owns the runtime / build / deploy sections.

---

## When to add a doc here

Add a doc here when:

- You're defining a new test category (e.g., load tests, fuzz
  tests) → add to `test-strategy.md`
- You're documenting a new test environment tool → add to
  `test-environment.md`
- You're writing a reusable troubleshooting recipe for a
  flaky test → add to `test-environment.md` or
  `docs/devops/development/TROUBLESHOOTING.md` (depending on
  whether the recipe is QA-scoped or runtime-scoped)

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
