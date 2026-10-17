# Backend Dev Role — Charter

> **Role tag:** `backend`
> **GitHub team:** `role-backend` (1 member today: `@shyamsunderprogramer-design`)
> **Charter owner:** This file is the canonical answer to "what does backend dev own?"

---

## What this role owns

The FastAPI Python backend and everything that runs inside it. File-level
inventory, in priority order:

### Core (app entry, config, db, lifecycle)
- `backend/core/main.py` — FastAPI app, lifespan, middleware, startup hooks
- `backend/core/config.py` — `settings` singleton, env-var reading
- `backend/core/database.py` — SQLAlchemy `Base`, `DatabaseManager`, all 13 model classes
- `backend/core/fast_startup.py` — startup banner + warm-up
- `backend/core/generate_ssl.py` — dev HTTPS cert generation
- `backend/core/backfill_cognitive_graph.py` — Neo4j backfill
- `backend/core/test_startup.py` — startup self-test

### Modules (7 sub-packages)
- `backend/modules/agents/` — AI agent orchestration, session manager
- `backend/modules/ai/` — provider routing, prompt templates, BYOK
- `backend/modules/crm/` — CRM integrations (Salesforce, HubSpot)
- `backend/modules/interview/` — interview session recording, analysis
- `backend/modules/platform/` — platform-specific endpoints
- `backend/modules/video/` — video processing, screen capture
- `backend/modules/voice/` — STT/TTS, voice commands, diarization

### Routes (FastAPI routers)
- `backend/routes/*.py` — 33+ routers, one per concern (auth, voice, agents, AI, etc.)

### Shared libs
- `backend/lib/http_client.py` — outbound HTTP helper
- `backend/lib/sse_helpers.py` — server-sent-event helpers

### Migrations
- `backend/migrations/` — Alembic env + versions/
- `backend/alembic.ini`
- `backend/start_server.py`

### Dependencies
- `backend/requirements.txt`
- `backend/requirements-test.txt`

### Test infra
- `backend/pytest.ini`
- `backend/tests/conftest.py` — co-owned with `qa` (see Co-owned section)

### Seed data only (not runtime state)
- `backend/data/seed*` — seed scripts + fixture data

> **Excluded** (gitignored runtime state): `backend/data/ainotetaker.db`,
> `backend/data/users.json`, `backend/data/audit_logs/`, `backend/data/voice_models/`,
> `backend/data/recordings/`, `backend/data/meeting_templates/`,
> `backend/data/user_keys/`.

---

## What this role reads but doesn't own

| Area | Owner | Why backend dev cares |
|---|---|---|
| `vercel.json` (CSP, allowed origins) | devops | backend CORS config must match |
| `.env.example` | devops | backend reads every var documented here |
| `k8s/helm/backend/values-*.yaml` | devops | backend dev sets the env-var values; devops files the manifest |
| `e2e/tests/` | qa | e2e tests call backend endpoints — backend dev reviews API contract tests |
| `apps/web/js/core/api.js` | uiux | the API contract from the web client — backend dev approves changes |
| `backend/security/` (impl) | devsecops + backend | devsecops owns policy/audit files; backend owns auth/encryption/rate_limit/validation impl |
| `apps/web/app.js` | uiux + backend | co-owned — UI/UX owns, backend approves API contract changes |

---

## What this role delivers

Typical PR outputs from a backend dev:

- New FastAPI router or new endpoints in an existing router
- New SQLAlchemy model + Alembic migration
- New AI provider integration (Ollama, OpenAI, Anthropic, etc.)
- New internal module under `backend/modules/`
- New Pydantic schemas
- New test file under `backend/tests/test_<module>.py`
- API reference update in `docs/backend/api/API_REFERENCE.md`
- Phase-2 feature work: updates `docs/backend/api/API_REFERENCE_PHASE2.md`
- Architecture deep-dive update in `docs/backend/architecture/TECHNICAL_SPECIFICATION.md`

---

## What this role's AI agent has access to

> **Status:** the role-scoped AI agent is a planning stub, not yet wired up.
> See `agents/backend/AGENTS.md` for the scoping plan.

When the agent is online, it will be able to:

- **Read:** every file in `backend/` (except `data/`, `.env`, etc.)
- **Write:** files in `backend/core/`, `backend/modules/`, `backend/routes/`,
  `backend/lib/`, `backend/migrations/`, `backend/tests/`
- **Bash:** pytest, alembic, uvicorn, pip install (scoped to `backend/`)
- **Search:** ripgrep across `backend/` only
- **Memory:** `agents/backend/MEMORY.md` (role-scoped persistent memory)

It will **not** have access to:
- `backend/data/users.json`, `backend/data/audit_logs/`, `*.pem`, `*.key`
- Files outside `backend/` (electron, mobile, web, infra)
- Shell commands that touch network or production

---

## What this role reviews when it gets a PR

When CODEOWNERS routes a PR to `role-backend`, this role checks:

1. **No broken endpoints** — `cd backend && pytest tests/ -q` passes
2. **No new env vars undocumented** — `.env.example` is updated
3. **No new SQLAlchemy model without migration** — `make alembic-revision` ran
4. **API contract unchanged or API reference updated** — `docs/backend/api/API_REFERENCE.md` is current
5. **No new secrets committed** — `*.pem`, `*.key`, `.env`, `users.json` not in the diff
6. **Tests cover new behavior** — `backend/tests/test_<feature>.py` exists
7. **Phase-2 work also updates** `docs/backend/api/API_REFERENCE_PHASE2.md` if applicable

---

## How to contact this role

- **Today:** `@shyamsunderprogramer-design` (sole human member of `role-backend`)
- **When collaborators join:** tag the `role-backend` GitHub Team in the PR

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
