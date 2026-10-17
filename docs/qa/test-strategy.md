# Test Strategy

> **Role tag:** `qa`
> **Owner:** `role-qa`

---

## What we test

ANT is a multi-platform monorepo (Electron, Vite web, React
Native mobile, MV3 Chrome extension, FastAPI backend) with a
large surface. The test strategy is layered:

| Layer | Tool | Where it lives | Who runs it |
|---|---|---|---|
| Unit (backend) | pytest | `backend/tests/` | CI on every PR |
| Unit (web JS) | node:test | `apps/web/js/__tests__/` (if present) | CI on every PR |
| Unit (mobile) | Jest | `mobile/__tests__/` | CI on every PR |
| Unit (electron) | node:test | `electron/tests/` | CI on every PR |
| E2E (web) | Playwright | `e2e/tests/` | CI on every PR |
| E2E (electron) | Spectron (legacy) / Playwright-electron (current) | `e2e/tests/electron/` (if present) | Manual + nightly |
| Performance | k6 | `qa/performance/` | Scheduled (nightly) |
| Manual / exploratory | human eyes | `qa/test-plans/` | Pre-release |
| Visual regression | Percy / Playwright screenshots | `e2e/tests/visual/` (if present) | PR with label `visual` |
| Security | trivy + bandit + npm audit | `.github/workflows/ci.yml` | CI on every PR |

---

## What we *don't* test

- **Real LLM provider integrations** — too flaky + costs money.
  We use Ollama locally (see `local-ai-wiring-2026-06-09`
  memory) for most AI-touching tests.
- **Real network conditions** — covered by k6 perf scripts in
  `qa/performance/`, not unit tests.
- **Real user data** — see `qa/fixtures/README.md` for the
  strict rule: no real PII, no real API keys, no real recordings.

---

## Regression tests for known bugs

Every "Fix #N" PR that pins a regression test follows the
convention `tests/test_fix_NN_<short_name>.py`. The full list is
in `CHANGELOG.md` under each release.

The most recent 15 are tracked in auto-memory. Examples:

- `tests/test_fix_31_user_id_auth.py` — `/agents/sessions` and
  `/shadow/start` no longer accept the literal `"default"` user_id
- `tests/test_fix_33_no_stub_recordings.py` — backend refuses to
  start with stub JSON files in `data/recordings/`
- `tests/test_fix_22_ci_workflow.py` — CI gates a PR if
  `backend/tests/` lacks a regression test for the fix
- `tests/test_fix_23_alembic_migrations.py` — Alembic head
  matches the SQLAlchemy model definitions

The "no regression test = no merge" rule is the heart of the
strategy. It's how we keep the test count growing with the
codebase without losing signal.

---

## Manual / exploratory

Automated tests catch regressions. They do *not* catch:

- Visual regressions that look fine in pixel diffs but feel
  wrong to a human
- Audio quality (transcription accuracy, mic echo, etc.)
- Multi-device interactions (Electron + mobile in the same
  room, etc.)
- Onboarding friction
- Error messages that confuse a real user

These are covered by `qa/test-plans/`. The QA reviewer runs the
plans before each release.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
