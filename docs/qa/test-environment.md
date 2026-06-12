# Test Environment

> **Role tag:** `qa`
> **Owner:** `role-qa`

---

## Versions in use (2026-06-11 snapshot)

| Tool | Version | Why |
|---|---|---|
| Python | 3.11.x | FastAPI + spaCy + Alembic; pinned in `backend/requirements.txt` |
| Node | 20.x LTS | Web + Electron + RN dev server; pinned in `.nvmrc` |
| npm | 10.x | Comes with Node 20 |
| pytest | 8.x | Backend tests |
| Playwright | 1.45.x | E2E + a11y |
| Jest | 29.x | Mobile tests |
| node:test (built-in) | Node 20 | Electron tests (no Jest dep) |
| Ollama | 0.5.x | Local AI for tests that touch the AI layer |
| Models pulled | `qwen3.5:9b`, `gemma4:e4b`, `lfm2.5` | See `local-ai-wiring-2026-06-09` memory |
| Neo4j | 5.x | Cognitive graph; container in `docker/` |
| SQLite | 3.40+ | Default backend DB (dev + tests) |
| ffmpeg | 6.x | Audio processing in tests |

---

## Local setup

1. `make setup` — installs Python deps, npm workspaces, and
   pulls Ollama models.
2. `make test` — runs the full backend + web + mobile + electron
   test suites.
3. `make e2e` — runs Playwright (requires the backend to be up).
4. `make perf` — runs k6 perf scripts (requires the backend to
   be up + a real-ish load profile).

---

## CI environment

The CI workflow (`.github/workflows/ci.yml`) uses:

- GitHub-hosted Ubuntu 22.04 runners
- 2 vCPU / 7 GB RAM / 14 GB SSD per job
- Python 3.11 (via `actions/setup-python`)
- Node 20 (via `actions/setup-node`)
- Cached `~/.cache/pip` and `~/.npm` for speed
- No Neo4j — tests that need Neo4j are tagged `@pytest.mark.neo4j`
  and skipped in CI; they run on demand in dev

---

## Why we skip Neo4j in CI

- Neo4j is heavy (1+ GB memory, slow startup)
- Most of the cognitive-graph logic is exercised against
  `in_memory_graph.py` (a thin shim used in tests)
- The few tests that need real Neo4j run on a self-hosted
  runner in the dev machine, not in CI

This is tracked as a follow-up: "spin up Neo4j in CI" is a
candidate for a future PR.

---

## Pre-commit

`.pre-commit-config.yaml` runs:

- `black`, `isort`, `flake8` (Python)
- `prettier` (JS / TS / JSON / YAML / Markdown)
- `detect-private-key` (no accidentally committed `*.pem` /
  `*.key` / `id_rsa`)

Excludes: `backend/venv/`, `AINT_Venv/`,
`backend/migrations/versions/` (Alembic-generated), `*.pyc`.

---

## Known gotchas

- **bcrypt 5.0.0 + passlib 1.7.4** — incompatible. Pin
  `bcrypt<4.1` until the auth code migrates off passlib. A live
  smoke test caught what 965 unit tests missed; see the
  `bcrypt-passlib-incompatibility-2026-06-07` memory.
- **TestClient returns 405** — fastapi 0.135.1 + httpx 0.28+:
  `TestClient` from FastAPI rejects APIRouter routes with 405.
  Workaround: use `httpx.AsyncClient` + `ASGITransport` directly.
- **Vite build** requires `--mode production` for the prod
  bundle, not the dev bundle.
- **Ollama "thinking" field** — qwen3.5:9b returns content in
  the `thinking` field if you don't set `"think": false` in the
  payload. Test the actual response, not the streamed chunks.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
