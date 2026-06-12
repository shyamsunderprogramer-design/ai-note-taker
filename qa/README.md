# QA Test Environment

> **Role tag:** `qa`
> **Owner:** `role-qa` (see [OWNERS.qa.md](../../OWNERS.qa.md) for the
> full charter)
> **What lives here:** test plans, fixtures, performance scripts — *not*
> the test code itself (that lives next to the code: `e2e/`,
> `backend/tests/`, `mobile/__tests__/`, `electron/tests/`)

---

## Why this folder exists

Test code stays next to its code (so a `git blame` of a test lands in
the same PR as the code it covers). But there are *test-environment*
artifacts that don't fit next to the code:

- **Manual / exploratory test plans** — checklists a human follows to
  verify a feature works in the wild (e.g., "open a new Electron
  window, record 5s of audio, check the transcript appears").
- **Synthetic fixtures** — sample users, sample recordings, sample
  questions, sample answers. These are *not* test code; they're
  *test data* the test code consumes.
- **Performance budgets** — k6 scripts, perf thresholds, historical
  numbers. Per-feature, not per-file.
- **Test-environment manifests** — which version of Ollama, which
  ffmpeg, which Neo4j, which browsers (for Playwright). When the
  test env changes, this is the doc to update.

This folder is the QA home for all of that.

---

## Folder layout

```
qa/
├── README.md                  # this file
├── test-plans/                # manual + exploratory test plans
│   └── README.md
├── fixtures/                  # test data, seed scripts
│   └── README.md
└── performance/               # k6 scripts, perf budgets
    └── README.md
```

---

## What goes in qa/ vs other places

| Type of artifact | Location |
|---|---|
| Automated test code (pytest, playwright, jest, node:test) | next to the code: `backend/tests/`, `e2e/tests/`, `mobile/__tests__/`, `electron/tests/` |
| Manual test plan for a feature | `qa/test-plans/<feature>.md` |
| Synthetic fixture (sample user, sample recording) | `qa/fixtures/<feature>/...` |
| k6 perf script | `qa/performance/<feature>.js` |
| Perf budget table (per-route SLO) | `qa/performance/<feature>.md` |
| Test-environment manifest (which versions of which tools) | `qa/test-environment.md` (in this README) |
| Test strategy / pyramid | `docs/qa/test-strategy.md` |
| DOCUMENTED BUG registry | `CHANGELOG.md` under "Pinned as DOCUMENTED BUG" |
| Pre-existing test failures registry | `memory/pre-existing-test-failures.md` |

---

## Test environment (current as of 2026-06-11)

This is the per-PR test environment. If you bump a tool version, update
this list and `docs/qa/test-environment.md`.

### Backend tests
- **Python:** 3.12 (system) + `AINT_Venv/` venv
- **pytest:** 8.x (from `requirements-test.txt`)
- **SQLite:** 3.45+ (system)
- **Neo4j:** optional — skipped if not running; `ANT_SKIP_NEO4J=1` env
- **Ollama:** optional — used by the AI integration tests; skip with
  `ANT_SKIP_OLLAMA_TESTS=1`
- **Network:** outbound HTTP allowed; tests use `pytest-httpx` for mocking

### Web build
- **Node.js:** 20.x (LTS)
- **Vite:** 5.x

### Mobile tests
- **Jest:** 29.x
- **React Native:** 0.74.x
- **Metro:** bundled with RN

### Electron tests
- **node:test:** Node 20's built-in
- **No Electron binary** required for the `node:test` smoke tests;
  full Electron-runtime tests are gated behind a separate `npm run
  test:electron-runtime` target

### E2E
- **Playwright:** 1.45+
- **Browsers:** Chromium, Firefox, WebKit (downloaded via
  `npx playwright install`)
- **Backend:** a local uvicorn on `:8000` (or staging) must be up
  before the e2e tests start

---

## How to run all tests from scratch

```bash
# 0. Install everything
make setup

# 1. Backend tests
cd backend && pytest tests/ -q && cd ..

# 2. Web build (smoke)
cd apps/web && npx vite build && cd ../..

# 3. Mobile tests
cd mobile && npm test && cd ..

# 4. Electron node:test smoke
cd electron && npm test && cd ..

# 5. E2E (gated; needs the backend running)
cd e2e && npx playwright install --with-deps && npx playwright test
```

`make test` does steps 1-4 in one go. Step 5 is separate because it
needs a live backend.

---

## Adding a new test-environment artifact

1. Decide which subfolder it belongs in (test-plans / fixtures /
   performance).
2. Add a README in that subfolder explaining what's there.
3. If the artifact is a script, add it to the appropriate
   `package.json` (or Makefile) as a target.
4. Update `docs/qa/test-environment.md` if the artifact changes the
   test environment.
5. Update the table above (the "What goes where" table) if the
   artifact is a new *kind* of test thing.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
