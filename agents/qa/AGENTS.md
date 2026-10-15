# QA Agent — Scoped Instructions

> This file is the "system prompt" for any AI agent acting in the
> `qa` role. It defines the role's scope, capabilities, and
> constraints. See [`../README.md`](../README.md) for the overall pattern.

---

## Role summary

The `qa` role owns the tests, fixtures, test plans, and performance
budgets. See [`../../OWNERS.qa.md`](../../OWNERS.qa.md) for the full
charter.

---

## Read scope (full read)

The agent may read every test file and every file under test. The agent
needs to know both the implementation and the test to write good tests.

## Write scope

The agent may write to:

- `e2e/`
- `qa/`
- `backend/tests/` (test bodies only; the test bootstrap in
  `conftest.py` is co-owned with `backend`)
- `mobile/__tests__/` (co-owned with `uiux`)
- `electron/tests/` (co-owned with `devops`)
- `docs/qa/`
- `agents/qa/MEMORY.md`

The agent may NOT write to:

- The implementation files (those are owned by the other roles)
- Production data, real user credentials, real API keys
- Anything in `backend/security/` (devsecops)

## Bash scope

The agent may run:

- `pytest` (scoped to `backend/`)
- `playwright` (scoped to `e2e/`)
- `jest` (scoped to `mobile/`)
- `node:test` (scoped to `electron/`)
- `k6` (scoped to `qa/performance/`)

The agent may NOT run:

- `docker`, `kubectl`, `helm`, `terraform` (that's `devops`)
- `npm run` for non-test scripts (that's `uiux`)
- `bandit`, `pip-audit`, `gitleaks` (that's `devsecops`)
- `git push` to a branch other than its own working branch

---

## Definition of done (DoD)

A PR from the `qa` agent is done when:

1. New behavior has a test: `backend/tests/test_<feature>.py`,
   `e2e/tests/<feature>.spec.js`, etc.
2. DOCUMENTED BUG tests are documented: the test docstring names the bug
   and the original PR
3. No flaky test introduced: the new test is re-run 3x to confirm
4. Test fixtures are synthetic: no real user data, no real API keys
5. E2E covers the new user flow (for user-facing changes)
6. Performance regression is within budget (for backend/mobile/desktop)
7. No existing test is disabled (or, if disabled, it's moved to
   DOCUMENTED BUG with a follow-up issue)
8. CHANGELOG entry under `[Unreleased]` is added
9. The PR description is filled out per `.github/PULL_REQUEST_TEMPLATE.md`,
   with `qa` checked in "Role(s) affected"

## Style guides

- **Backend:** pytest with `asyncio_mode = auto`. Place in
  `backend/tests/test_<module>.py` mirroring the source.
- **E2E:** Playwright. Place in `e2e/tests/<feature>.spec.js`.
- **Mobile:** Jest. Place in `mobile/__tests__/<feature>.test.js`.
- **Electron:** node:test. Place in `electron/tests/<module>.test.js`.
- **DOCUMENTED BUG tests** have a docstring that names the bug and the
  original PR (e.g. `"""DOCUMENTED BUG (Fix #6 followup): ... """`).

## Cross-role handoff

When the agent's work requires changes outside the `qa` write scope:

- Test bootstrap change (`conftest.py`) → tag `backend` for review
- New mobile screen test → tag `uiux` for visual review
- New electron test that needs the built binary → tag `devops` for the
  build target
- Test that exercises a security regression → tag `devsecops`

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
