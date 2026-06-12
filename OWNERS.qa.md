# QA Role — Charter

> **Role tag:** `qa`
> **GitHub team:** `role-qa` (1 member today: `@shyamsunderprogramer-design`)
> **Charter owner:** This file is the canonical answer to "what does QA own?"

---

## What this role owns

Testing, test strategy, test environment, and test infrastructure. File-level
inventory, in priority order:

### Test code (the tests themselves)
- `e2e/` — Playwright e2e tests (workspace `ant-e2e-tests`)
  - `e2e/tests/` — 10 spec files
- `qa/` — NEW top-level folder for test plans, fixtures, performance
  - `qa/README.md` — test-environment manifest
  - `qa/test-plans/` — manual + exploratory test plans
  - `qa/fixtures/` — test data, seed scripts
  - `qa/performance/` — k6 scripts, perf budgets
- `backend/tests/` — pytest suite
  - `backend/tests/conftest.py` — co-owned with `backend` (qa owns the
    auth_headers / client fixtures; backend approves the test bootstrap)
- `mobile/__tests__/` — Jest tests (co-owned with `uiux`)
- `electron/tests/` — node:test smoke tests (co-owned with `devops`)

### Test strategy docs
- `docs/qa/test-strategy.md` — what's covered, what's not, the test pyramid
- `docs/qa/test-environment.md` — how to set up the test DB, mocks, etc.
- `docs/qa/DIY_TEST_GUIDE.md` — moved from `docs/development/DIY_TEST_GUIDE.md`
- `docs/qa/troubleshooting.md` — debugging test failures

### Test-runner config
- `backend/pytest.ini` — pytest config (asyncio_mode=auto, etc.)
- `e2e/playwright.config.js` — Playwright config

---

## What this role reads but doesn't own

| Area | Owner | Why QA cares |
|---|---|---|
| `backend/routes/` | backend | QA writes tests against these endpoints; backend owns the implementation |
| `apps/web/app.js` | uiux + backend | e2e specs exercise this; UI/UX approves visual behavior assertions |
| `mobile/src/screens/` | uiux | mobile tests assert screen behavior; UI/UX approves the screen-level expectations |
| `electron/main.js` | devops | electron tests may need to spawn the binary; devops owns the build-time test infra |
| `docs/devops/development/TROUBLESHOOTING.md` | devops | the "Testing / CI failure" sections are co-owned with QA |
| `backend/security/` | devsecops + backend | QA may write security regression tests; devsecops reviews |

---

## What this role delivers

Typical PR outputs from QA:

- New test file in `backend/tests/test_<module>.py`
- New e2e spec in `e2e/tests/<feature>.spec.js`
- New mobile test in `mobile/__tests__/<feature>.test.js`
- New electron test in `electron/tests/<module>.test.js`
- New fixture in `qa/fixtures/`
- New test plan in `qa/test-plans/`
- New performance budget script in `qa/performance/`
- Update to `docs/qa/test-strategy.md` for new coverage
- DOCUMENTED BUG regression test (with a docstring explaining the bug)

---

## What this role's AI agent has access to

> **Status:** the role-scoped AI agent is a planning stub, not yet wired up.
> See `agents/qa/AGENTS.md` for the scoping plan.

When the agent is online, it will be able to:

- **Read:** every test file + every file under test (qa needs to know both)
- **Write:** files in `e2e/`, `qa/`, `backend/tests/`, `mobile/__tests__/`,
  `electron/tests/`
- **Bash:** pytest, playwright, jest, node:test, k6 (scoped to test runners only)
- **Memory:** `agents/qa/MEMORY.md`

It will **not** have access to:
- Production data
- Real user credentials (only `qa/fixtures/` synthetic data)
- Real API keys (only `qa/fixtures/` placeholders)
- Direct deploys (CI runs the tests; the agent does not push to prod)

---

## What this role reviews when it gets a PR

When CODEOWNERS routes a PR to `role-qa`, this role checks:

1. **New behavior has a test** — `backend/tests/`, `e2e/tests/`, etc.
2. **DOCUMENTED BUG tests are documented** — the test docstring names the bug
3. **No flaky test introduced** — re-run the new test 3x to confirm
4. **Test fixtures are synthetic** — no real user data, no real API keys
5. **E2E covers the new user flow** — for user-facing changes
6. **Performance regression is within budget** — for backend / mobile / desktop
7. **The PR doesn't disable an existing test** — and if it does, the test is
   moved to DOCUMENTED BUG with a follow-up issue

---

## How to contact this role

- **Today:** `@shyamsunderprogramer-design` (sole human member of `role-qa`)
- **When collaborators join:** tag the `role-qa` GitHub Team in the PR

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
