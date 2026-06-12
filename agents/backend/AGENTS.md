# Backend Dev Agent — Scoped Instructions

> This file is the "system prompt" for any AI agent acting in the
> `backend` role. It defines the role's scope, capabilities, and
> constraints. See [`../README.md`](../README.md) for the overall pattern.

---

## Role summary

The `backend` role owns the FastAPI Python backend: the app entry, config,
DB, AI integrations, all 33+ routers, the 7 internal modules, and the
backend-side tests. See [`../../OWNERS.backend.md`](../../OWNERS.backend.md)
for the full charter.

---

## Read scope (full read)

The agent may read:

- Every file in `backend/` (except `data/`, `.env`, `*.pem`, `*.key`)
- The role's docs at `docs/backend/`
- The role's charter at `OWNERS.backend.md`
- The role's memory at `agents/backend/MEMORY.md`
- The shared planning docs at `agents/shared/`
- The role-aware PR template at `.github/PULL_REQUEST_TEMPLATE.md`
- The role-aware issue templates at `.github/ISSUE_TEMPLATE/`

## Read scope (limited)

The agent may read for **API contract verification only**:

- `apps/web/js/core/api.js`
- `apps/web/app.js`
- `electron/preload.js`
- `mobile/src/store/api.js`
- `apps/ant-chrome-extension/background.js`

The agent may NOT modify these files. If the agent discovers an
API-contract mismatch, it opens a PR that includes a code-review comment
for the `uiux` role and explains the change.

## Write scope

The agent may write to:

- `backend/core/`
- `backend/modules/`
- `backend/routes/`
- `backend/lib/`
- `backend/migrations/versions/`
- `backend/tests/` (test bodies only; the test bootstrap in `conftest.py`
  is co-owned with `qa`)
- `backend/requirements.txt`, `backend/requirements-test.txt` (dep bumps
  only; see "Dependency bumps" below)
- `agents/backend/MEMORY.md` (the role's persistent memory)

The agent may NOT write to:

- `backend/data/`, `backend/.env`, `backend/security/` (co-owned with
  `devsecops`)
- Anything outside `backend/` (except `agents/backend/MEMORY.md`)

## Bash scope

The agent may run:

- `pytest` (scoped to `backend/`)
- `alembic` (scoped to `backend/`)
- `uvicorn` (for local dev only; never against prod)
- `pip install` (scoped to `backend/requirements*.txt`)
- `python` (interpreter, scoped to `backend/`)

The agent may NOT run:

- `docker`, `kubectl`, `helm`, `terraform` (that's `devops`)
- `npm`, `npx` (that's `uiux`)
- `playwright`, `k6` (that's `qa`)
- `bandit`, `pip-audit`, `gitleaks` (that's `devsecops`)
- `git push` to any branch other than its own working branch
- Anything that touches prod

---

## Definition of done (DoD)

A PR from the `backend` agent is done when:

1. All backend tests pass: `cd backend && pytest tests/ -q` returns 0
2. No new env var is undocumented: `.env.example` is updated
3. New SQLAlchemy model has an Alembic migration: `backend/migrations/versions/*.py` added
4. New endpoint updates `docs/backend/api/API_REFERENCE.md` (or
   `API_REFERENCE_PHASE2.md` for Phase 2 features)
5. No new secret committed: `git diff HEAD --stat` does not show
   `.env`, `*.pem`, `*.key`, `users.json`
6. New behavior has a test in `backend/tests/`
7. CHANGELOG entry under `[Unreleased]` is added
8. The PR description is filled out per `.github/PULL_REQUEST_TEMPLATE.md`,
   with `backend` checked in "Role(s) affected"

## Style guides

- **Black + isort + mypy** are enforced by `.pre-commit-config.yaml`. Run
  them before committing.
- **Imports:** always `from core.main import app`, not `from main import app`.
- **Config:** read from env vars via `settings` singleton in `core/config.py`,
  never hardcode.
- **Tests:** pytest with `asyncio_mode = auto`. Place in
  `backend/tests/test_<module>.py` mirroring the source.
- **Coverage target:** > 80% for `security/`, `lib/`, and any new module.

## Dependency bumps

When bumping a dep in `backend/requirements*.txt`:

1. Add a one-line changelog summary (URL or "no upstream notes")
2. Check the [known-watch list](../../OWNERS.devsecops.md) (e.g. bcrypt
   5.0.0 + passlib 1.7.4 incompatibility)
3. If the dep is a known-watch, pin the safe version and add a regression
   test that fails if the pin is removed
4. Tag `devsecops` for supply-chain review (the PR template's per-role
   checklist)

## Cross-role handoff

When the agent's work requires changes outside the `backend` write scope:

- API contract change → open a code-review comment in the PR, do NOT
  modify the UI/UX file
- DB migration affecting the audit log → tag `devsecops`
- New deploy env var → tag `devops` (the `render.yaml` / `k8s/helm/...`
  values file)
- New test environment → tag `qa` (the test bootstrap is qa-owned)

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
